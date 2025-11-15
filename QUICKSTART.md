# Quick Start Guide

Get the social trends analyzer running in 5 minutes.

## Prerequisites Check

- [ ] Python 3.11+ installed
- [ ] Docker & Docker Compose installed
- [ ] Reddit API credentials (see [docs/REDDIT_API_SETUP.md](docs/REDDIT_API_SETUP.md) for detailed instructions)

## Step-by-Step Setup

### 1. Start Infrastructure (2 minutes)

```bash
docker-compose up -d
```

Wait for services to be ready:
```bash
# Check Elasticsearch
curl http://localhost:9200/_cluster/health

# Check Kibana (open in browser)
open http://localhost:5601
```

### 2. Get Reddit API Credentials (2 minutes)

**Quick Steps:**
1. Go to https://www.reddit.com/prefs/apps
2. Click **"create another app..."** at the bottom
3. Fill in:
   - **Name**: `SocialTrendsBot`
   - **Type**: Select **"script"**
   - **Redirect URI**: `http://localhost:8080` (required but not used)
4. Click **"create app"**
5. Copy your **Client ID** (under the app name) and **Client Secret** (the "secret" field)

**⚠️ Important**: The Client Secret is only shown once! Save it immediately.

**For detailed instructions, see [docs/REDDIT_API_SETUP.md](docs/REDDIT_API_SETUP.md)**

### 3. Configure Environment (1 minute)

```bash
cp .env.example .env
```

Edit `.env` and add your Reddit credentials:
```env
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_secret_here
REDDIT_USER_AGENT=SocialTrendsBot/1.0
```

### 4. Install Dependencies (1 minute)

```bash
pip install -r requirements.txt
```

### 5. Setup Elasticsearch (30 seconds)

```bash
python scripts/setup_es.py
```

You should see:
```
Created index template: socialposts-v1-template
Created index template: topics-v1-template
Created ILM policy: socialposts-policy
Elasticsearch setup completed
```

### 6. Test the Pipeline (1 minute)

```bash
python scripts/test_pipeline.py
```

This will:
- Create sample posts
- Process them through the pipeline
- Index them to Elasticsearch

### 7. Run Services

Open 5 terminal windows:

**Terminal 1 - Fetcher:**
```bash
python -m src.fetcher.main
```

**Terminal 2 - Preprocessor:**
```bash
python -m src.preprocessor.main
```

**Terminal 3 - Indexer:**
```bash
python -m src.indexer.main
```

**Terminal 4 - Topic Extractor:**
```bash
python -m src.topic_extractor.main
```

**Terminal 5 - API:**
```bash
python -m src.api.main
```

### 8. Setup Kibana Dashboard

1. Open http://localhost:5601
2. Go to **Stack Management** > **Saved Objects**
3. Click **Import** and select `config/kibana_dashboard.json`
4. Create index patterns:
   - Go to **Stack Management** > **Index Patterns**
   - Create pattern: `socialposts-v1-*` (time field: `created_at`)
   - Create pattern: `topics-v1-*` (time field: `created_at`)
5. Open **Dashboard** and select "Social Trends & Sentiment Dashboard"

### 9. Verify It's Working

Check the API:
```bash
curl http://localhost:8000/health
```

Check status:
```bash
curl -H "Authorization: Bearer dev-token-change-in-prod" http://localhost:8000/status
```

## Troubleshooting

### Elasticsearch not responding
```bash
docker-compose logs elasticsearch
docker-compose restart elasticsearch
```

### Redis connection error
```bash
docker-compose logs redis
redis-cli ping
```

### No posts being fetched
- Check Reddit API credentials in `.env`
- Verify subreddit names are correct
- Check fetcher logs for rate limit errors

### Topics not appearing
- Wait 10-15 minutes for topic extractor to run
- Ensure at least 5 posts are indexed
- Check topic extractor logs

## Next Steps

- Monitor the dashboard in Kibana
- Adjust subreddits in `.env`
- Explore the API endpoints (see README.md)
- Set up monitoring alerts

## Production Deployment

For production:
1. Use a secrets manager for API credentials
2. Deploy to Kubernetes or use managed services
3. Set up proper monitoring and alerts
4. Configure ILM policies for retention
5. Scale services based on load

See README.md for detailed documentation.

