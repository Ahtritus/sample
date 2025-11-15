"""Run all services in development mode."""
import subprocess
import sys
import time
import signal
from pathlib import Path

processes = []


def signal_handler(sig, frame):
    """Handle shutdown signal."""
    print("\nShutting down services...")
    for proc in processes:
        proc.terminate()
    for proc in processes:
        proc.wait()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Run all services."""
    root = Path(__file__).parent.parent
    
    # Start services
    services = [
        ("fetcher", ["python", "-m", "src.fetcher.main"]),
        ("preprocessor", ["python", "-m", "src.preprocessor.main"]),
        ("indexer", ["python", "-m", "src.indexer.main"]),
        ("topic_extractor", ["python", "-m", "src.topic_extractor.main"]),
        ("api", ["python", "-m", "src.api.main"]),
    ]
    
    print("Starting services...")
    for name, cmd in services:
        print(f"Starting {name}...")
        proc = subprocess.Popen(
            cmd,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(proc)
        time.sleep(2)
    
    print("All services started. Press Ctrl+C to stop.")
    
    # Wait for processes
    for proc in processes:
        proc.wait()


if __name__ == "__main__":
    main()

