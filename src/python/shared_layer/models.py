"""Pydantic models for data validation and type safety."""
from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


class NewsSource(str, Enum):
    """Supported news sources."""
    ZERODHA = "ZERODHA"


class Direction(str, Enum):
    """Trading direction bias."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class EventType(str, Enum):
    """Types of market events."""
    EARNINGS = "Earnings"
    ORDER = "Order"
    REGULATORY = "Regulatory"
    MACRO = "Macro"
    OTHER = "Other"


class Priority(str, Enum):
    """Watchlist priority levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NewsItem(BaseModel):
    """Model for news items."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: NewsSource
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    published_at: datetime
    stock_symbol: Optional[str] = Field(None, max_length=20)
    url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    dedup_hash: Optional[str] = None

    class Config:
        """Pydantic config."""
        use_enum_values = True

    @validator('stock_symbol')
    def validate_stock_symbol(cls, v):
        """Validate stock symbol format."""
        if v and not v.isupper():
            return v.upper()
        return v


class AnalysisResult(BaseModel):
    """Model for AI analysis results."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    news_id: str
    stock_symbol: str = Field(..., max_length=20)
    event_type: EventType
    direction: Direction
    impact_strength: int = Field(..., ge=1, le=5)
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(..., min_length=1, max_length=200)
    bias_score: float = Field(..., ge=0.0, le=5.0)
    news_published_at: datetime  # When the news was originally published
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic config."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    @validator('bias_score', pre=True, always=True)
    def calculate_bias_score(cls, v, values):
        """Calculate bias score if not provided."""
        if v is None and 'impact_strength' in values and 'confidence' in values:
            return values['impact_strength'] * values['confidence']
        return v

    @validator('stock_symbol')
    def validate_stock_symbol(cls, v):
        """Validate stock symbol format."""
        return v.upper() if v else v


class WatchlistItem(BaseModel):
    """Model for watchlist items."""
    stock_symbol: str = Field(..., max_length=20)
    direction: Direction
    priority: Priority
    bias_score: float = Field(..., ge=0.0, le=5.0)
    reason: str = Field(..., min_length=1, max_length=200)
    news_count: int = Field(..., ge=1)
    sector: Optional[str] = Field(None, max_length=50)
    latest_news_datetime: datetime  # Most recent news datetime
    date: str = Field(...)  # YYYY-MM-DD format (kept for backward compatibility)

    class Config:
        """Pydantic config."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    @validator('stock_symbol')
    def validate_stock_symbol(cls, v):
        """Validate stock symbol format."""
        return v.upper() if v else v


class LLMAnalysisRequest(BaseModel):
    """Model for LLM analysis request."""
    news_content: str
    stock_symbol: str
    news_title: Optional[str] = None


class LLMAnalysisResponse(BaseModel):
    """Model for LLM analysis response."""
    event_type: str
    direction: str
    impact_strength: int = Field(..., ge=1, le=5)
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str

    @validator('event_type')
    def validate_event_type(cls, v):
        """Validate event type."""
        valid_types = [e.value for e in EventType]
        if v not in valid_types:
            return EventType.OTHER.value
        return v

    @validator('direction')
    def validate_direction(cls, v):
        """Validate direction."""
        v_upper = v.upper()
        valid_directions = [d.value for d in Direction]
        if v_upper not in valid_directions:
            return Direction.NEUTRAL.value
        return v_upper
