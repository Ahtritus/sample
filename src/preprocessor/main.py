"""Main entry point for preprocessor service."""
import argparse
from src.preprocessor.preprocessor import Preprocessor
from src.common.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Social trends preprocessor")
    parser.add_argument("--input-queue", default="raw_posts")
    parser.add_argument("--output-queue", default="enriched_posts")
    parser.add_argument("--batch-size", type=int)
    
    args = parser.parse_args()
    
    preprocessor = Preprocessor()
    preprocessor.process_queue(
        input_queue=args.input_queue,
        output_queue=args.output_queue,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()

