"""Utility functions used across the application."""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from aws_lambda_powertools import Logger

from .constants import (
    BIAS_SCORE_HIGH_THRESHOLD,
    BIAS_SCORE_MEDIUM_THRESHOLD,
    IST_TIMEZONE
)
from .models import Priority

logger = Logger()


def determine_priority(bias_score: float) -> Priority:
    """Determine priority level based on bias score.

    Args:
        bias_score: Calculated bias score

    Returns:
        Priority: Priority level enum
    """
    if bias_score >= BIAS_SCORE_HIGH_THRESHOLD:
        return Priority.HIGH
    elif bias_score >= BIAS_SCORE_MEDIUM_THRESHOLD:
        return Priority.MEDIUM
    else:
        return Priority.LOW


def get_current_date_ist() -> str:
    """Get current date in IST timezone.

    Returns:
        str: Date in YYYY-MM-DD format
    """
    # Note: For production, use proper timezone handling with pytz
    # For simplicity, assuming UTC+5:30 offset
    utc_now = datetime.utcnow()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now.strftime("%Y-%m-%d")


def format_api_response(
    success: bool,
    data: Optional[Any] = None,
    error: Optional[Dict[str, str]] = None,
    status_code: int = 200
) -> Dict[str, Any]:
    """Format standardized API response.

    Args:
        success: Whether operation was successful
        data: Response data
        error: Error information if failed
        status_code: HTTP status code

    Returns:
        dict: Formatted API response
    """
    response = {
        "success": success
    }

    if data is not None:
        response["data"] = data

    if error is not None:
        response["error"] = error

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
        },
        "body": response
    }


def get_env_variable(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """Get environment variable with validation.

    Args:
        key: Environment variable key
        default: Default value if not set
        required: Whether variable is required

    Returns:
        str: Environment variable value

    Raises:
        ValueError: If required variable is not set
    """
    value = os.environ.get(key, default)

    if required and not value:
        raise ValueError(f"Required environment variable {key} is not set")

    return value


def extract_stock_symbols_with_llm(
    news_title: str,
    news_content: str,
    llm_client: Optional[Any] = None
) -> list[str]:
    """Extract stock symbols from news using LLM (Bedrock).

    This method uses AI to intelligently extract stock symbols, understanding:
    - Company names → stock symbols
    - Context to filter out false positives
    - Indian market specific symbols (NSE/BSE)

    Args:
        news_title: News article title
        news_content: News article content
        llm_client: LLM client instance (if None, creates new one)

    Returns:
        list: List of extracted stock symbols (empty list if none found)
    """
    try:
        # Import here to avoid circular dependency
        from .ai.llm_client import LLMClient

        # Use provided client or create new one
        if llm_client is None:
            llm_client = LLMClient()

        # Extract symbols using LLM
        symbols = llm_client.extract_stock_symbols(news_title, news_content)

        if symbols:
            logger.info(f"LLM extracted {len(symbols)} symbols: {symbols}")
        else:
            logger.info("LLM found no symbols in news")

        return symbols

    except Exception as e:
        logger.error(f"LLM symbol extraction failed: {str(e)}")
        # Return empty list on failure instead of fallback
        return []


def sanitize_text(text: str) -> str:
    """Sanitize text by removing special characters and extra whitespace.

    Args:
        text: Text to sanitize

    Returns:
        str: Sanitized text
    """
    import re

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters except basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)

    return text.strip()


def is_market_hours() -> bool:
    """Check if current time is during market hours (IST).

    Returns:
        bool: True if during market hours
    """
    from datetime import time

    # Get current IST time
    utc_now = datetime.utcnow()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    current_time = ist_now.time()

    # Market hours: 9:15 AM to 3:30 PM IST
    market_open = time(9, 15)
    market_close = time(15, 30)

    return market_open <= current_time <= market_close


def chunk_list(lst: list, chunk_size: int) -> list[list]:
    """Split list into chunks of specified size.

    Args:
        lst: List to chunk
        chunk_size: Size of each chunk

    Returns:
        list: List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
