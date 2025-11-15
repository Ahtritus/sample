"""Main entry point for indexer service."""
import argparse
from src.indexer.indexer import Indexer
from src.common.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Social trends indexer")
    parser.add_argument("--input-queue", default="enriched_posts")
    parser.add_argument("--batch-size", type=int)
    
    args = parser.parse_args()
    
    indexer = Indexer()
    indexer.process_queue(
        input_queue=args.input_queue,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()

