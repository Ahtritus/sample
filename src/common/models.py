"""Data models for social posts and topics."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Engagement(BaseModel):
    """Engagement metrics for a post."""
    score: int = 0
    comments: int = 0
    likes: int = 0


class SocialPost(BaseModel):
    """Enriched social post model."""
    platform: str
    post_id: str
    canonical_id: str
    created_at: datetime
    ingest_ts: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    user_name: str
    user_followers: int = 0
    text: str
    language: str = "en"
    sentiment_score: float = 0.0
    sentiment_label: str = "neutral"
    topics: List[str] = []
    topic_id: Optional[str] = None
    keywords: List[str] = []
    entities: List[str] = []
    region: Optional[str] = None
    geo_point: Optional[Dict[str, float]] = None
    is_bot_score: float = 0.0
    engagement: Engagement = Field(default_factory=Engagement)
    raw: Dict[str, Any] = {}
    
    def to_es_doc(self) -> Dict[str, Any]:
        """Convert to Elasticsearch document format."""
        doc = self.dict(exclude_none=True)
        # Convert datetime to ISO format
        doc["created_at"] = self.created_at.isoformat()
        doc["ingest_ts"] = self.ingest_ts.isoformat()
        return doc


class Topic(BaseModel):
    """Topic model for clustering results."""
    topic_id: str
    keywords: List[str]
    top_keywords: List[str]
    volume: int
    velocity: float = 0.0
    avg_sentiment: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    sample_posts: List[Dict[str, Any]] = []
    
    def to_es_doc(self) -> Dict[str, Any]:
        """Convert to Elasticsearch document format."""
        doc = self.dict(exclude_none=True)
        doc["created_at"] = self.created_at.isoformat()
        doc["updated_at"] = self.updated_at.isoformat()
        return doc

