# Real-Time Social Trend & Sentiment Analyzer (MVP)

An end-to-end system that ingests social posts from Reddit, identifies trending topics, computes sentiment, and visualizes results in Kibana dashboards.

## Architecture

```
┌─────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐     ┌─────────┐
│ Reddit  │───> │   Fetcher    │───> │Preprocessor │───> │ Indexer  │───> │Elastic- │
│   API   │     │              │     │             │     │          │     │ search  │
└─────────┘     └──────────────┘     └─────────────┘     └──────────┘     └─────────┘
                      │                     │                   │                │
                      │                     │                   │                │
                      v                     v                   v                v
                  ┌───────┐            ┌───────┐          ┌───────┐       ┌─────────┐
                  │ Redis │            │ Redis │          │ Redis │       │ Kibana  │
                  │ Queue │            │ Queue │          │ Queue │       │         │
                  └───────┘            └───────┘          └───────┘       └─────────┘
                                                                                │
                                                                                v
                                                                          ┌──────────┐
                                                                          │   API    │
                                                                          │          │
                                                                          └──────────┘
                                                                                │
                                                                                v
                                                                          ┌──────────┐
                                                                          │ Topic    │
                                                                          │Extractor │
                                                                          └──────────┘
```

## Components

1. **Fetcher**: Polls Reddit API, handles rate limits, persists cursor
2. **Preprocessor**: Normalizes text, detects language, generates canonical_id, deduplicates, computes sentiment
3. **Indexer**: Bulk writes enriched posts to Elasticsearch
4. **Topic Extractor**: TF-IDF + k-means clustering, runs periodically
5. **API**: Internal HTTP endpoints for status, topics, search
6. **Kibana Dashboard**: Time-series, word cloud, sample posts visualization

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Reddit API credentials (client ID and secret)
- Elasticsearch 8.x
- Redis

## Quick Start

### 1. Clone and Setup

```bash
git clone <repo-url>
cd social-trends-analyzer
```

### 2. Configure Environment

**First, get your Reddit API credentials:**
- See [docs/REDDIT_API_SETUP.md](docs/REDDIT_API_SETUP.md) for detailed instructions
- Quick version: Go to https://www.reddit.com/prefs/apps and create a "script" type app
- Copy your Client ID and Client Secret

**Then configure your environment:**

```bash
cp .env.example .env
```

Edit `.env` with your Reddit credentials:
```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=SocialTrendsBot/1.0
SUBREDDITS=technology,programming,python,webdev
```

### 3. Start Infrastructure

Start Elasticsearch, Kibana, and Redis:

```bash
docker-compose up -d
```

Wait for services to be healthy (check with `docker-compose ps`).

### 4. Setup Elasticsearch

Create index templates and ILM policies:

```bash
python scripts/setup_es.py
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Run Services

#### Option A: Run All Services (Development)

```bash
python scripts/run_all.py
```

#### Option B: Run Services Individually

Terminal 1 - Fetcher:
```bash
python -m src.fetcher.main
```

Terminal 2 - Preprocessor:
```bash
python -m src.preprocessor.main
```

Terminal 3 - Indexer:
```bash
python -m src.indexer.main
```

Terminal 4 - Topic Extractor:
```bash
python -m src.topic_extractor.main
```

Terminal 5 - API:
```bash
python -m src.api.main
```

### 7. Setup Kibana Dashboard

1. Open Kibana: http://localhost:5601
2. Go to Stack Management > Saved Objects
3. Import `config/kibana_dashboard.json`
4. Create index patterns:
   - `socialposts-v1-*` (time field: `created_at`)
   - `topics-v1-*` (time field: `created_at`)
5. Open the "Social Trends & Sentiment Dashboard"

## API Endpoints

All endpoints require authentication via Bearer token in the `Authorization` header.

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "elasticsearch": "healthy",
  "timestamp": "2024-01-01T00:00:00"
}
```

### Pipeline Status

```bash
GET /status
Authorization: Bearer <token>
```

Response:
```json
{
  "status": "running",
  "queues": {
    "raw_posts": 10,
    "enriched_posts": 5
  },
  "last_cursor": "2024-01-01T12:00:00",
  "timestamp": "2024-01-01T12:05:00"
}
```

### Get Topics

```bash
GET /topics?since=2024-01-01T00:00:00&limit=20
Authorization: Bearer <token>
```

Response:
```json
{
  "topics": [
    {
      "topic_id": "topic_0_1234567890",
      "keywords": ["python", "programming", "tutorial"],
      "top_keywords": ["python", "programming"],
      "volume": 150,
      "avg_sentiment": 0.65,
      "sample_posts": [...]
    }
  ],
  "count": 1
}
```

### Get Topic Details

```bash
GET /topic/{topic_id}
Authorization: Bearer <token>
```

Response:
```json
{
  "topic": {...},
  "time_series": [
    {
      "time": "2024-01-01T10:00:00",
      "volume": 25,
      "avg_sentiment": 0.7
    }
  ],
  "sample_posts": [...]
}
```

### Search Posts

```bash
GET /search?q=python&from=2024-01-01T00:00:00&to=2024-01-01T23:59:59&limit=50
Authorization: Bearer <token>
```

Response:
```json
{
  "posts": [...],
  "count": 50,
  "query": "python"
}
```

### Start Fetcher (Dev)

```bash
POST /start-fetch
Authorization: Bearer <token>
```

### Reindex Topic (Admin)

```bash
POST /reindex-topic/{topic_id}
Authorization: Bearer <token>
```

## Data Model

### Social Post Document

