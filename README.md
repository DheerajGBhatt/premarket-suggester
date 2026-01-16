# AI Intraday Stock Suggester - Pre-Market News Analysis

An AI-powered system that analyzes pre-market news and generates high-confidence intraday watchlists with directional bias in real-time using **AWS Bedrock**.

## Overview

This application helps intraday traders identify high-probability trading opportunities by:

- Ingesting news from Zerodha Pulse RSS feed (aggregated Indian market news)
- Using **AWS Bedrock** models (Claude, Llama, Titan, etc.) to extract stock symbols and analyze news impact in a **single optimized LLM call**
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
              1. Fetch News from Zerodha Pulse RSS
                      ↓
              2. Combined Extract + Analyze (Single LLM Call)
                 - Extract NSE/BSE stock symbol
                 - Analyze intraday trading impact
                 - Score confidence & direction
                      ↓
              3. Aggregate & Rank by Bias Score
                      ↓
              Return JSON Response
```


## Supported Bedrock Models

The application automatically adapts to different Bedrock models and supports **cross-region inference profiles** for high availability.

### Cross-Region Inference Profiles (Recommended)

| Model                                     | Inference Profile ID                             | Use Case                        |
| ----------------------------------------- | ------------------------------------------------ | ------------------------------- |
| **Claude 3.5 Sonnet** *(Default)* | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` | Best quality, high availability |
| **Claude 3 Haiku**                  | `us.anthropic.claude-3-haiku-20240307-v1:0`    | Fast, cost-effective            |
| **EU Region**                       | `eu.anthropic.claude-3-5-sonnet-20241022-v2:0` | EU data residency               |

### Single-Region Model IDs

| Model                       | Model ID                                      | Use Case                        |
| --------------------------- | --------------------------------------------- | ------------------------------- |
| **Claude 3.5 Sonnet** | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Best quality, accurate analysis |
| **Claude 3 Haiku**    | `anthropic.claude-3-haiku-20240307-v1:0`    | Fast, cost-effective            |
| **Llama 3 70B**       | `meta.llama3-70b-instruct-v1:0`             | Open source, good quality       |
| **Amazon Titan**      | `amazon.titan-text-express-v1`              | AWS native, lowest cost         |
| **AI21 Jurassic**     | `ai21.j2-ultra-v1`                          | Alternative option              |
| **Cohere Command**    | `cohere.command-text-v14`                   | Alternative option              |

Simply change the `BedrockModelId` parameter to switch models!

## News Source

The application fetches news from **Zerodha Pulse**, which aggregates Indian market news from multiple sources:

### Zerodha Pulse

- **RSS Feed**: `https://pulse.zerodha.com/feed.php`
- **Coverage**: NSE/BSE stocks, Indian market news
- **Sources**: Aggregated from MoneyControl, Economic Times, Business Standard, Mint, and more

**Why Zerodha Pulse?**

- ✅ **Aggregated**: Single feed with news from multiple publishers
- ✅ **Market-Focused**: Curated for Indian stock market traders
- ✅ **Reliable**: Official Zerodha service
- ✅ **Structured**: Consistent RSS format
- ✅ **Fast**: No HTML parsing overhead

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

# Generate watchlist (takes 1-3 minutes)
curl $API_URL/watchlist
```

## API Endpoints

Base URL: `https://{api-id}.execute-api.{region}.amazonaws.com/{stage}`

### GET /watchlist

Generate fresh watchlist in real-time.

**Response Time:** 1-3 minutes (fetches & analyzes news in real-time)

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

**Per Request (20-30 news items analyzed):**

| Model             | Lambda               | Bedrock API            | Total/Request |
| ----------------- | -------------------- | ---------------------- | ------------- |
| Claude 3.5 Sonnet | $0.02 | $0.08-0.12   | **$0.10-0.14**   |               |
| Claude 3 Haiku    | $0.02 | $0.015-0.025 | **$0.035-0.045** |               |
| Llama 3 70B       | $0.02 | $0.04-0.06   | **$0.06-0.08**   |               |
| Amazon Titan      | $0.02 | $0.005-0.01  | **$0.025-0.03**  |               |

**Monthly (with daily scheduled execution):**

| Model             | Daily          | Monthly                  | + API Gateway | Total |
| ----------------- | -------------- | ------------------------ | ------------- | ----- |
| Claude 3.5 Sonnet | $0.12 | $3.60  | +$3 |**~$7/month** |               |       |
| Claude 3 Haiku    | $0.04 | $1.20  | +$3 |**~$4/month** |               |       |
| Llama 3 70B       | $0.07 | $2.10  | +$3 |**~$5/month** |               |       |
| Amazon Titan      | $0.025 | $0.75 | +$3 |**~$4/month** |               |       |

**Recommendation:** Start with Claude 3 Haiku for cost-effective quality!

## Architecture Benefits

- **Single LLM Call** - Combined extraction + analysis per news item
- **Parallel Processing** - Concurrent analysis with ThreadPoolExecutor
- **Cross-Region Inference** - High availability with inference profiles
- **Aggregated News Source** - Zerodha Pulse provides curated market news
- **Model Agnostic** - Switch Bedrock models without code changes
- **IAM-based Auth** - No API keys to manage
- **Stateless** - No database, fresh analysis on every request
- **Serverless** - Pay-per-use with auto-scaling

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

### Zerodha Pulse feed not fetching

- **Issue**: Empty news items or feed errors
- **Solution**:
  - Check CloudWatch logs for specific feed errors
  - Verify `https://pulse.zerodha.com/feed.php` is accessible
  - Use `feedparser` error messages to debug feed issues

### Low news volume

- **Issue**: Fewer news items than expected
- **Solution**:
  - Zerodha Pulse may be slow to update during off-market hours
  - Check feed URL in browser: `https://pulse.zerodha.com/feed.php`
  - News volume is typically higher during market hours (9:15 AM - 3:30 PM IST)

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
- Test Zerodha Pulse feed in browser
- Try different Bedrock models
- Verify feedparser is working correctly
- Check `CLAUDE.md` for coding standards

## License

Private project - All rights reserved

## Acknowledgments

- Built with AWS SAM and Python 3.12
- Powered by **AWS Bedrock** with cross-region inference support
- News ingestion via **Zerodha Pulse** RSS feed
- Uses `feedparser` for reliable RSS parsing
- Uses `pydantic` for data validation
- Uses `aws_lambda_powertools` for logging and tracing
- Follows AntStack engineering best practices
- Stateless, cost-optimized architecture
