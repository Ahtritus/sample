"""Topic extractor: TF-IDF + k-means clustering."""
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from src.common.config import settings
from src.common.logger import setup_logger
from src.common.es_client import ESClient
from src.common.models import Topic
from src.common.metrics import errors_total

logger = setup_logger(__name__)


class TopicExtractor:
    """Extracts topics using TF-IDF and k-means clustering."""
    
    def __init__(self, n_clusters: int = 10, min_docs_per_topic: int = 5):
        """Initialize topic extractor."""
        self.es = ESClient()
        self.n_clusters = n_clusters
        self.min_docs_per_topic = min_docs_per_topic
        logger.info(f"Initialized topic extractor (n_clusters={n_clusters})")
    
    def fetch_recent_posts(self, minutes: int = 15) -> List[Dict[str, Any]]:
        """Fetch recent posts from Elasticsearch."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            cutoff_str = cutoff_time.isoformat()
            
            query = {
                "query": {
                    "range": {
                        "created_at": {
                            "gte": cutoff_str
                        }
                    }
                },
                "size": 1000,
                "_source": ["post_id", "text", "keywords", "sentiment_score", "created_at"]
            }
            
            posts = self.es.search(query, index_pattern="socialposts-v1-*", size=1000)
            logger.info(f"Fetched {len(posts)} recent posts")
            return posts
            
        except Exception as e:
            logger.error(f"Error fetching recent posts: {e}")
            errors_total.labels(component="topic_extractor", error_type="fetch_error").inc()
            return []
    
    def extract_topics(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract topics from posts using TF-IDF + k-means."""
        if len(posts) < self.min_docs_per_topic:
            logger.warning(f"Not enough posts for topic extraction: {len(posts)}")
            return []
        
        try:
            # Prepare texts
            texts = [post.get("text", "") for post in posts]
            post_ids = [post.get("post_id") for post in posts]
            
            # Filter out empty texts
            valid_indices = [i for i, text in enumerate(texts) if text and len(text) > 20]
            if len(valid_indices) < self.min_docs_per_topic:
                return []
            
            valid_texts = [texts[i] for i in valid_indices]
            valid_posts = [posts[i] for i in valid_indices]
            
            # TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2
            )
            
            tfidf_matrix = vectorizer.fit_transform(valid_texts)
            
            # Determine number of clusters (don't exceed number of documents)
            n_clusters = min(self.n_clusters, len(valid_texts) // self.min_docs_per_topic)
            if n_clusters < 2:
                logger.warning("Not enough documents for clustering")
                return []
            
            # K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)
            
            # Extract feature names
            feature_names = vectorizer.get_feature_names_out()
            
            # Build topic clusters
            topics = []
            for cluster_id in range(n_clusters):
                cluster_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
                
                if len(cluster_indices) < self.min_docs_per_topic:
                    continue
                
                # Get top keywords for this cluster
                cluster_center = kmeans.cluster_centers_[cluster_id]
                top_indices = cluster_center.argsort()[-10:][::-1]
                top_keywords = [feature_names[i] for i in top_indices]
                
                # Get sample posts
                cluster_posts = [valid_posts[i] for i in cluster_indices]
                sample_posts = [
                    {
                        "post_id": p.get("post_id"),
                        "text": p.get("text", "")[:200],  # Truncate
                        "sentiment_score": p.get("sentiment_score", 0.0)
                    }
                    for p in cluster_posts[:5]  # Top 5 samples
                ]
                
                # Compute average sentiment
                avg_sentiment = np.mean([p.get("sentiment_score", 0.0) for p in cluster_posts])
                
                # Generate topic ID
                topic_id = f"topic_{cluster_id}_{int(time.time())}"
                
                topic = {
                    "topic_id": topic_id,
                    "keywords": top_keywords,
                    "top_keywords": top_keywords[:5],
                    "volume": len(cluster_indices),
                    "avg_sentiment": float(avg_sentiment),
                    "sample_posts": sample_posts,
                    "cluster_indices": cluster_indices,
                    "post_ids": [valid_posts[i].get("post_id") for i in cluster_indices]
                }
                
                topics.append(topic)
            
            logger.info(f"Extracted {len(topics)} topics from {len(valid_texts)} posts")
            return topics
            
        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            errors_total.labels(component="topic_extractor", error_type="extraction_error").inc()
            return []
    
    def compute_velocity(self, current_volume: int, previous_volume: int) -> float:
        """Compute trend velocity (growth rate)."""
        if previous_volume == 0:
            return float('inf') if current_volume > 0 else 0.0
        return (current_volume - previous_volume) / previous_volume
    
    def index_topics(self, topics: List[Dict[str, Any]]):
        """Index topics to Elasticsearch."""
        if not topics:
            return
        
        try:
            # Convert to Topic models and index
            topic_docs = []
            for topic_data in topics:
                topic = Topic(
                    topic_id=topic_data["topic_id"],
                    keywords=topic_data["keywords"],
                    top_keywords=topic_data["top_keywords"],
                    volume=topic_data["volume"],
                    velocity=topic_data.get("velocity", 0.0),
                    avg_sentiment=topic_data["avg_sentiment"],
                    sample_posts=topic_data["sample_posts"]
                )
                topic_docs.append(topic.to_es_doc())
            
            # Index topics
            self.es.bulk_index(topic_docs, "topics-v1")
            logger.info(f"Indexed {len(topic_docs)} topics")
            
        except Exception as e:
            logger.error(f"Error indexing topics: {e}")
            errors_total.labels(component="topic_extractor", error_type="indexing_error").inc()
    
    def assign_topics_to_posts(self, topics: List[Dict[str, Any]]):
        """Assign topic IDs to posts."""
        try:
            for topic in topics:
                topic_id = topic["topic_id"]
                post_ids = topic.get("post_ids", [])
                
                if not post_ids:
                    continue
                
                # Update posts with topic_id
                for post_id in post_ids:
                    query = {
                        "term": {"post_id": post_id}
                    }
                    script = {
                        "source": "ctx._source.topic_id = params.topic_id; ctx._source.topics = [params.topic_id]",
                        "params": {"topic_id": topic_id}
                    }
                    
                    self.es.update_by_query("socialposts-v1-*", query, script)
            
            logger.info("Assigned topic IDs to posts")
            
        except Exception as e:
            logger.error(f"Error assigning topics: {e}")
            errors_total.labels(component="topic_extractor", error_type="assignment_error").inc()
    
    def run_extraction(self, minutes: int = 15):
        """Run topic extraction on recent posts."""
        logger.info(f"Starting topic extraction (last {minutes} minutes)")
        
        # Fetch recent posts
        posts = self.fetch_recent_posts(minutes=minutes)
        
        if not posts:
            logger.info("No recent posts to extract topics from")
            return
        
        # Extract topics
        topics = self.extract_topics(posts)
        
        if not topics:
            logger.info("No topics extracted")
            return
        
        # Index topics
        self.index_topics(topics)
        
        # Assign topics to posts
        self.assign_topics_to_posts(topics)
        
        logger.info(f"Topic extraction completed: {len(topics)} topics")