```json
{
  "platform": "reddit",
  "post_id": "abc123",
  "canonical_id": "sha256_hash",
  "created_at": "2024-01-01T12:00:00",
  "ingest_ts": "2024-01-01T12:01:00",
  "user_id": "user123",
  "user_name": "username",
  "user_followers": 100,
  "text": "Normalized post text",
  "language": "en",
  "sentiment_score": 0.65,
  "sentiment_label": "positive",
  "topics": ["topic_0_1234567890"],
  "topic_id": "topic_0_1234567890",
  "keywords": ["python", "programming"],
  "entities": [],
  "region": "US",
  "is_bot_score": 0.1,
  "engagement": {
    "score": 50,
    "comments": 10,
    "likes": 40
  }
}
```

### Topic Document

```json
{
  "topic_id": "topic_0_1234567890",
  "keywords": ["python", "programming", "tutorial"],
  "top_keywords": ["python", "programming"],
  "volume": 150,
  "velocity": 0.25,
  "avg_sentiment": 0.65,
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:10:00",
  "sample_posts": [...]
}
```

## Configuration

Key environment variables:

- `REDDIT_CLIENT_ID`: Reddit API client ID
- `REDDIT_CLIENT_SECRET`: Reddit API client secret
- `SUBREDDITS`: Comma-separated list of subreddits to monitor
- `FETCH_INTERVAL_SEC`: Fetch interval in seconds (default: 60)
- `TOPIC_EXTRACT_INTERVAL_MIN`: Topic extraction interval in minutes (default: 10)
- `BATCH_SIZE`: Processing batch size (default: 500)
- `ES_HOST`: Elasticsearch host (default: localhost)
- `REDIS_HOST`: Redis host (default: localhost)
- `API_TOKEN`: API authentication token

## Monitoring

### Metrics (Prometheus)

- `fetch_requests_total`: Total fetch requests by platform and status
- `fetch_duration_seconds`: Fetch duration histogram
- `posts_processed_total`: Processed posts by status
- `posts_indexed_total`: Indexed posts by status
- `queue_size`: Current queue size
- `errors_total`: Errors by component and type

### Logs

All services log to stdout with structured logging:
- Timestamp
- Component name
- Log level
- Message

### Alerts (Recommended)

Set up alerts for:
- Queue backlog > 1000 items
- Sustained fetch failures (> 5 consecutive)
- Elasticsearch bulk index failures > 10%
- Topic extraction failures

## Development

### Project Structure

```
.
├── src/
│   ├── common/          # Shared utilities
│   ├── fetcher/         # Reddit API fetcher
│   ├── preprocessor/    # NLP and enrichment
│   ├── indexer/         # Elasticsearch indexing
│   ├── topic_extractor/ # Topic clustering
│   └── api/             # HTTP API
├── config/              # ES templates, Kibana dashboards
├── scripts/             # Setup and utility scripts
├── docker-compose.yml   # Infrastructure services
└── requirements.txt     # Python dependencies
```

### Running Tests

```bash
# Unit tests (when implemented)
pytest tests/

# Integration test
python -m src.fetcher.main --once
python -m src.topic_extractor.main --once
```

### Docker Build

```bash
# Build all services
docker build -f Dockerfile.fetcher -t social-trends-fetcher .
docker build -f Dockerfile.preprocessor -t social-trends-preprocessor .
docker build -f Dockerfile.indexer -t social-trends-indexer .
docker build -f Dockerfile.topic_extractor -t social-trends-topic-extractor .
docker build -f Dockerfile.api -t social-trends-api .
```

## Production Deployment

### Kubernetes

1. Create secrets for API credentials
2. Deploy Elasticsearch cluster (or use managed service)
3. Deploy Redis cluster
4. Deploy services as Kubernetes deployments
5. Configure service monitoring and alerts

### Environment Variables

Use a secrets manager (Vault, AWS SSM, GCP Secret Manager) for:
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `API_TOKEN`
- `ES_USERNAME` / `ES_PASSWORD` (if using secured ES)

### Scaling

- **Fetcher**: Single instance (rate limits)
- **Preprocessor**: Scale horizontally (stateless)
- **Indexer**: Scale horizontally (stateless)
- **Topic Extractor**: Single instance or scheduled job
- **API**: Scale horizontally (stateless)

## Troubleshooting

### Elasticsearch Connection Issues

```bash
# Check ES health
curl http://localhost:9200/_cluster/health

# Check indices
curl http://localhost:9200/_cat/indices?v
```

### Redis Connection Issues

```bash
# Test Redis connection
redis-cli ping
```

### No Posts Being Fetched

1. Check Reddit API credentials
2. Verify subreddit names are correct
3. Check fetcher logs for rate limit errors
4. Verify cursor persistence in Redis

### Topics Not Appearing

1. Ensure enough posts are indexed (minimum 5 per topic)
2. Check topic extractor logs
3. Verify topic extractor is running periodically
4. Check ES topics index: `curl http://localhost:9200/topics-v1-*/_search`

## Limitations (MVP Scope)

- Single platform (Reddit only)
- Basic sentiment analysis (TextBlob)
- Simple bot detection (heuristics)
- No image/video analysis
- No predictive modeling
- 30-day retention only

## Future Enhancements

- Multi-platform support (Twitter/X)
- Advanced NLP models (BERT, GPT-based sentiment)
- Real-time streaming (Kafka)
- Advanced bot detection (ML models)
- Geographic heatmaps
- Predictive trend forecasting
- User demographic modeling

## License

See LICENSE file.

## Support

For issues and questions, please open a GitHub issue.

