"""Main entry point for fetcher service."""
import argparse
import sys
from src.fetcher.reddit_fetcher import RedditFetcher
from src.common.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Social trends fetcher")
    parser.add_argument("--platform", default="reddit", choices=["reddit"])
    parser.add_argument("--subreddits", help="Comma-separated list of subreddits")
    parser.add_argument("--once", action="store_true", help="Run once instead of continuous")
    
    args = parser.parse_args()
    
    fetcher = RedditFetcher()
    
    if args.subreddits:
        fetcher.subreddits = [s.strip() for s in args.subreddits.split(",")]
    
    if args.once:
        # Run once and exit
        posts = fetcher.fetch_all_subreddits()
        logger.info(f"Fetched {len(posts)} posts total")
        for post in posts:
            print(f"Post: {post.get('post_id')} from r/{post.get('subreddit')}")
    else:
        # Run continuously
        fetcher.run_continuous()


if __name__ == "__main__":
    main()

