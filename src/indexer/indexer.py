"""Indexer service: bulk writes enriched posts to Elasticsearch."""
import time
from typing import List, Dict, Any
from src.common.config import settings
from src.common.logger import setup_logger
from src.common.redis_client import RedisClient
from src.common.es_client import ESClient
from src.common.metrics import posts_indexed_total, indexing_duration_seconds, errors_total

logger = setup_logger(__name__)


class Indexer:
    """Indexes enriched posts to Elasticsearch."""
    
    def __init__(self):
        """Initialize indexer."""
        self.redis = RedisClient()
        self.es = ESClient()
        logger.info("Initialized indexer")
    
    def index_batch(self, docs: List[Dict[str, Any]]) -> int:
        """Index a batch of documents."""
        if not docs:
            return 0
        
        start_time = time.time()
        
        try:
            indexed = self.es.bulk_index(docs, "socialposts-v1")
            
            duration = time.time() - start_time
            logger.info(f"Indexed {indexed}/{len(docs)} documents in {duration:.2f}s")
            
            return indexed
            
        except Exception as e:
            logger.error(f"Error indexing batch: {e}")
            errors_total.labels(component="indexer", error_type="indexing_error").inc()
            return 0
    
    def process_queue(self, input_queue: str = "enriched_posts", batch_size: int = None):
        """Process enriched posts from queue and index to ES."""
        if batch_size is None:
            batch_size = settings.BATCH_SIZE
        
        logger.info(f"Starting to index from queue: {input_queue}")
        
        batch = []
        last_index_time = time.time()
        
        while True:
            try:
                # Pop from queue
                doc = self.redis.pop_from_queue(input_queue, timeout=5)
                
                if doc:
                    batch.append(doc)
                
                # Index batch when full or timeout
                should_index = (
                    len(batch) >= batch_size or
                    (batch and time.time() - last_index_time > 30)
                )
                
                if should_index and batch:
                    self.index_batch(batch)
                    batch = []
                    last_index_time = time.time()
                
            except KeyboardInterrupt:
                # Index remaining batch
                if batch:
                    self.index_batch(batch)
                logger.info("Stopping indexer")
                break
            except Exception as e:
                logger.error(f"Error in index queue: {e}")
                errors_total.labels(component="indexer", error_type="queue_error").inc()
                time.sleep(1)

