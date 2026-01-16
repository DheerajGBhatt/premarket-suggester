# Product Requirements Document (PRD)

## Product Name

AI Intraday Stock Suggester – Pre-Market News Based

---

## 1. Problem Statement

Intraday traders often miss high-quality trading opportunities driven by overnight or early-morning news due to:

- Information overload across multiple news sources
- Lack of structured interpretation of news impact
- Difficulty converting news into actionable intraday bias

Manual analysis is slow, subjective, and inconsistent.

---

## 2. Product Objective

Build an AI-powered system that analyzes **pre-market news only** and generates a **high-confidence intraday watchlist** with directional bias in real-time.

The system does **not** predict prices or automate trades.

---

## 3. Goals & Non-Goals

### Goals

- Identify stocks likely to move intraday due to news
- Classify direction (Bullish / Bearish / Neutral)
- Estimate impact strength and confidence
- Generate a concise watchlist on-demand

### Non-Goals

- No price prediction
- No automated trade execution
- No technical indicator analysis
- No long-term investment recommendations
- No data persistence

---

## 4. Target Users

- Active intraday traders
- Proprietary trading desks (manual execution)
- Retail traders using price-action strategies

---

## 5. Key User Workflow

1. User calls the `/watchlist` API endpoint
2. System fetches latest news from Zerodha Pulse RSS
3. AI extracts stock symbols and analyzes news in a single optimized call
4. Stocks are scored and ranked by bias score
5. User receives a prioritized watchlist in JSON format
6. Trader confirms entries using price action after market open

---

## 6. Data Sources

### News Source

- **Zerodha Pulse RSS Feed**: `https://pulse.zerodha.com/feed.php`
  - Aggregated Indian market news from multiple publishers
  - Coverage: NSE/BSE stocks, corporate announcements, earnings, market news
  - Sources include: MoneyControl, Economic Times, Business Standard, Mint

### Why Zerodha Pulse?

- Single aggregated feed vs multiple RSS sources
- Market-focused curation for Indian stocks
- Reliable official Zerodha service
- Structured RSS format

---

## 7. Core Features

### 7.1 News Ingestion

- Real-time fetching on API request (stateless)
- RSS feed parsing via `feedparser`
- Deduplication by title
- No persistent storage

### 7.2 AI News Analysis (Optimized Single Call)

AI extracts stock symbols AND analyzes news in a **single LLM call** per news item:

For each news item:

- **Stock Symbol Extraction**: Identify NSE/BSE stock symbol from news text
- **Event Type**: Earnings, Order, Regulatory, Macro, Other
- **Direction**: Bullish / Bearish / Neutral
- **Impact Strength**: 1–5 scale
- **Confidence Score**: 0.0–1.0
- **Rationale**: One-line explanation (max 200 chars)

### 7.3 Bias Scoring Engine

Compute a bias score:

```
Bias Score = Impact Strength × Confidence
```

Threshold-based filtering:

- Bias Score ≥ 2.5 → High priority
- Bias Score 1.5–2.4 → Medium priority
- Bias Score < 1.5 → Excluded from watchlist

### 7.4 Watchlist Generation

- Ranked list of 5–10 stocks (configurable)
- Grouped by Bullish / Bearish
- Aggregated by stock symbol (multiple news = higher confidence)
- Sorted by bias score descending

---

## 8. Output Format

### API Response

```json
{
  "success": true,
  "data": {
    "watchlist": [
      {
        "stock_symbol": "TATASTEEL",
        "direction": "BULLISH",
        "priority": "HIGH",
        "bias_score": 4.25,
        "reason": "Strong earnings beat with margin expansion",
        "news_count": 3
      }
    ],
    "bullish_stocks": [...],
    "bearish_stocks": [...],
    "metadata": {
      "generated_at": "2024-01-12",
      "total_news_fetched": 25,
      "total_analyzed": 18,
      "watchlist_size": 8,
      "bullish_count": 5,
      "bearish_count": 3
    }
  }
}
```

---

## 9. AI Prompting Strategy

The AI must:

- Extract valid NSE/BSE stock symbols from news text
- Ignore indices (NIFTY, SENSEX), commodities, non-Indian stocks
- Focus only on same-day tradability
- Ignore long-term fundamentals
- Avoid speculative language
- Produce structured JSON output
- Return null for stock_symbol if no relevant stock found

---

## 10. Success Metrics

### Quantitative

- % of watchlist stocks showing ≥ 1% intraday move
- Directional accuracy (Bullish vs Bearish)
- Average move during first 90 minutes
- API response time (target: < 3 minutes)

### Qualitative

- Trader feedback on usefulness
- Reduction in pre-market analysis time

---

## 11. Risk & Constraints

- News interpretation is probabilistic, not deterministic
- False positives on low-liquidity stocks
- Overreaction to already-priced-in news
- Zerodha Pulse feed availability

Mitigations:

- Confidence thresholds
- Minimum news count filter
- Manual confirmation post-market open
- Error handling for feed failures

---

## 12. Tech Stack

### Infrastructure

- **AWS SAM** - Infrastructure as Code
- **AWS Lambda** - Serverless compute (Python 3.12)
- **API Gateway** - REST API endpoint
- **AWS Bedrock** - LLM inference (model-agnostic)

### AI Models (via Bedrock)

- Claude 3.5 Sonnet (recommended for quality)
- Claude 3 Haiku (recommended for cost)
- Llama 3 70B, Amazon Titan, AI21, Cohere (alternatives)

### Libraries

- `aws_lambda_powertools` - Logging, tracing
- `pydantic` - Data validation
- `feedparser` - RSS parsing
- `boto3` - AWS SDK

### Architecture

- **Stateless**: No database, fresh analysis on every request
- **Serverless**: Pay-per-use, auto-scaling
- **Model-agnostic**: Switch Bedrock models via config

---

## 13. API Endpoints

### GET /watchlist

Generate fresh watchlist in real-time.

- **Response Time**: 1-3 minutes
- **Authentication**: None (can add API key if needed)
- **CORS**: Enabled for all origins

---

## 14. Cost Estimation

| Model | Per Request | Monthly (daily use) |
|-------|-------------|---------------------|
| Claude 3.5 Sonnet | ~$0.12 | ~$7/month |
| Claude 3 Haiku | ~$0.04 | ~$4/month |
| Llama 3 70B | ~$0.07 | ~$5/month |

---

## 15. MVP Scope (Implemented)

Included:

- Real-time news ingestion from Zerodha Pulse
- Combined AI-based symbol extraction + analysis
- Bias scoring and watchlist generation
- REST API endpoint
- Cross-region Bedrock inference support

Excluded:

- Live market data
- Trade execution
- Backtesting
- Scheduled/cron-based execution
- Alerts (Telegram/Slack)
- Web dashboard

---

## 16. Future Enhancements

- Sector-level sentiment aggregation
- Gap-up / gap-down validation
- Post-market performance feedback loop
- Scheduled execution with SNS alerts
- Web dashboard for visualization
- Multiple news source support
- Caching layer for repeated requests

---

## 17. Final Note

This system is designed to **improve preparedness**, not replace trader judgment.

> "The edge is knowing _what to watch_ before the bell rings."
