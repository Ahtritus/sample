"""Setup Elasticsearch: create index templates and ILM policies."""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.es_client import ESClient
from src.common.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Setup Elasticsearch indices and policies."""
    es = ESClient()
    
    # Check health
    if not es.health_check():
        logger.error("Elasticsearch is not healthy")
        sys.exit(1)
    
    # Load index templates
    config_dir = Path(__file__).parent.parent / "config"
    
    # Social posts template
    with open(config_dir / "es_index_template.json", "r") as f:
        posts_template = json.load(f)
    es.create_index_template("socialposts-v1-template", posts_template)
    
    # Topics template
    with open(config_dir / "es_topics_template.json", "r") as f:
        topics_template = json.load(f)
    es.create_index_template("topics-v1-template", topics_template)
    
    # ILM policy
    with open(config_dir / "es_ilm_policy.json", "r") as f:
        ilm_policy = json.load(f)
    es.create_ilm_policy("socialposts-policy", ilm_policy["policy"])
    
    logger.info("Elasticsearch setup completed")


if __name__ == "__main__":
    main()

