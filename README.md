# AI Intraday Stock Suggester - Pre-Market News Analysis

An AI-powered system that analyzes pre-market news and generates high-confidence intraday watchlists with directional bias in real-time using **AWS Bedrock**.

## Overview

This application helps intraday traders identify high-probability trading opportunities by:
- Ingesting news from multiple RSS feeds (MoneyControl, Economic Times, Business Standard, Mint)
- Using **AWS Bedrock** models (Claude, Llama, Titan, etc.) to analyze news for intraday trading impact
- Scoring and ranking stocks by potential impact
- Generating a prioritized watchlist (5-10 stocks) with Bullish/Bearish bias

**What it does NOT do:**
- Price prediction
- Automated trade execution
- Technical indicator analysis
- Store any historical data

## Architecture

**Stateless, Real-time Generation with AWS Bedrock:**

```
API Request → Watchlist Generator Lambda
                      ↓
              1. Fetch News from RSS Feeds
                 (MoneyControl, Economic Times,
                  Business Standard, Mint)
                      ↓
              2. Analyze with AWS Bedrock (Model-Agnostic)
                      ↓
              3. Score & Rank
                      ↓
              Return JSON Response
```

**Key Features:**
- ✅ **RSS Feeds**: Reliable, structured news from official sources
- ✅ **AWS Bedrock**: Model-agnostic AI (Claude, Llama, Titan, etc.)
- ✅ **No API Keys**: IAM-based authentication
- ✅ **No Database**: Everything in-memory, no persistence
- ✅ **Real-time**: Fresh analysis on every request
- ✅ **Stateless**: Each request is independent
- ✅ **Simple**: Single Lambda orchestrates everything
- ✅ **Cost-effective**: Pay only for actual usage

## Supported Bedrock Models

The application automatically adapts to different Bedrock models:

| Model | Model ID | Use Case | Cost |
|-------|----------|----------|------|
| **Claude 3.5 Sonnet** *(Recommended)* | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Best quality, accurate analysis | $$$ |
| **Claude 3 Haiku** | `anthropic.claude-3-haiku-20240307-v1:0` | Fast, cheaper, good quality | $$ |
| **Llama 3 70B** | `meta.llama3-70b-instruct-v1:0` | Open source, good quality | $$ |
| **Amazon Titan** | `amazon.titan-text-express-v1` | AWS native, cheaper | $ |
| **AI21 Jurassic** | `ai21.j2-ultra-v1` | Alternative option | $$$ |
| **Cohere Command** | `cohere.command-text-v14` | Alternative option | $$ |

Simply change the `BedrockModelId` parameter to switch models!

## RSS News Sources

The application fetches news from the following RSS feeds:

### MoneyControl
- **Market Reports**: `https://www.moneycontrol.com/rss/marketreports.xml`
- **Business News**: `https://www.moneycontrol.com/rss/business.xml`
- **Latest News**: `https://www.moneycontrol.com/rss/latestnews.xml`

### Economic Times
- **Stocks**: `https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms`
- **Markets**: `https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms`
- **Top Stories**: `https://economictimes.indiatimes.com/rssfeedstopstories.cms`

### Business Standard & Mint (NSE/BSE Coverage)
- **Business Standard Markets**: `https://www.business-standard.com/rss/markets-106.rss`
- **Business Standard Companies**: `https://www.business-standard.com/rss/companies-101.rss`
- **Mint Markets**: `https://www.livemint.com/rss/markets`

**Advantages of RSS Feeds:**
- ✅ **Reliable**: Official data sources from publishers
- ✅ **Structured**: Consistent data format
- ✅ **Fast**: No HTML parsing overhead
- ✅ **No Breaking**: Unlike web scraping, RSS feeds are stable
- ✅ **Ethical**: Using official feeds as intended

## Prerequisites

- Python 3.12
- AWS CLI configured
- AWS SAM CLI
- **AWS Bedrock access** (model access enabled in AWS Console)

## Quick Start

### 1. Enable Bedrock Model Access

**Important:** Before deploying, enable model access in AWS Bedrock:

```bash
# Open AWS Console > Bedrock > Model access
# OR use CLI:
aws bedrock list-foundation-models --region us-east-1

# Request access to Claude 3.5 Sonnet (or your preferred model)
```

