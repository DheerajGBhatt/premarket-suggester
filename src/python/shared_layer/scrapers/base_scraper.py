"""Base scraper class for news sources using RSS feeds."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
import feedparser
from aws_lambda_powertools import Logger
from shared_layer.models import NewsSource
from shared_layer.utils import sanitize_text, extract_stock_symbols_with_llm

logger = Logger(child=True)


class BaseScraper(ABC):
    """Abstract base class for RSS-based news scrapers."""

    def __init__(self):
        """Initialize base scraper."""
        import os
        self.timeout = 30
        # Maximum items to fetch per source (reduced to prevent timeouts)
        self.max_items = int(os.environ.get('MAX_NEWS_ITEMS', '10'))

    @abstractmethod
    def fetch_news(self) -> List[Dict[str, Any]]:
        """Fetch news from the RSS feed.

        Returns:
            list: List of news dictionaries
        """
        pass

    def parse_rss_feed(self, rss_url: str, source: NewsSource) -> List[Dict[str, Any]]:
        """Parse RSS feed and return structured news items.

        Args:
            rss_url: RSS feed URL
            source: News source identifier

        Returns:
            list: List of news dictionaries
        """
        news_items = []

        try:
            # Parse RSS feed
            logger.info(f"Fetching RSS feed from {rss_url}")
            feed = feedparser.parse(rss_url)

            if feed.bozo:
                logger.warning(f"Feed parsing warning for {rss_url}: {feed.bozo_exception}")

            # Process entries
            for entry in feed.entries[:self.max_items]:
                try:
                    # Extract title
                    title = entry.get('title', '').strip()
                    if not title:
                        continue

                    # Extract content (try multiple fields)
                    content = (
                        entry.get('summary', '') or
                        entry.get('description', '') or
                        entry.get('content', [{}])[0].get('value', '') or
                        title
                    )

                    # Parse published date
                    published_at = datetime.utcnow()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published_at = datetime(*entry.published_parsed[:6])
                        except Exception as e:
                            logger.warning(f"Error parsing date: {e}")
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        try:
                            published_at = datetime(*entry.updated_parsed[:6])
                        except Exception as e:
                            logger.warning(f"Error parsing date: {e}")

                    # Extract URL
                    url = entry.get('link', '')

                    # Extract stock symbols from title and content using LLM
                    symbols = extract_stock_symbols_with_llm(title, content)
                    stock_symbol = symbols[0] if symbols else None

                    # Create news item
                    news_item = {
                        'source': source.value,
                        'title': sanitize_text(title),
                        'content': sanitize_text(content),
                        'published_at': published_at,
                        'stock_symbol': stock_symbol,
                        'url': url
                    }

                    news_items.append(news_item)

                except Exception as e:
                    logger.warning(f"Error parsing RSS entry: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching RSS feed from {rss_url}: {str(e)}")

        logger.info(f"Fetched {len(news_items)} items from {source.value}")
        return news_items
