"""NLP processing: sentiment, keywords, language detection."""
import re
from typing import List, Dict, Any, Tuple
from textblob import TextBlob
from langdetect import detect, LangDetectException
from rake_nltk import Rake
import nltk
from src.common.logger import setup_logger

logger = setup_logger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


class NLPProcessor:
    """NLP processing utilities."""
    
    def __init__(self):
        """Initialize NLP processor."""
        self.rake = Rake()
        logger.info("Initialized NLP processor")
    
    def normalize_text(self, text: str) -> str:
        """Normalize text: strip URLs, collapse whitespace."""
        if not text:
            return ""
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove Reddit-specific patterns
        text = re.sub(r'/r/\w+', '', text)
        text = re.sub(r'/u/\w+', '', text)
        
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Strip
        text = text.strip()
        
        return text
    
    def detect_language(self, text: str) -> str:
        """Detect language of text."""
        if not text or len(text) < 10:
            return "en"
        
        try:
            lang = detect(text)
            return lang
        except LangDetectException:
            return "en"
    
    def compute_sentiment(self, text: str) -> Tuple[float, str]:
        """Compute sentiment score and label."""
        if not text:
            return 0.0, "neutral"
        
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            # Convert to label
            if polarity > 0.1:
                label = "positive"
            elif polarity < -0.1:
                label = "negative"
            else:
                label = "neutral"
            
            return float(polarity), label
        except Exception as e:
            logger.warning(f"Sentiment computation failed: {e}")
            return 0.0, "neutral"
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords using RAKE."""
        if not text or len(text) < 20:
            return []
        
        try:
            self.rake.extract_keywords_from_text(text)
            keywords = self.rake.get_ranked_phrases()[:max_keywords]
            # Clean and normalize keywords
            keywords = [k.lower().strip() for k in keywords if len(k) > 2]
            return keywords
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return []
    
    def infer_region(self, text: str, language: str, user_location: str = None) -> str:
        """Infer region from text, language, or user location."""
        # Simple heuristic: use language as region indicator
        # In production, use geocoding API or user profile data
        lang_to_region = {
            "en": "US",
            "es": "ES",
            "fr": "FR",
            "de": "DE",
            "ja": "JP",
            "zh": "CN",
        }
        
        if user_location:
            # Try to extract country from user location
            return user_location
        
        return lang_to_region.get(language, "UNKNOWN")
    
    def compute_bot_score(self, text: str, user_name: str, user_followers: int) -> float:
        """Compute bot likelihood score (0.0 = human, 1.0 = bot)."""
        score = 0.0
        
        # Heuristics for bot detection
        if not text or len(text) < 10:
            score += 0.3
        
        if user_followers == 0:
            score += 0.2
        
        # Check for bot-like patterns
        if user_name and any(pattern in user_name.lower() for pattern in ["bot", "auto", "spam"]):
            score += 0.5
        
        # Repetitive text
        if text and len(set(text.split())) < 5:
            score += 0.3
        
        return min(score, 1.0)

