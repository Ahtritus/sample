"""Reddit API fetcher with cursor persistence and rate limiting."""
import praw
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.common.config import settings
from src.common.logger import setup_logger
from src.common.redis_client import RedisClient
from src.common.metrics import fetch_requests_total, fetch_duration_seconds, errors_total

logger = setup_logger(__name__)


class RedditFetcher:
    """Fetches posts from Reddit API."""
    
    def __init__(self):
        """Initialize Reddit fetcher."""
        self.reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT
        )
        self.redis = RedisClient()
        self.subreddits = [s.strip() for s in settings.SUBREDDITS.split(",")]
        logger.info(f"Initialized Reddit fetcher for subreddits: {self.subreddits}")
    
    def _get_cursor_key(self, subreddit: str) -> str:
        """Get cursor key for subreddit."""
        return f"cursor:reddit:{subreddit}"
    
    def _get_last_fetch_time(self, subreddit: str) -> Optional[datetime]:
        """Get last fetch time from cursor."""
        cursor = self.redis.get_cursor(self._get_cursor_key(subreddit))
        if cursor:
            try:
                return datetime.fromisoformat(cursor)
            except:
                return None
        return None
    
    def _save_cursor(self, subreddit: str, timestamp: datetime):
        """Save cursor timestamp."""
        self.redis.set_cursor(self._get_cursor_key(subreddit), timestamp.isoformat())
    
    def _normalize_post(self, submission: Any, subreddit: str) -> Dict[str, Any]:
        """Normalize Reddit submission to common format."""
        try:
            created_at = datetime.fromtimestamp(submission.created_utc)
            
            return {
                "platform": "reddit",
                "post_id": submission.id,
                "created_at": created_at.isoformat(),
                "user_id": str(submission.author) if submission.author else "unknown",
                "user_name": str(submission.author) if submission.author else "unknown",
                "user_followers": 0,  # Reddit doesn't expose follower count easily
                "text": f"{submission.title} {submission.selftext}".strip(),
                "engagement": {
                    "score": submission.score,
                    "comments": submission.num_comments,
                    "likes": submission.ups
                },
                "subreddit": subreddit,
                "url": submission.url,
                "raw": {
                    "id": submission.id,
                    "title": submission.title,
                    "selftext": submission.selftext,
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "created_utc": submission.created_utc,
                    "subreddit": subreddit
                }
            }
        except Exception as e:
            logger.error(f"Error normalizing post {submission.id}: {e}")
            return None
    
    def fetch_new_posts(self, subreddit: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch new posts from subreddit."""
        start_time = time.time()
        posts = []
        
        try:
            subreddit_obj = self.reddit.subreddit(subreddit)
            last_fetch = self._get_last_fetch_time(subreddit)
            
            # Fetch new posts
            for submission in subreddit_obj.new(limit=limit):
                created_at = datetime.fromtimestamp(submission.created_utc)
                
                # Skip if we've already fetched this
                if last_fetch and created_at <= last_fetch:
                    continue
                
                normalized = self._normalize_post(submission, subreddit)
                if normalized:
                    posts.append(normalized)
            
            # Update cursor to current time
            if posts:
                latest_time = max(
                    datetime.fromtimestamp(p["raw"]["created_utc"]) 
                    for p in posts if p and "raw" in p and "created_utc" in p["raw"]
                )
                self._save_cursor(subreddit, latest_time)
            else:
                # Still update cursor to prevent refetching
                self._save_cursor(subreddit, datetime.utcnow())
            
            duration = time.time() - start_time
            fetch_duration_seconds.labels(platform="reddit").observe(duration)
            fetch_requests_total.labels(platform="reddit", status="success").inc()
            
            logger.info(f"Fetched {len(posts)} new posts from r/{subreddit} in {duration:.2f}s")
            return posts
            
        except Exception as e:
            logger.error(f"Error fetching from r/{subreddit}: {e}")
            fetch_requests_total.labels(platform="reddit", status="error").inc()
            errors_total.labels(component="fetcher", error_type="fetch_error").inc()
            return []
    
    def fetch_all_subreddits(self) -> List[Dict[str, Any]]:
        """Fetch posts from all configured subreddits."""
        all_posts = []
        
        for subreddit in self.subreddits:
            try:
                posts = self.fetch_new_posts(subreddit, limit=100)
                all_posts.extend(posts)
                
                # Rate limiting: Reddit allows 60 requests per minute
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error fetching from r/{subreddit}: {e}")
                continue
        
        return all_posts
    
    def run_continuous(self, queue_name: str = "raw_posts"):
        """Continuously fetch and push to queue."""
        logger.info("Starting continuous fetch loop")
        
        while True:
            try:
                posts = self.fetch_all_subreddits()
                
                for post in posts:
                    self.redis.push_to_queue(queue_name, post)
                
                logger.info(f"Pushed {len(posts)} posts to queue")
                
                # Wait before next fetch
                time.sleep(settings.FETCH_INTERVAL_SEC)
                
            except KeyboardInterrupt:
                logger.info("Stopping fetcher")
                break
            except Exception as e:
                logger.error(f"Error in fetch loop: {e}")
                errors_total.labels(component="fetcher", error_type="loop_error").inc()
                time.sleep(30)  # Back off on error

