"""Prometheus metrics for monitoring."""
from prometheus_client import Counter, Histogram, Gauge

# Fetch metrics
fetch_requests_total = Counter(
    'fetch_requests_total',
    'Total number of fetch requests',
    ['platform', 'status']
)

fetch_duration_seconds = Histogram(
    'fetch_duration_seconds',
    'Time spent fetching posts',
    ['platform']
)

# Processing metrics
posts_processed_total = Counter(
    'posts_processed_total',
    'Total number of posts processed',
    ['status']
)

processing_duration_seconds = Histogram(
    'processing_duration_seconds',
    'Time spent processing posts'
)

# Indexing metrics
posts_indexed_total = Counter(
    'posts_indexed_total',
    'Total number of posts indexed',
    ['status']
)

indexing_duration_seconds = Histogram(
    'indexing_duration_seconds',
    'Time spent indexing posts'
)

# Queue metrics
queue_size = Gauge(
    'queue_size',
    'Current size of processing queue'
)

# Error metrics
errors_total = Counter(
    'errors_total',
    'Total number of errors',
    ['component', 'error_type']
)

