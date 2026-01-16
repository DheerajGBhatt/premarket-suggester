"""Business logic services for watchlist generation."""
from typing import List, Dict, Any
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from aws_lambda_powertools import Logger, Tracer

from shared_layer.scrapers.zerodha_scraper import ZerodhaScraper
from shared_layer.ai.llm_client import LLMClient
from shared_layer.ai.prompts import SYSTEM_PROMPT, format_analysis_prompt
from shared_layer.models import NewsItem, AnalysisResult, WatchlistItem, Direction, Priority, EventType, LLMAnalysisResponse
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

    @tracer.capture_method
    def analyze_news_item(self, news_item: NewsItem) -> AnalysisResult:
        """Analyze a single news item using LLM.

        First extracts stock symbols if not present, then analyzes the news.

        Args:
            news_item: News item to analyze

        Returns:
            AnalysisResult: Analysis result, or None if no stock symbol found
        """
        try:
            # Extract stock symbol if not already present
            if not news_item.stock_symbol:
                logger.debug(f"Extracting stock symbol for: {news_item.title[:50]}...")
                from shared_layer.utils import extract_stock_symbols_with_llm

                symbols = extract_stock_symbols_with_llm(
                    news_item.title,
                    news_item.content,
                    self.llm_client
                )

                if not symbols:
                    logger.info(f"No stock symbol found, skipping: {news_item.title[:50]}...")
                    return None

                # Update news item with extracted symbol
                news_item.stock_symbol = symbols[0]
                logger.info(f"Extracted symbol: {news_item.stock_symbol}")

            logger.info(f"Analyzing news: {news_item.stock_symbol} - {news_item.title[:50]}...")

            # Format prompt
            user_prompt = format_analysis_prompt(
                stock_symbol=news_item.stock_symbol,
                news_title=news_item.title,
                news_content=news_item.content
            )

            # Call LLM
            llm_response = self.llm_client.analyze_news(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt
            )

            # Validate response
            validated_response = LLMAnalysisResponse(**llm_response)

            # Create analysis result
            analysis = AnalysisResult(
                news_id=news_item.id,
                stock_symbol=news_item.stock_symbol,
                event_type=EventType(validated_response.event_type),
                direction=Direction(validated_response.direction),
                impact_strength=validated_response.impact_strength,
                confidence=validated_response.confidence,
                rationale=validated_response.rationale,
                bias_score=validated_response.impact_strength * validated_response.confidence,
                news_published_at=news_item.published_at
            )

            logger.info(
                f"Analysis complete for {analysis.stock_symbol}: "
                f"{analysis.direction} (bias_score={analysis.bias_score:.2f})"
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing news item: {str(e)}")
            return None

    def _extract_symbol_for_item(self, news_item: NewsItem) -> NewsItem:
        """Extract stock symbol for a single news item.

        Args:
            news_item: News item to process

        Returns:
            NewsItem: Updated news item with stock_symbol populated
        """
        try:
            if not news_item.stock_symbol:
                from shared_layer.utils import extract_stock_symbols_with_llm

                symbols = extract_stock_symbols_with_llm(
                    news_item.title,
                    news_item.content,
                    self.llm_client
                )

                if symbols:
                    news_item.stock_symbol = symbols[0]
                    logger.debug(f"Extracted symbol: {news_item.stock_symbol} for {news_item.title[:50]}...")
                else:
                    logger.debug(f"No symbol found for: {news_item.title[:50]}...")
        except Exception as e:
            logger.warning(f"Error extracting symbol: {str(e)}")

        return news_item

    @tracer.capture_method
    def extract_symbols_parallel(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """Extract stock symbols for all news items in parallel.

        Args:
            news_items: List of news items without stock symbols

        Returns:
            list: News items with stock symbols populated
        """
        logger.info(f"Extracting stock symbols in parallel for {len(news_items)} items (max_workers={self.max_workers})")

        items_with_symbols = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all extraction tasks
            future_to_item = {
                executor.submit(self._extract_symbol_for_item, item): item
                for item in news_items
            }

            # Collect results as they complete
            for future in as_completed(future_to_item):
                try:
                    item = future.result()
                    if item.stock_symbol:
                        items_with_symbols.append(item)
                except Exception as e:
                    logger.error(f"Error in parallel symbol extraction: {str(e)}")

        logger.info(f"Extracted symbols for {len(items_with_symbols)}/{len(news_items)} items")
        return items_with_symbols

    def _analyze_single_item(self, news_item: NewsItem) -> AnalysisResult:
        """Analyze a single news item (without symbol extraction).

        Args:
            news_item: News item with stock_symbol already populated

        Returns:
            AnalysisResult or None
        """
        try:
            logger.info(f"Analyzing: {news_item.stock_symbol} - {news_item.title[:50]}...")

            # Format prompt
            user_prompt = format_analysis_prompt(
                stock_symbol=news_item.stock_symbol,
                news_title=news_item.title,
                news_content=news_item.content
            )

            # Call LLM
            llm_response = self.llm_client.analyze_news(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt
            )

            # Validate response
            validated_response = LLMAnalysisResponse(**llm_response)

            # Create analysis result
            analysis = AnalysisResult(
                news_id=news_item.id,
                stock_symbol=news_item.stock_symbol,
                event_type=EventType(validated_response.event_type),
                direction=Direction(validated_response.direction),
                impact_strength=validated_response.impact_strength,
                confidence=validated_response.confidence,
                rationale=validated_response.rationale,
                bias_score=validated_response.impact_strength * validated_response.confidence,
                news_published_at=news_item.published_at
            )

            logger.info(
                f"Analysis complete for {analysis.stock_symbol}: "
                f"{analysis.direction} (bias_score={analysis.bias_score:.2f})"
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing news item: {str(e)}")
            return None

    @tracer.capture_method
    def analyze_all_news(self, news_items: List[NewsItem]) -> List[AnalysisResult]:
        """Analyze all news items in parallel with early termination to prevent timeouts.

        Step 1: Extract stock symbols in parallel for all items
        Step 2: Analyze items with symbols in parallel

        Args:
            news_items: List of news items

        Returns:
            list: List of analysis results
        """
        stats = {
            'total': len(news_items),
            'with_symbols': 0,
            'analyzed': 0,
            'errors': 0
        }

        if not news_items:
            logger.warning("No news items to analyze")
            return []

        # Step 1: Extract symbols in parallel
        logger.info("Step 1: Extracting stock symbols in parallel...")
        items_with_symbols = self.extract_symbols_parallel(news_items)
        stats['with_symbols'] = len(items_with_symbols)

        if not items_with_symbols:
            logger.warning("No items with stock symbols found after extraction")
            return []

        # Step 2: Analyze in parallel
        logger.info(f"Step 2: Analyzing {len(items_with_symbols)} items in parallel...")
        analyses = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all analysis tasks
            future_to_item = {
                executor.submit(self._analyze_single_item, item): item
                for item in items_with_symbols
            }

            # Collect results as they complete
            for future in as_completed(future_to_item):
                try:
                    analysis = future.result()
                    if analysis:
                        analyses.append(analysis)
                        stats['analyzed'] += 1
                    else:
                        stats['errors'] += 1
                except Exception as e:
                    logger.error(f"Error in parallel analysis: {str(e)}")
                    stats['errors'] += 1

        logger.info(
            f"Analysis complete: {stats['analyzed']} successful, "
            f"{stats['errors']} errors, "
            f"{stats['with_symbols']} items had symbols out of {stats['total']} total"
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
