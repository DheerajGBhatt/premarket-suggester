"""Tests for Pydantic models."""
import pytest
from datetime import datetime
from src.shared_layer.models import NewsItem, AnalysisResult, WatchlistItem, NewsSource, Direction, Priority, EventType


class TestNewsItem:
    """Tests for NewsItem model."""

    def test_news_item_creation(self):
        """Test creating a valid NewsItem."""
        news = NewsItem(
            source=NewsSource.NSE,
            title="Test News Title",
            content="Test news content with details",
            published_at=datetime.utcnow(),
            stock_symbol="TATASTEEL",
            url="https://example.com/news"
        )

        assert news.source == NewsSource.NSE.value
        assert news.title == "Test News Title"
        assert news.stock_symbol == "TATASTEEL"
        assert news.id is not None

    def test_stock_symbol_uppercase(self):
        """Test that stock symbol is converted to uppercase."""
        news = NewsItem(
            source=NewsSource.NSE,
            title="Test",
            content="Test content",
            published_at=datetime.utcnow(),
            stock_symbol="infy",
            url="https://example.com"
        )

        assert news.stock_symbol == "INFY"


class TestAnalysisResult:
    """Tests for AnalysisResult model."""

    def test_analysis_result_creation(self):
        """Test creating a valid AnalysisResult."""
        analysis = AnalysisResult(
            news_id="news-123",
            stock_symbol="INFY",
            event_type=EventType.EARNINGS,
            direction=Direction.BULLISH,
            impact_strength=4,
            confidence=0.85,
            rationale="Strong earnings beat",
            bias_score=3.4
        )

        assert analysis.stock_symbol == "INFY"
        assert analysis.direction == Direction.BULLISH.value
        assert analysis.bias_score == 3.4

    def test_bias_score_calculation(self):
        """Test automatic bias score calculation."""
        analysis = AnalysisResult(
            news_id="news-123",
            stock_symbol="INFY",
            event_type=EventType.EARNINGS,
            direction=Direction.BULLISH,
            impact_strength=4,
            confidence=0.75,
            rationale="Good results"
        )

        # bias_score should be calculated as impact_strength * confidence
        assert analysis.bias_score == 4 * 0.75

    def test_impact_strength_validation(self):
        """Test that impact strength must be between 1 and 5."""
        with pytest.raises(ValueError):
            AnalysisResult(
                news_id="news-123",
                stock_symbol="INFY",
                event_type=EventType.EARNINGS,
                direction=Direction.BULLISH,
                impact_strength=6,  # Invalid
                confidence=0.85,
                rationale="Test",
                bias_score=5.1
            )


class TestWatchlistItem:
    """Tests for WatchlistItem model."""

    def test_watchlist_item_creation(self):
        """Test creating a valid WatchlistItem."""
        item = WatchlistItem(
            stock_symbol="TATASTEEL",
            direction=Direction.BULLISH,
            priority=Priority.HIGH,
            bias_score=4.25,
            reason="Strong earnings with margin expansion",
            news_count=3,
            date="2024-01-12"
        )

        assert item.stock_symbol == "TATASTEEL"
        assert item.direction == Direction.BULLISH.value
        assert item.priority == Priority.HIGH.value
        assert item.news_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
