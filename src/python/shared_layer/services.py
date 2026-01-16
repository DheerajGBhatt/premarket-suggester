"""Business logic services for watchlist generation."""
from typing import List, Dict, Any
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from aws_lambda_powertools import Logger, Tracer

from shared_layer.scrapers.zerodha_scraper import ZerodhaScraper
from shared_layer.ai.llm_client import LLMClient
from shared_layer.ai.prompts import SYSTEM_PROMPT, format_combined_analysis_prompt
from shared_layer.models import NewsItem, AnalysisResult, WatchlistItem, Direction, Priority, EventType
from shared_layer.utils import get_env_variable, determine_priority, get_current_date_ist
from shared_layer.constants import MAX_WATCHLIST_SIZE, MIN_NEWS_COUNT_FOR_WATCHLIST

logger = Logger(child=True)
tracer = Tracer()


class WatchlistGeneratorService:
    """Service that orchestrates the entire watchlist generation process."""

    def __init__(self):
        """Initialize the service."""
        self.max_watchlist_size = int(get_env_variable('MAX_WATCHLIST_SIZE', str(MAX_WATCHLIST_SIZE)))

        # Parallel processing configuration
        # Limit concurrent LLM calls to avoid rate limits and reduce Lambda memory pressure
        self.max_workers = int(get_env_variable('MAX_PARALLEL_WORKERS', '5'))

        # Initialize scraper
        self.scraper = ZerodhaScraper()

        # Initialize LLM client
        self.llm_client = LLMClient()

    @tracer.capture_method
    def fetch_all_news(self) -> List[NewsItem]:
        """Fetch news from Zerodha Pulse.

        Returns:
            list: List of NewsItem objects
        """
        all_news = []
        stats = {
            'total_fetched': 0,
            'total_with_symbols': 0,
            'errors': 0
        }

        try:
            logger.info("Fetching news from Zerodha Pulse")
            news_data_list = self.scraper.fetch_news()
            stats['total_fetched'] = len(news_data_list)

            # Convert to NewsItem objects
            # Note: Stock symbols will be extracted during analysis to save time
            for news_data in news_data_list:
                try:
                    news_item = NewsItem(**news_data)
                    all_news.append(news_item)
                except Exception as e:
                    logger.warning(f"Error creating NewsItem: {str(e)}")
                    stats['errors'] += 1

        except Exception as e:
            logger.error(f"Error fetching from Zerodha Pulse: {str(e)}")
            stats['errors'] += 1

        logger.info(f"Fetched {stats['total_fetched']} news items")
        return all_news

    def _combined_extract_and_analyze(self, news_item: NewsItem) -> AnalysisResult:
        """Extract stock symbol and analyze news in a single LLM call.

        This method combines symbol extraction and news analysis into one call,
        reducing Bedrock API costs by ~50%.

        Args:
            news_item: News item to analyze

        Returns:
            AnalysisResult: Analysis result, or None if no stock symbol found
        """
        try:
            logger.debug(f"Combined extract+analyze for: {news_item.title[:50]}...")

            # Format combined prompt (no stock symbol needed upfront)
            user_prompt = format_combined_analysis_prompt(
                news_title=news_item.title,
                news_content=news_item.content
            )

            # Single LLM call for both extraction and analysis
            llm_response = self.llm_client.extract_and_analyze(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt
            )

            # If no stock symbol found, skip this news item
            if not llm_response:
                logger.debug(f"No stock symbol found, skipping: {news_item.title[:50]}...")
                return None

            # Create analysis result
            analysis = AnalysisResult(
                news_id=news_item.id,
                stock_symbol=llm_response['stock_symbol'],
                event_type=EventType(llm_response.get('event_type', 'Other')),
                direction=Direction(llm_response.get('direction', 'NEUTRAL')),
                impact_strength=llm_response.get('impact_strength', 1),
                confidence=llm_response.get('confidence', 0.5),
                rationale=llm_response.get('rationale', 'No rationale provided'),
                bias_score=llm_response.get('impact_strength', 1) * llm_response.get('confidence', 0.5),
                news_published_at=news_item.published_at
            )

            logger.info(
                f"Combined analysis complete: {analysis.stock_symbol} - "
                f"{analysis.direction} (bias_score={analysis.bias_score:.2f})"
            )

            return analysis

        except Exception as e:
            logger.error(f"Error in combined extract+analyze: {str(e)}")
            return None

    @tracer.capture_method
    def analyze_all_news(self, news_items: List[NewsItem]) -> List[AnalysisResult]:
        """Analyze all news items in parallel using combined extraction+analysis.

        Uses a single LLM call per news item to extract stock symbol and analyze,
        reducing Bedrock API costs by ~50% compared to separate calls.

        Args:
            news_items: List of news items

        Returns:
            list: List of analysis results
        """
        stats = {
            'total': len(news_items),
            'analyzed': 0,
            'skipped': 0,
            'errors': 0
        }

        if not news_items:
            logger.warning("No news items to analyze")
            return []

        logger.info(f"Analyzing {len(news_items)} items with combined extract+analyze (max_workers={self.max_workers})")
        analyses = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all combined extract+analyze tasks
            future_to_item = {
                executor.submit(self._combined_extract_and_analyze, item): item
                for item in news_items
            }

            # Collect results as they complete
            for future in as_completed(future_to_item):
                try:
                    analysis = future.result()
                    if analysis:
                        analyses.append(analysis)
                        stats['analyzed'] += 1
                    else:
                        stats['skipped'] += 1
                except Exception as e:
                    logger.error(f"Error in parallel analysis: {str(e)}")
                    stats['errors'] += 1

        logger.info(
            f"Analysis complete: {stats['analyzed']} successful, "
            f"{stats['skipped']} skipped (no symbol), "
            f"{stats['errors']} errors out of {stats['total']} total"
        )
        return analyses

    @tracer.capture_method
    def generate_watchlist(self, analyses: List[AnalysisResult]) -> List[WatchlistItem]:
        """Generate watchlist from analysis results.

        Args:
            analyses: List of analysis results

        Returns:
            list: List of watchlist items
        """
        # Aggregate by stock symbol
        stock_aggregates = defaultdict(lambda: {
            'analyses': [],
            'total_bias_score': 0.0,
            'directions': defaultdict(int),
            'latest_news_datetime': None,
        })

        for analysis in analyses:
            symbol = analysis.stock_symbol
            agg = stock_aggregates[symbol]
            agg['analyses'].append(analysis)
            agg['total_bias_score'] += analysis.bias_score
            agg['directions'][analysis.direction] += 1

            # Track the latest news datetime for this stock
            if agg['latest_news_datetime'] is None or analysis.news_published_at > agg['latest_news_datetime']:
                agg['latest_news_datetime'] = analysis.news_published_at

        # Generate watchlist items
        watchlist_items = []
        date = get_current_date_ist()

        for symbol, agg in stock_aggregates.items():
            try:
                news_count = len(agg['analyses'])

                # Skip if too few news items
                if news_count < MIN_NEWS_COUNT_FOR_WATCHLIST:
                    continue

                # Calculate average bias score
                avg_bias_score = agg['total_bias_score'] / news_count

                # Determine dominant direction
                directions = agg['directions']
                if not directions:
                    continue

                dominant_direction = max(directions, key=directions.get)

                # Skip NEUTRAL stocks
                if dominant_direction == Direction.NEUTRAL.value:
                    continue

                # Determine priority
                priority = determine_priority(avg_bias_score)

                # Skip LOW priority stocks
                if priority == Priority.LOW:
                    continue

                # Get best rationale
                sorted_analyses = sorted(
                    agg['analyses'],
                    key=lambda x: x.bias_score,
                    reverse=True
                )
                best_rationale = sorted_analyses[0].rationale

                # Create watchlist item
                item = WatchlistItem(
                    stock_symbol=symbol,
                    direction=Direction(dominant_direction),
                    priority=priority,
                    bias_score=avg_bias_score,
                    reason=best_rationale,
                    news_count=news_count,
                    sector=None,
                    latest_news_datetime=agg['latest_news_datetime'],
                    date=date
                )

                watchlist_items.append(item)

            except Exception as e:
                logger.warning(f"Error creating watchlist item for {symbol}: {str(e)}")
                continue

        # Sort by bias score descending
        watchlist_items.sort(key=lambda x: x.bias_score, reverse=True)

        # Limit to max size
        watchlist_items = watchlist_items[:self.max_watchlist_size]

        logger.info(f"Generated watchlist with {len(watchlist_items)} stocks")
        return watchlist_items

    @tracer.capture_method
    def generate_complete_watchlist(self) -> Dict[str, Any]:
        """Generate complete watchlist by orchestrating all steps.

        Returns:
            dict: Complete watchlist with metadata
        """
        try:
            # Step 1: Fetch news
            logger.info("Step 1: Fetching news from all sources")
            news_items = self.fetch_all_news()

            if not news_items:
                logger.warning("No news items with stock symbols found")
                return {
                    'watchlist': [],
                    'metadata': {
                        'generated_at': get_current_date_ist(),
                        'total_news_fetched': 0,
                        'total_analyzed': 0,
                        'watchlist_size': 0
                    }
                }

            # Step 2: Analyze news with LLM
            logger.info(f"Step 2: Analyzing {len(news_items)} news items")
            analyses = self.analyze_all_news(news_items)

            if not analyses:
                logger.warning("No successful analyses")
                return {
                    'watchlist': [],
                    'metadata': {
                        'generated_at': get_current_date_ist(),
                        'total_news_fetched': len(news_items),
                        'total_analyzed': 0,
                        'watchlist_size': 0
                    }
                }

            # Step 3: Generate watchlist
            logger.info(f"Step 3: Generating watchlist from {len(analyses)} analyses")
            watchlist = self.generate_watchlist(analyses)

            # Prepare response - use json() to properly serialize datetime objects
            bullish_stocks = [item.dict() for item in watchlist if item.direction == Direction.BULLISH]
            bearish_stocks = [item.dict() for item in watchlist if item.direction == Direction.BEARISH]

            # Convert datetime objects to ISO format strings
            def serialize_item(item_dict):
                """Convert datetime objects to ISO format strings."""
                for key, value in item_dict.items():
                    if hasattr(value, 'isoformat'):
                        item_dict[key] = value.isoformat()
                return item_dict

            result = {
                'watchlist': [serialize_item(item.dict()) for item in watchlist],
                'bullish_stocks': [serialize_item(item) for item in bullish_stocks],
                'bearish_stocks': [serialize_item(item) for item in bearish_stocks],
                'metadata': {
                    'generated_at': get_current_date_ist(),
                    'total_news_fetched': len(news_items),
                    'total_analyzed': len(analyses),
                    'watchlist_size': len(watchlist),
                    'bullish_count': len(bullish_stocks),
                    'bearish_count': len(bearish_stocks)
                }
            }

            logger.info(f"Watchlist generation complete: {len(watchlist)} stocks")
            return result

        except Exception as e:
            logger.error(f"Error generating watchlist: {str(e)}", exc_info=True)
            raise