Models must be enabled in your AWS account before use!

### 2. Clone and Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your values (no API key needed!)
nano .env
```

### 3. Build and Deploy

```bash
# Build
sam build

# Deploy with default model (Claude 3.5 Sonnet)
sam deploy --guided

# OR deploy with different model
sam deploy --parameter-overrides BedrockModelId=anthropic.claude-3-haiku-20240307-v1:0
```

### 4. Test

```bash
# Get API endpoint
API_URL=$(aws cloudformation describe-stacks \
    --stack-name premarket-suggester \
    --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
    --output text)

# Test health
curl $API_URL/health

# Generate watchlist (takes 1-3 minutes)
curl $API_URL/watchlist
```

## API Endpoints

Base URL: `https://{api-id}.execute-api.{region}.amazonaws.com/{stage}`

### GET /watchlist
Generate fresh watchlist in real-time

**Response:**
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
      "total_news_fetched": 45,
      "total_analyzed": 38,
      "watchlist_size": 8,
      "bullish_count": 5,
      "bearish_count": 3
    }
  }
}
```

### GET /health
Health check endpoint

**Response Time:** 1-3 minutes (fetches & analyzes news in real-time)

## Configuration

### Switching Models

**Option 1: At Deploy Time**
```bash
sam deploy --parameter-overrides BedrockModelId=meta.llama3-70b-instruct-v1:0
```

**Option 2: Update Environment Variable**
```bash
aws lambda update-function-configuration \
    --function-name premarket-suggester-WatchlistGenerator \
    --environment Variables={BEDROCK_MODEL_ID=amazon.titan-text-express-v1}
```

**Option 3: Update Stack**
```bash
# Edit samconfig.toml
parameter_overrides = "BedrockModelId=anthropic.claude-3-haiku-20240307-v1:0"

# Redeploy
sam deploy
```

### Environment Variables

Key variables:
- `BEDROCK_MODEL_ID`: Bedrock model identifier (see supported models above)
- `NEWS_SOURCES_ENABLED`: Comma-separated list of sources
- `MAX_WATCHLIST_SIZE`: Maximum stocks in watchlist (default: 10)
- `LLM_TEMPERATURE`: Model temperature 0.0-1.0 (default: 0.3)
- `LLM_MAX_TOKENS`: Max response tokens (default: 1000)

## Development

### Running Locally

```bash
# Ensure AWS credentials have Bedrock permissions
aws sts get-caller-identity

# Start local API
sam local start-api --env-vars env.json

# Test endpoint
curl http://localhost:3000/watchlist
```

### Testing Different Models Locally

```bash
# Edit env.json
{
  "WatchlistAPIFunction": {
    "BEDROCK_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0"
  }
}

# Restart local API
sam local start-api --env-vars env.json
```

## Cost Estimation with Bedrock

**Per Request (30-50 news items analyzed):**

| Model | Lambda | Bedrock API | Total/Request |
|-------|--------|-------------|---------------|
| Claude 3.5 Sonnet | $0.02 | $0.15-0.25 | **$0.17-0.27** |
| Claude 3 Haiku | $0.02 | $0.03-0.05 | **$0.05-0.07** |
| Llama 3 70B | $0.02 | $0.08-0.12 | **$0.10-0.14** |
| Amazon Titan | $0.02 | $0.01-0.02 | **$0.03-0.04** |

**Monthly (with daily scheduled execution):**

| Model | Daily | Monthly | + API Gateway | Total |
|-------|-------|---------|---------------|-------|
| Claude 3.5 Sonnet | $0.22 | $6.60 | +$3 | **~$10/month** |
| Claude 3 Haiku | $0.06 | $1.80 | +$3 | **~$5/month** |
| Llama 3 70B | $0.12 | $3.60 | +$3 | **~$7/month** |
| Amazon Titan | $0.035 | $1.05 | +$3 | **~$4/month** |

**Recommendation:** Start with Claude 3 Haiku for cost-effective quality!

## Advantages of This Architecture

### RSS Feeds vs Web Scraping

✅ **Reliable** - Official feeds don't break with website redesigns
✅ **Fast** - Structured XML parsing vs HTML parsing
✅ **Ethical** - Using official publisher APIs
✅ **No Rate Limiting** - RSS feeds are meant for consumption
✅ **Better Data Quality** - Clean, structured content
✅ **Lower Maintenance** - No selector updates needed

### Bedrock vs Direct API Calls (Anthropic/OpenAI)

✅ **No API Key Management** - IAM-based, no Secrets Manager needed
✅ **Model Agnostic** - Switch models without code changes
✅ **AWS Native** - Better integration with Lambda, CloudWatch
✅ **Unified Billing** - All in AWS bill, easier tracking
✅ **Better Compliance** - Data stays in AWS
✅ **Region Flexibility** - Use models in your preferred region

### Stateless vs Database Architecture

✅ **Simpler** - No database to manage
✅ **Cheaper** - No DynamoDB costs
✅ **Always Fresh** - Real-time data on every request
✅ **Easier Debugging** - Single code path
✅ **No Data Sync Issues** - Everything generated fresh

## Monitoring

### CloudWatch Logs

```bash
# View logs
sam logs -n WatchlistGeneratorFunction --tail

