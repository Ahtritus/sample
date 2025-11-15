"""Elasticsearch client wrapper."""
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from src.common.config import settings
from src.common.logger import setup_logger
from src.common.metrics import posts_indexed_total, indexing_duration_seconds, errors_total
import time

logger = setup_logger(__name__)


class ESClient:
    """Elasticsearch client wrapper."""
    
    def __init__(self):
        """Initialize ES client."""
        es_config = {
            "hosts": [f"{settings.ES_HOST}:{settings.ES_PORT}"],
            "verify_certs": False,
        }
        
        if settings.ES_USERNAME and settings.ES_PASSWORD:
            es_config["basic_auth"] = (settings.ES_USERNAME, settings.ES_PASSWORD)
        
        self.client = Elasticsearch(**es_config)
        logger.info(f"Connected to Elasticsearch at {settings.ES_HOST}:{settings.ES_PORT}")
    
    def create_index_template(self, template_name: str, template_body: Dict[str, Any]) -> bool:
        """Create or update an index template."""
        try:
            # ES 8.x API: use body parameter with name
            self.client.indices.put_index_template(
                name=template_name,
                body=template_body
            )
            logger.info(f"Created index template: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index template: {e}")
            errors_total.labels(component="es_client", error_type="template_creation").inc()
            return False
    
    def create_ilm_policy(self, policy_name: str, policy_body: Dict[str, Any]) -> bool:
        """Create or update an ILM policy."""
        try:
            # ES 8.x API: use body parameter
            self.client.ilm.put_lifecycle(name=policy_name, body=policy_body)
            logger.info(f"Created ILM policy: {policy_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create ILM policy: {e}")
            errors_total.labels(component="es_client", error_type="ilm_creation").inc()
            return False
    
    def bulk_index(self, docs: List[Dict[str, Any]], index_prefix: str) -> int:
        """Bulk index documents with date-based index naming."""
        if not docs:
            return 0
        
        start_time = time.time()
        indexed_count = 0
        
        try:
            # Group docs by date for index naming
            from collections import defaultdict
            from datetime import datetime
            
            docs_by_date = defaultdict(list)
            for doc in docs:
                # Extract date from created_at or ingest_ts
                date_str = doc.get("created_at", doc.get("ingest_ts", datetime.utcnow().isoformat()))
                if isinstance(date_str, str):
                    date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else:
                    date_obj = date_str
                
                date_key = date_obj.strftime("%Y.%m.%d")
                index_name = f"{index_prefix}-{date_key}"
                docs_by_date[index_name].append(doc)
            
            # Bulk index for each date
            for index_name, date_docs in docs_by_date.items():
                actions = []
                for doc in date_docs:
                    action = {
                        "_index": index_name,
                        "_id": doc.get("canonical_id", doc.get("post_id")),
                        "_source": doc
                    }
                    actions.append(action)
                
                if actions:
                    success, failed = bulk(self.client, actions, raise_on_error=False)
                    indexed_count += success
                    
                    if failed:
                        logger.warning(f"Failed to index {len(failed)} documents")
                        errors_total.labels(component="es_client", error_type="bulk_index").inc()
            
            duration = time.time() - start_time
            indexing_duration_seconds.observe(duration)
            posts_indexed_total.labels(status="success").inc(indexed_count)
            
            logger.info(f"Indexed {indexed_count} documents in {duration:.2f}s")
            return indexed_count
            
        except Exception as e:
            logger.error(f"Bulk index failed: {e}")
            errors_total.labels(component="es_client", error_type="bulk_index").inc()
            posts_indexed_total.labels(status="error").inc(len(docs))
            return 0
    
    def search(self, query: Dict[str, Any], index_pattern: str = "socialposts-v1-*", size: int = 100) -> List[Dict[str, Any]]:
        """Search documents."""
        try:
            # ES 8.x API: use body parameter for query
            response = self.client.search(
                index=index_pattern,
                body=query,
                size=size
            )
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            errors_total.labels(component="es_client", error_type="search").inc()
            return []
    
    def update_by_query(self, index_pattern: str, query: Dict[str, Any], script: Dict[str, Any]) -> int:
        """Update documents by query."""
        try:
            # ES 8.x API: use body parameter
            response = self.client.update_by_query(
                index=index_pattern,
                body={
                    "query": query,
                    "script": script
                }
            )
            return response.get("updated", 0)
        except Exception as e:
            logger.error(f"Update by query failed: {e}")
            errors_total.labels(component="es_client", error_type="update_by_query").inc()
            return 0
    
    def health_check(self) -> bool:
        """Check ES cluster health."""
        try:
            health = self.client.cluster.health()
            return health["status"] in ["green", "yellow"]
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

