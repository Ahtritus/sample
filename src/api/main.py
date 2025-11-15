"""Internal API for status, topics, and search."""
from fastapi import FastAPI, HTTPException, Header, Query
from typing import Optional, List
from datetime import datetime, timedelta
from src.common.config import settings
from src.common.logger import setup_logger
from src.common.es_client import ESClient
from src.common.redis_client import RedisClient
from src.common.metrics import errors_total
import json

logger = setup_logger(__name__)

app = FastAPI(title="Social Trends API")
es = ESClient()
redis = RedisClient()


def verify_token(authorization: Optional[str] = Header(None)):
    """Verify API token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = authorization.replace("Bearer ", "")
    if token != settings.API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
    
    return token


@app.get("/health")
def health_check():
    """Health check endpoint."""
    es_healthy = es.health_check()
    return {
        "status": "healthy" if es_healthy else "degraded",
        "elasticsearch": "healthy" if es_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/start-fetch")
def start_fetch(authorization: Optional[str] = Header(None)):
    """Start fetcher (dev only)."""
    verify_token(authorization)
    # In production, this would trigger a background job
    return {"message": "Fetcher started", "status": "ok"}


@app.get("/status")
def get_status(authorization: Optional[str] = Header(None)):
    """Get pipeline health status."""
    verify_token(authorization)
    
    try:
        # Get queue sizes
        raw_queue_size = redis.queue_length("raw_posts")
        enriched_queue_size = redis.queue_length("enriched_posts")
        
        # Get last cursor (example for first subreddit)
        subreddits = settings.SUBREDDITS.split(",")
        last_cursor = None
        if subreddits:
            cursor_key = f"cursor:reddit:{subreddits[0].strip()}"
            last_cursor = redis.get_cursor(cursor_key)
        
        return {
            "status": "running",
            "queues": {
                "raw_posts": raw_queue_size,
                "enriched_posts": enriched_queue_size
            },
            "last_cursor": last_cursor,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        errors_total.labels(component="api", error_type="status_error").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topics")
def get_topics(
    since: Optional[str] = Query(None, description="ISO datetime"),
    limit: int = Query(20, ge=1, le=100),
    authorization: Optional[str] = Header(None)
):
    """Get topics list with volume and keywords."""
    verify_token(authorization)
    
    try:
        query = {
            "query": {
                "match_all": {}
            },
            "sort": [{"volume": {"order": "desc"}}],
            "size": limit
        }
        
        if since:
            query["query"] = {
                "range": {
                    "created_at": {
                        "gte": since
                    }
                }
            }
        
        topics = es.search(query, index_pattern="topics-v1-*", size=limit)
        
        return {
            "topics": topics,
            "count": len(topics)
        }
    except Exception as e:
        logger.error(f"Error getting topics: {e}")
        errors_total.labels(component="api", error_type="topics_error").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topic/{topic_id}")
def get_topic(
    topic_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get topic metadata with time series."""
    verify_token(authorization)
    
    try:
        # Get topic
        topic_query = {
            "query": {
                "term": {"topic_id": topic_id}
            }
        }
        topics = es.search(topic_query, index_pattern="topics-v1-*", size=1)
        
        if not topics:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        topic = topics[0]
        
        # Get posts for this topic
        posts_query = {
            "query": {
                "term": {"topic_id": topic_id}
            },
            "sort": [{"created_at": {"order": "desc"}}],
            "size": 100
        }
        posts = es.search(posts_query, index_pattern="socialposts-v1-*", size=100)
        
        # Aggregate time series (hourly)
        from collections import defaultdict
        time_series = defaultdict(lambda: {"volume": 0, "sentiment_sum": 0.0, "count": 0})
        
        for post in posts:
            created_at = post.get("created_at")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    hour_key = dt.strftime("%Y-%m-%dT%H:00:00")
                    time_series[hour_key]["volume"] += 1
                    time_series[hour_key]["sentiment_sum"] += post.get("sentiment_score", 0.0)
                    time_series[hour_key]["count"] += 1
                except:
                    pass
        
        # Compute avg sentiment per hour
        series_data = []
        for hour, data in sorted(time_series.items()):
            avg_sentiment = data["sentiment_sum"] / data["count"] if data["count"] > 0 else 0.0
            series_data.append({
                "time": hour,
                "volume": data["volume"],
                "avg_sentiment": avg_sentiment
            })
        
        return {
            "topic": topic,
            "time_series": series_data,
            "sample_posts": posts[:10]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic: {e}")
        errors_total.labels(component="api", error_type="topic_detail_error").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
def search_posts(
    q: str = Query(..., description="Search query"),
    from_time: Optional[str] = Query(None, alias="from", description="ISO datetime"),
    to_time: Optional[str] = Query(None, alias="to", description="ISO datetime"),
    limit: int = Query(50, ge=1, le=200),
    authorization: Optional[str] = Header(None)
):
    """Search posts."""
    verify_token(authorization)
    
    try:
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": q,
                                "fields": ["text", "keywords"],
                                "type": "best_fields"
                            }
                        }
                    ]
                }
            },
            "sort": [{"created_at": {"order": "desc"}}],
            "size": limit
        }
        
        # Add time range if provided
        if from_time or to_time:
            range_query = {}
            if from_time:
                range_query["gte"] = from_time
            if to_time:
                range_query["lte"] = to_time
            
            query["query"]["bool"]["must"].append({
                "range": {"created_at": range_query}
            })
        
        posts = es.search(query, index_pattern="socialposts-v1-*", size=limit)
        
        return {
            "posts": posts,
            "count": len(posts),
            "query": q
        }
    except Exception as e:
        logger.error(f"Error searching posts: {e}")
        errors_total.labels(component="api", error_type="search_error").inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reindex-topic/{topic_id}")
def reindex_topic(
    topic_id: str,
    authorization: Optional[str] = Header(None)
):
    """Re-run topic extraction for a topic (admin)."""
    verify_token(authorization)
    
    # In production, this would trigger a background job
    return {
        "message": f"Reindexing topic {topic_id}",
        "status": "queued"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)

