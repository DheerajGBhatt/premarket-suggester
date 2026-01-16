# Technical Design Document

## System Name

AI Intraday Stock Suggester – Pre-Market News Based

---

## 1. Architecture Overview

The system is a **stateless, API-driven AWS serverless application** that fetches news from Zerodha Pulse RSS feed, analyzes them using AWS Bedrock LLM, and returns an **intraday watchlist synchronously via API**.

There is **no scheduled execution, no background jobs, and no persistent database**. All computation happens at request time.

### High-Level Architecture

```
Client (UI / Curl / Bot)
   ↓
API Gateway (REST)
   ↓
Lambda Function (Python 3.12)
   ↓
Zerodha Pulse RSS Feed
   ↓
AWS Bedrock (Combined Extract + Analyze)
   ↓
Scoring & Ranking (In-memory)
   ↓
API Response (Watchlist JSON)
```

---

## 2. Technology Stack

### Infrastructure

- **AWS SAM** - Infrastructure as Code
- **AWS Lambda** - Python 3.12 runtime
- **Amazon API Gateway** - REST API
- **AWS Bedrock** - LLM inference

### AI Models (via Bedrock)

- Claude 3.5 Sonnet (default, best quality)
- Claude 3 Haiku (fast, cost-effective)
- Llama 3 70B, Amazon Titan (alternatives)

### Libraries

- `aws_lambda_powertools` - Logging, tracing, API routing
- `pydantic` - Data validation
- `feedparser` - RSS parsing
- `boto3` - AWS SDK

---

## 3. Infrastructure Design (AWS SAM)

### Resources

| Resource | Type | Purpose |
|----------|------|---------|
| WatchlistAPIFunction | Lambda | Main handler |
| WatchlistAPI | API Gateway | REST endpoint |
| SharedLayer | Lambda Layer | Shared code |
| IAM Role | IAM | Bedrock access |

### No Scheduled Jobs or Databases

The architecture is fully stateless with no:
- EventBridge rules
- DynamoDB tables
- S3 buckets for state

---

## 4. Lambda Function

### WatchlistAPIFunction

**Purpose:**
- Fetch news from Zerodha Pulse RSS
- Extract stock symbols and analyze using Bedrock (single LLM call)
- Score and rank stocks
- Return intraday watchlist

**Configuration:**

| Property | Value |
|----------|-------|
| Runtime | Python 3.12 |
| Memory | 2048 MB |
| Timeout | 900 seconds |
| Handler | app.lambda_handler |

**Trigger:**
- API Gateway (`GET /watchlist`)

---

## 5. Code Structure

```
src/
├── functions/
│   └── watchlist_api/
│       └── app.py              # Lambda handler
└── python/
    └── shared_layer/
        ├── __init__.py
        ├── services.py         # WatchlistGeneratorService
        ├── models.py           # Pydantic models
        ├── utils.py            # Utility functions
        ├── constants.py        # Configuration
        ├── ai/
        │   ├── llm_client.py   # Bedrock client
        │   └── prompts.py      # LLM prompts
        └── scrapers/
            ├── base_scraper.py
            └── zerodha_scraper.py
```

---

## 6. Data Flow

### Request Flow

```
1. GET /watchlist request
       ↓
2. ZerodhaScraper.fetch_news()
   - Fetch RSS from pulse.zerodha.com
   - Parse entries (title, content, date, URL)
   - Deduplicate by title
       ↓
3. WatchlistGeneratorService.analyze_all_news()
   - Parallel processing (ThreadPoolExecutor)
   - For each news item:
     - Combined LLM call (extract symbol + analyze)
     - Create AnalysisResult
       ↓
4. WatchlistGeneratorService.generate_watchlist()
   - Group by stock symbol
   - Calculate aggregated bias score
   - Sort by bias score descending
   - Limit to MAX_WATCHLIST_SIZE
       ↓
5. Return JSON response
```

### LLM Analysis (Single Call)

Each news item is processed with a single Bedrock call that:
1. Extracts NSE/BSE stock symbol from news text
2. Classifies event type
3. Determines direction (Bullish/Bearish/Neutral)
4. Scores impact strength (1-5)
5. Calculates confidence (0.0-1.0)
6. Generates rationale

**Output Schema:**

```json
{
  "stock_symbol": "TATASTEEL",
  "event_type": "Earnings",
  "direction": "BULLISH",
  "impact_strength": 4,
  "confidence": 0.85,
  "rationale": "Strong Q3 earnings beat expectations"
}
```

---

## 7. Scoring Engine

### Bias Score Calculation

```
Bias Score = Impact Strength × Confidence
```

### Priority Thresholds

| Bias Score | Priority |
|------------|----------|
| ≥ 2.5 | HIGH |
| 1.5 - 2.4 | MEDIUM |
| < 1.5 | Excluded |

### Aggregation

When multiple news items mention the same stock:
- Highest bias score is used
- News count is tracked
- Latest news datetime preserved

---

## 8. AWS Bedrock Integration

### Client Configuration

```python
bedrock_runtime = boto3.client('bedrock-runtime')
```

### Model Support

The LLM client supports multiple providers:
- Anthropic (Claude)
- Meta (Llama)
- Amazon (Titan)
- AI21 (Jurassic)
- Cohere (Command)

### Cross-Region Inference

Supports inference profiles for high availability:
- `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
- `eu.anthropic.claude-3-5-sonnet-20241022-v2:0`

---

## 9. API Design

### GET /watchlist

**Response:**

```json
{
  "success": true,
  "data": {
    "watchlist": [...],
    "bullish_stocks": [...],
    "bearish_stocks": [...],
    "metadata": {
      "generated_at": "2024-01-12",
      "total_news_fetched": 25,
      "total_analyzed": 18,
      "watchlist_size": 8
    }
  }
}
```

**Response Time:** 1-3 minutes

---

## 10. Security & IAM

### IAM Permissions

```yaml
- bedrock:InvokeModel
- logs:CreateLogGroup
- logs:CreateLogStream
- logs:PutLogEvents
- xray:PutTraceSegments
- xray:PutTelemetryRecords
```

### Security Features

- IAM-based authentication (no API keys)
- No data persistence
- No secrets management required

---

## 11. Observability

### Logging

- AWS Lambda Powertools Logger
- Structured JSON logs
- Correlation IDs

### Tracing

- AWS X-Ray integration
- Powertools Tracer

### Key Metrics

- Request duration
- News fetch success rate
- Bedrock API latency
- Analysis success rate

---

## 12. Error Handling

### RSS Feed Errors

- Log error and continue
- Return empty watchlist if all feeds fail

### Bedrock Errors

- Log error per news item
- Skip failed items
- Continue with successful analyses

### Response Handling

- Always return valid JSON
- Include error details in response
- Graceful degradation

---

## 13. Deployment

### Commands

```bash
# Build
sam build

# Deploy
sam deploy --guided

# Local testing
sam local start-api
```

### Environments

- dev
- staging
- prod

---

## 14. Cost Estimation

| Component | Cost |
|-----------|------|
| Lambda | ~$0.02/request |
| Bedrock (Claude Haiku) | ~$0.02/request |
| API Gateway | ~$3/month |
| **Total** | **~$4-7/month** |

---

## 15. Summary

This architecture provides:
- **Stateless** - No database or persistent state
- **Serverless** - Pay-per-use, auto-scaling
- **Model-agnostic** - Switch Bedrock models via config
- **Cost-effective** - Optimized LLM usage
- **Maintainable** - Clean separation of concerns

> The system focuses on one goal:
> **Deliver a reliable, pre-market intraday watchlist driven by news analysis.**
