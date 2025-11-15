"""Test the end-to-end pipeline with sample data."""
import json
import time
from datetime import datetime
from src.common.redis_client import RedisClient
from src.common.es_client import ESClient
from src.preprocessor.preprocessor import Preprocessor
from src.indexer.indexer import Indexer
from src.common.logger import setup_logger

logger = setup_logger(__name__)


def create_sample_post(subreddit: str, title: str, text: str = "") -> dict:
    """Create a sample Reddit post."""
    return {
        "platform": "reddit",
        "post_id": f"test_{int(time.time())}",
        "created_at": datetime.utcnow().isoformat(),
        "user_id": "test_user",
        "user_name": "testuser",
        "user_followers": 100,
        "text": f"{title} {text}".strip(),
        "engagement": {
            "score": 10,
            "comments": 5,
            "likes": 10
        },
        "subreddit": subreddit,
        "raw": {
            "id": f"test_{int(time.time())}",
            "title": title,
            "selftext": text,
            "score": 10,
            "num_comments": 5,
            "created_utc": time.time(),
            "subreddit": subreddit
        }
    }


def main():
    """Test the pipeline."""
    logger.info("Starting pipeline test")
    
    # Initialize clients
    redis = RedisClient()
    es = ESClient()
    preprocessor = Preprocessor()
    indexer = Indexer()
    
    # Create sample posts
    sample_posts = [
        create_sample_post("python", "Python 3.12 new features", "Excited about the new type hints!"),
        create_sample_post("python", "Python async tutorial", "Learning asyncio is challenging but fun."),
        create_sample_post("programming", "Best practices for code reviews", "Here are some tips..."),
        create_sample_post("programming", "Code review guidelines", "Make sure to check these things."),
        create_sample_post("technology", "AI developments in 2024", "GPT-4 is amazing!"),
    ]
    
    logger.info(f"Created {len(sample_posts)} sample posts")
    
    # Push to queue
    for post in sample_posts:
        redis.push_to_queue("raw_posts", post)
    
    logger.info("Pushed posts to raw_posts queue")
    
    # Process posts
    processed = []
    for post in sample_posts:
        enriched = preprocessor.process_post(post)
        if enriched:
            processed.append(enriched)
            redis.push_to_queue("enriched_posts", enriched.to_es_doc())
    
    logger.info(f"Processed {len(processed)} posts")
    
    # Index posts
    enriched_docs = [p.to_es_doc() for p in processed]
    indexed = indexer.index_batch(enriched_docs)
    
    logger.info(f"Indexed {indexed} posts")
    
    # Wait a bit for indexing
    time.sleep(2)
    
    # Verify in ES
    query = {"query": {"match_all": {}}}
    results = es.search(query, index_pattern="socialposts-v1-*", size=10)
    
    logger.info(f"Found {len(results)} documents in Elasticsearch")
    
    for result in results:
        logger.info(f"Post: {result.get('post_id')} - {result.get('text', '')[:50]}...")
    
    logger.info("Pipeline test completed")


if __name__ == "__main__":
    main()