# Filter for Bedrock calls
sam logs -n WatchlistGeneratorFunction --tail --filter "Bedrock"
```

### Key Metrics

- Request duration
- News sources success rate
- **Bedrock API success rate**
- **Bedrock model latency**
- Watchlist generation success rate

### Bedrock-Specific Monitoring

```bash
# Check Bedrock usage
aws cloudwatch get-metric-statistics \
    --namespace AWS/Bedrock \
    --metric-name Invocations \
    --dimensions Name=ModelId,Value=anthropic.claude-3-5-sonnet-20241022-v2:0 \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-12T00:00:00Z \
    --period 3600 \
    --statistics Sum
```

## Troubleshooting

### Bedrock model not accessible
- **Issue**: AccessDeniedException
- **Solution**: Enable model access in AWS Console > Bedrock > Model access

### Bedrock rate limit
- **Issue**: ThrottlingException
- **Solution**: Request quota increase or reduce request rate

### Model not available in region
- **Issue**: ValidationException
- **Solution**: Check model availability: `aws bedrock list-foundation-models --region us-east-1`

### Wrong output format
- **Issue**: Different models return different formats
- **Solution**: LLM client automatically handles different model formats

### RSS feed not fetching
- **Issue**: Empty news items or feed errors
- **Solution**:
  - Check CloudWatch logs for specific feed errors
  - Verify RSS feed URLs are accessible
  - Some feeds may be temporarily unavailable - others will continue to work
  - Use `feedparser` error messages to debug specific feed issues

### Low news volume
- **Issue**: Fewer news items than expected
- **Solution**:
  - RSS feeds may be slow to update during off-market hours
  - Check individual feed URLs in browser
  - Consider adding more RSS sources if needed

## Security

- ✅ **No API keys** - IAM-based authentication
- ✅ **No Secrets Manager** - Simplified security
- ✅ IAM roles follow least-privilege
- ✅ No data stored anywhere
- ✅ All requests are independent
- ✅ Bedrock data stays in AWS

## Model Selection Guide

**For Production (Best Quality):**
- Use `anthropic.claude-3-5-sonnet-20241022-v2:0`
- Most accurate analysis
- Best structured output

**For Cost Optimization:**
- Use `anthropic.claude-3-haiku-20240307-v1:0`
- 80% of Sonnet quality at 20% cost
- Fast response times

**For Open Source:**
- Use `meta.llama3-70b-instruct-v1:0`
- No vendor lock-in
- Good quality

**For Maximum Savings:**
- Use `amazon.titan-text-express-v1`
- AWS native, lowest cost
- Acceptable quality for many use cases

## Support

For issues:
- Check CloudWatch logs
- Verify Bedrock model access is enabled
- Test RSS feeds individually (check URLs in browser)
- Try different Bedrock models
- Verify feedparser is working correctly
- Check `claude.md` for detailed docs

## License

Private project - All rights reserved

## Acknowledgments

- Built with AWS SAM and Python
- Powered by **AWS Bedrock** (model-agnostic AI)
- News ingestion via **RSS feeds** from MoneyControl, Economic Times, Business Standard, and Mint
- Uses `feedparser` for reliable RSS parsing
- Follows AntStack engineering best practices
- Stateless architecture for simplicity
