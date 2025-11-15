"""Configuration management for the social trends analyzer."""
import os
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    # Platform API
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "SocialTrendsBot/1.0")
    
    # Elasticsearch
    ES_HOST: str = os.getenv("ES_HOST", "localhost")
    ES_PORT: int = int(os.getenv("ES_PORT", "9200"))
    ES_USE_SSL: bool = os.getenv("ES_USE_SSL", "false").lower() == "true"
    ES_USERNAME: Optional[str] = os.getenv("ES_USERNAME")
    ES_PASSWORD: Optional[str] = os.getenv("ES_PASSWORD")
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Processing
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "500"))
    FETCH_INTERVAL_SEC: int = int(os.getenv("FETCH_INTERVAL_SEC", "60"))
    TOPIC_EXTRACT_INTERVAL_MIN: int = int(os.getenv("TOPIC_EXTRACT_INTERVAL_MIN", "10"))
    
    # Subreddits to monitor
    SUBREDDITS: str = os.getenv("SUBREDDITS", "technology,programming,python,webdev")
    
    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_TOKEN: str = os.getenv("API_TOKEN", "dev-token-change-in-prod")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

