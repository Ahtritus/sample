"""Preprocessor service: normalizes, enriches, and deduplicates posts."""
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from src.common.config import settings
from src.common.logger import setup_logger
from src.common.redis_client import RedisClient
from src.common.models import SocialPost
from src.preprocessor.nlp_processor import NLPProcessor
from src.common.metrics import posts_processed_total, processing_duration_seconds, errors_total

logger = setup_logger(__name__)


class Preprocessor:
    """Preprocesses raw posts: normalization, enrichment, deduplication."""
    
    def __init__(self):
        """Initialize preprocessor."""
        self.redis = RedisClient()
        self.nlp = NLPProcessor()
        logger.info("Initialized preprocessor")
    
    def generate_canonical_id(self, platform: str, normalized_text: str, user_id: str, time_bucket: str) -> str:
        """Generate canonical ID for deduplication."""
        # Time bucket: round to 5-minute intervals
        content = f"{platform}:{normalized_text}:{user_id}:{time_bucket}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get_time_bucket(self, created_at: datetime) -> str:
        """Get time bucket (5-minute interval)."""
        # Round to 5-minute intervals
        minutes = (created_at.minute // 5) * 5
        bucket_time = created_at.replace(minute=minutes, second=0, microsecond=0)
        return bucket_time.isoformat()
    
    def process_post(self, raw_post: Dict[str, Any]) -> Optional[SocialPost]:
        """Process a single raw post."""
        start_time = time.time()
        
        try:
            # Extract basic fields
            platform = raw_post.get("platform", "reddit")
            post_id = raw_post.get("post_id")
            created_at_str = raw_post.get("created_at")
            
            if not post_id or not created_at_str:
                logger.warning("Missing required fields in raw post")
                return None
            
            # Parse datetime
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except:
                created_at = datetime.utcnow()
            
            # Normalize text
            raw_text = raw_post.get("text", "")
            normalized_text = self.nlp.normalize_text(raw_text)
            
            if not normalized_text or len(normalized_text) < 10:
                logger.debug(f"Skipping post {post_id}: text too short")
                return None
            
            # Generate canonical ID
            time_bucket = self.get_time_bucket(created_at)
            user_id = raw_post.get("user_id", "unknown")
            canonical_id = self.generate_canonical_id(platform, normalized_text, user_id, time_bucket)
            
            # Check for duplicates
            if self.redis.check_duplicate(canonical_id):
                logger.debug(f"Skipping duplicate post: {canonical_id}")
                posts_processed_total.labels(status="duplicate").inc()
                return None
            
            # Language detection
            language = self.nlp.detect_language(normalized_text)
            
            # Sentiment analysis
            sentiment_score, sentiment_label = self.nlp.compute_sentiment(normalized_text)
            
            # Keyword extraction
            keywords = self.nlp.extract_keywords(normalized_text, max_keywords=10)
            
            # Region inference
            region = self.nlp.infer_region(normalized_text, language)
            
            # Bot score
            user_followers = raw_post.get("user_followers", 0)
            user_name = raw_post.get("user_name", "")
            is_bot_score = self.nlp.compute_bot_score(normalized_text, user_name, user_followers)
            
            # Engagement
            engagement_data = raw_post.get("engagement", {})
            from src.common.models import Engagement
            engagement = Engagement(
                score=engagement_data.get("score", 0),
                comments=engagement_data.get("comments", 0),
                likes=engagement_data.get("likes", 0)
            )
            
            # Create enriched post
            post = SocialPost(
                platform=platform,
                post_id=post_id,
                canonical_id=canonical_id,
                created_at=created_at,
                user_id=user_id,
                user_name=user_name,
                user_followers=user_followers,
                text=normalized_text,
                language=language,
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                keywords=keywords,
                region=region,
                is_bot_score=is_bot_score,
                engagement=engagement,
                raw=raw_post
            )
            
            duration = time.time() - start_time
            processing_duration_seconds.observe(duration)
            posts_processed_total.labels(status="success").inc()
            
            return post
            
        except Exception as e:
            logger.error(f"Error processing post: {e}")
            posts_processed_total.labels(status="error").inc()
            errors_total.labels(component="preprocessor", error_type="processing_error").inc()
            return None
    
    def process_queue(self, input_queue: str = "raw_posts", output_queue: str = "enriched_posts", batch_size: int = None):
        """Process posts from input queue and push to output queue."""
        if batch_size is None:
            batch_size = settings.BATCH_SIZE
        
        logger.info(f"Starting to process queue: {input_queue} -> {output_queue}")
        
        while True:
            try:
                # Pop from input queue
                raw_post = self.redis.pop_from_queue(input_queue, timeout=5)
                
                if not raw_post:
                    continue
                
                # Process post
                enriched_post = self.process_post(raw_post)
                
                if enriched_post:
                    # Push to output queue
                    self.redis.push_to_queue(output_queue, enriched_post.to_es_doc())
                    logger.debug(f"Processed post: {enriched_post.post_id}")
                
            except KeyboardInterrupt:
                logger.info("Stopping preprocessor")
                break
            except Exception as e:
                logger.error(f"Error in process queue: {e}")
                errors_total.labels(component="preprocessor", error_type="queue_error").inc()
                time.sleep(1)

