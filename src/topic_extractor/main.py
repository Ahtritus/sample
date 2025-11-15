"""Main entry point for topic extractor service."""
import argparse
import time
from src.topic_extractor.topic_extractor import TopicExtractor
from src.common.config import settings
from src.common.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Social trends topic extractor")
    parser.add_argument("--once", action="store_true", help="Run once instead of continuous")
    parser.add_argument("--minutes", type=int, default=15, help="Time window in minutes")
    parser.add_argument("--n-clusters", type=int, default=10, help="Number of clusters")
    
    args = parser.parse_args()
    
    extractor = TopicExtractor(n_clusters=args.n_clusters)
    
    if args.once:
        # Run once
        extractor.run_extraction(minutes=args.minutes)
    else:
        # Run continuously
        interval_sec = settings.TOPIC_EXTRACT_INTERVAL_MIN * 60
        logger.info(f"Starting continuous topic extraction (interval: {interval_sec}s)")
        
        while True:
            try:
                extractor.run_extraction(minutes=args.minutes)
                time.sleep(interval_sec)
            except KeyboardInterrupt:
                logger.info("Stopping topic extractor")
                break
            except Exception as e:
                logger.error(f"Error in topic extraction loop: {e}")
                time.sleep(60)


if __name__ == "__main__":
    main()

