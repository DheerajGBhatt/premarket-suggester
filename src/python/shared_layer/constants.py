"""Constants used across the application."""
from typing import Dict

# Bias score thresholds
BIAS_SCORE_HIGH_THRESHOLD = 2.5
BIAS_SCORE_MEDIUM_THRESHOLD = 1.5

# Watchlist configuration
MAX_WATCHLIST_SIZE = 10
MIN_NEWS_COUNT_FOR_WATCHLIST = 1

# LLM configuration
DEFAULT_LLM_TEMPERATURE = 0.3
DEFAULT_LLM_MAX_TOKENS = 1000

# Date and time
IST_TIMEZONE = "Asia/Kolkata"
MARKET_OPEN_HOUR = 9  # 9:00 AM IST
MARKET_CLOSE_HOUR = 15  # 3:30 PM IST

# News sources configuration (RSS feeds)
NEWS_SOURCES: Dict[str, Dict[str, str]] = {
    "NSE": {
        "description": "Business Standard, Mint (NSE/BSE coverage)",
        "type": "rss"
    },
    "MONEYCONTROL": {
        "description": "MoneyControl RSS feeds (Markets, Business, Latest)",
        "type": "rss"
    },
    "ECONOMIC_TIMES": {
        "description": "Economic Times RSS feeds (Stocks, Markets, Top Stories)",
        "type": "rss"
    }
}

# API response messages
ERROR_MESSAGES = {
    "invalid_input": "Invalid input parameters provided",
    "llm_error": "Error analyzing news with LLM",
    "rss_fetch_error": "Failed to fetch RSS feed from source",
    "rate_limit": "Rate limit exceeded, please try again later"
}

# Logging
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_ERROR = "ERROR"

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_MULTIPLIER = 2
