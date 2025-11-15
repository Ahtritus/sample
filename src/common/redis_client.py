"""Redis client wrapper for queue and deduplication."""
import json
import redis
from typing import Optional, List, Any
from src.common.config import settings
from src.common.logger import setup_logger
from src.common.metrics import queue_size

logger = setup_logger(__name__)


class RedisClient:
    """Redis client wrapper."""
    
    def __init__(self):
        """Initialize Redis client."""
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        try:
            self.client.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def push_to_queue(self, queue_name: str, item: Any) -> bool:
        """Push item to queue."""
        try:
            self.client.rpush(queue_name, json.dumps(item))
            queue_size.inc()
            return True
        except Exception as e:
            logger.error(f"Failed to push to queue: {e}")
            return False
    
    def pop_from_queue(self, queue_name: str, timeout: int = 0) -> Optional[Any]:
        """Pop item from queue."""
        try:
            result = self.client.blpop(queue_name, timeout=timeout)
            if result:
                queue_size.dec()
                return json.loads(result[1])
            return None
        except Exception as e:
            logger.error(f"Failed to pop from queue: {e}")
            return None
    
    def queue_length(self, queue_name: str) -> int:
        """Get queue length."""
        try:
            length = self.client.llen(queue_name)
            queue_size.set(length)
            return length
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    def set_cursor(self, key: str, value: str) -> bool:
        """Set cursor value."""
        try:
            self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set cursor: {e}")
            return False
    
    def get_cursor(self, key: str) -> Optional[str]:
        """Get cursor value."""
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Failed to get cursor: {e}")
            return None
    
    def check_duplicate(self, canonical_id: str, ttl: int = 86400) -> bool:
        """Check if canonical_id exists (deduplication)."""
        try:
            key = f"seen:{canonical_id}"
            exists = self.client.exists(key)
            if not exists:
                self.client.setex(key, ttl, "1")
            return exists == 1
        except Exception as e:
            logger.error(f"Failed to check duplicate: {e}")
            return False

