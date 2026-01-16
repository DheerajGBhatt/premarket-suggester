"""Zerodha Pulse news scraper using RSS feed."""
from typing import List, Dict, Any
from datetime import datetime
import feedparser
from .base_scraper import BaseScraper, logger
from shared_layer.models import NewsSource
from shared_layer.utils import sanitize_text, extract_stock_symbols_with_llm


class ZerodhaScraper(BaseScraper):
    """Scraper for Zerodha Pulse Indian stock market news.

    Zerodha Pulse aggregates news from multiple Indian sources.
    Some items have descriptions, others only have titles.
    """

    def __init__(self):
        """Initialize Zerodha Pulse scraper."""
        super().__init__()
        # Zerodha Pulse RSS feed
        self.rss_feeds = [
            "https://pulse.zerodha.com/feed.php"  # Zerodha Pulse aggregated news
        ]

    def parse_zerodha_feed(self, rss_url: str) -> List[Dict[str, Any]]:
        """Parse Zerodha Pulse RSS feed with custom handling.

        Args:
            rss_url: RSS feed URL

        Returns:
            list: List of news dictionaries
        """
        news_items = []

        try:
            logger.info(f"Fetching Zerodha Pulse feed from {rss_url}")
            feed = feedparser.parse(rss_url)

            if feed.bozo:
                logger.warning(f"Feed parsing warning: {feed.bozo_exception}")

            logger.info(f"Found {len(feed.entries)} entries in feed")

            for entry in feed.entries[:self.max_items]:
                try:
                    # Extract title
                    title = entry.get('title', '').strip()
                    if not title:
                        continue

                    # Extract description/content
                    # Zerodha feed uses 'description' field, which may be empty
                    description = (
                        entry.get('description', '').strip() or
                        entry.get('summary', '').strip()
                    )

                    # If description is empty or too short, use title
                    # But include both for LLM analysis
                    if not description or len(description) < 20:
                        content = title
                        logger.debug(f"Using title as content for: {title[:50]}...")
                    else:
                        content = f"{title}. {description}"

                    # Parse published date
                    published_at = datetime.utcnow()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published_at = datetime(*entry.published_parsed[:6])
                        except Exception as e:
                            logger.warning(f"Error parsing date: {e}")

                    # Extract URL
                    url = entry.get('link', '')
                    if not url:
                        logger.debug(f"No URL for entry: {title[:50]}...")
                        continue

                    # Create news item WITHOUT stock symbol extraction
                    # Stock symbols will be extracted during analysis phase to save time
                    news_item = {
                        'source': NewsSource.ZERODHA.value,
                        'title': sanitize_text(title),
                        'content': sanitize_text(content),
                        'published_at': published_at,
                        'stock_symbol': None,  # Will be extracted during analysis
                        'url': url
                    }

                    news_items.append(news_item)
                    logger.debug(f"Added: {title[:50]}...")

                except Exception as e:
                    logger.warning(f"Error parsing entry: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching Zerodha feed: {str(e)}")

        logger.info(f"Parsed {len(news_items)} items with stock symbols from Zerodha Pulse")
        return news_items

    def fetch_news(self) -> List[Dict[str, Any]]:
        """Fetch news from Zerodha Pulse RSS feed.

        Returns:
            list: List of news dictionaries
        """
        all_news = []

        # Fetch from RSS feed using custom parser
        for rss_url in self.rss_feeds:
            try:
                news_items = self.parse_zerodha_feed(rss_url)
                all_news.extend(news_items)
                logger.info(f"Fetched {len(news_items)} items from {rss_url}")
            except Exception as e:
                logger.error(f"Error fetching from {rss_url}: {str(e)}")
                continue

        # Remove duplicates based on title
        seen_titles = set()
        unique_news = []
        for item in all_news:
            title = item.get('title', '')
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(item)

        logger.info(f"Fetched total {len(unique_news)} unique items from Zerodha Pulse")
        return unique_news[:self.max_items]  # Limit to max_items
