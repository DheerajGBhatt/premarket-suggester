# RSS Feed Configuration

This document describes the RSS feed used by the premarket suggester application.

## News Source

The application fetches news from **Zerodha Pulse**, which aggregates Indian market news from multiple publishers.

### Zerodha Pulse

| Property | Value |
|----------|-------|
| **Feed URL** | `https://pulse.zerodha.com/feed.php` |
| **Coverage** | NSE/BSE stocks, Indian market news |
| **Sources** | MoneyControl, Economic Times, Business Standard, Mint, and more |
| **Format** | RSS 2.0 |

**Scraper:** `ZerodhaScraper`
**File:** `src/python/shared_layer/scrapers/zerodha_scraper.py`

## Why Zerodha Pulse?

| Benefit | Description |
|---------|-------------|
| **Aggregated** | Single feed with news from multiple publishers |
| **Market-Focused** | Curated specifically for Indian stock market traders |
| **Reliable** | Official Zerodha service with high uptime |
| **Simplified** | One feed to manage instead of 9+ feeds |
| **Quality** | Pre-filtered for market relevance |

## Architecture

### Scraper Implementation

```
ZerodhaScraper (zerodha_scraper.py)
       │
       ├── Inherits from BaseScraper
       │
       ├── fetch_news()
       │      └── Fetches RSS feed
       │
       ├── parse_zerodha_feed()
       │      ├── Parse RSS entries
       │      ├── Extract title, content, date, URL
       │      └── Return news items (without stock symbols)
       │
       └── Deduplication by title
```

### Base Scraper

All scrapers inherit from `BaseScraper` which provides:
- Common configuration (max_items, timeout)
- Logging via PowerTools
- Error handling

**File:** `src/python/shared_layer/scrapers/base_scraper.py`

### RSS Parsing

- **Library:** `feedparser`
- **Features:**
  - Automatic date parsing
  - Content extraction (description, summary)
  - Robust error handling
  - Feed validation

## Feed Characteristics

### Content Structure

Each RSS entry provides:

| Field | Availability | Description |
|-------|--------------|-------------|
| Title | ✅ Always | News headline |
| Description | ⚠️ Sometimes | Article summary (may be empty) |
| Link | ✅ Always | Full article URL |
| Published Date | ✅ Always | Publication timestamp |

**Note:** Some entries have empty descriptions. The scraper uses the title as content when description is missing or too short.

### Update Frequency

- **Frequency:** Near real-time (updated every 5-15 minutes)
- **Items per fetch:** 20-50 news items
- **Coverage hours:** 24/7 (higher volume during market hours)

### Stock Symbol Handling

**Important:** Zerodha Pulse does not include stock symbols in the RSS feed.

Stock symbols are extracted during analysis using the LLM:
1. News item fetched without stock symbol
2. Combined LLM call extracts symbol AND analyzes news
3. News items without identifiable stocks are skipped

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_NEWS_ITEMS` | 20 | Maximum news items to process |

### Customization

To modify the RSS feed, edit `zerodha_scraper.py`:

```python
class ZerodhaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.rss_feeds = [
            "https://pulse.zerodha.com/feed.php"
            # Add additional feeds here if needed
        ]
```

## Error Handling

### Feed Errors

If the RSS feed fails to fetch:
- Error is logged to CloudWatch
- Empty news list is returned
- API returns empty watchlist with metadata

### Parsing Errors

If individual entries fail to parse:
- Entry is skipped
- Other entries continue processing
- Warning logged for debugging

### Monitoring

Check CloudWatch logs for:
```
"Fetching Zerodha Pulse feed from <url>"
"Found N entries in feed"
"Parsed N items with stock symbols from Zerodha Pulse"
"Error fetching Zerodha feed: <error>"
```

## Testing

### Manual Testing

Test the feed in a browser:
```bash
open https://pulse.zerodha.com/feed.php
```

### Python Testing

```python
import feedparser

feed = feedparser.parse("https://pulse.zerodha.com/feed.php")
print(f"Feed title: {feed.feed.title}")
print(f"Items: {len(feed.entries)}")
for entry in feed.entries[:3]:
    print(f"- {entry.title}")
```

### Lambda Testing

```bash
# Local invoke
sam local invoke WatchlistAPIFunction

# Local API
sam local start-api
curl http://localhost:3000/watchlist
```

## Comparison: Before vs After

### Previous Architecture (Multiple Feeds)

| Source | Feeds | Items |
|--------|-------|-------|
| MoneyControl | 3 | ~60-90 |
| Economic Times | 3 | ~90-150 |
| Business Standard | 2 | ~40-60 |
| Mint | 1 | ~15-25 |
| **Total** | **9** | **~200-325** |

### Current Architecture (Single Feed)

| Source | Feeds | Items |
|--------|-------|-------|
| Zerodha Pulse | 1 | ~20-50 |
| **Total** | **1** | **~20-50** |

### Benefits of Simplification

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| RSS Feeds | 9 | 1 | 89% fewer |
| Scrapers | 4 | 1 | 75% fewer |
| Code lines | ~400 | ~100 | 75% reduction |
| Maintenance | High | Low | Simplified |
| LLM Calls | ~200-325 | ~20-50 | ~85% reduction |

## Dependencies

### Python Packages

```txt
feedparser>=6.0.10  # RSS/Atom feed parser
```

## Future Enhancements

### Additional Sources (If Needed)

If Zerodha Pulse is insufficient, consider adding:
- **CNBC India:** `https://www.cnbctv18.com/rss/`
- **Reuters India:** `https://www.reuters.com/rssfeed/india`
- **NSE Official:** Corporate announcements API

### Caching

- Cache RSS feed responses (5-10 minutes TTL)
- Reduce redundant fetches for repeated requests
- Improve response times

### Fallback Sources

- Add backup RSS feeds if Zerodha Pulse is unavailable
- Automatic failover to alternative sources

## Support

For RSS feed issues:
1. Check CloudWatch logs for specific errors
2. Test feed URL in browser: `https://pulse.zerodha.com/feed.php`
3. Verify feedparser is installed in Lambda layer
4. Check Lambda network connectivity

## References

- **feedparser documentation:** https://feedparser.readthedocs.io/
- **Zerodha Pulse:** https://pulse.zerodha.com/
- **RSS 2.0 specification:** https://www.rssboard.org/rss-specification
