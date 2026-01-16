# Technical Design Document

## System Name

AI Intraday Stock Suggester – Pre-Market News Based (Live RSS)

---

## 1. Architecture Overview

The system is a **stateless, API-driven AWS-native application** designed to ingest  **live RSS feeds on demand** , analyze them using an LLM (Amazon Bedrock), and return an  **intraday watchlist response synchronously via API** .

There is  **no scheduled execution, no background jobs, and no persistent database** . All computation happens at request time.

### High-Level Architecture

```
Client (UI / Curl / Bot)
   ↓
API Gateway
   ↓
FastAPI Lambda (AWS SAM)
   ↓
Live RSS Fetch (In-memory)
   ↓
Amazon Bedrock (via Strands)
   ↓
Scoring & Ranking (In-memory)
   ↓
API Response (Watchlist JSON)
```

---

## 2. Technology Stack

### Infrastructure

* **AWS Cloud**
* **AWS SAM** (Serverless Application Model)
* **AWS Lambda** (Python 3.11 runtime)
* **Amazon API Gateway**

### AI / LLM

* **Amazon Bedrock**
* Model options:
  * Claude Haiku (default, low latency)
  * Claude Sonnet (optional, higher reasoning)

### SDK / Framework

* **Strands SDK** (Bedrock orchestration)
* **FastAPI** (single API surface)
* **Python**

## 3. Infrastructure Design (AWS)

### 3.1 AWS SAM Stack

The SAM stack defines a  **single Lambda-backed API** .

Resources include:

* One Lambda function (FastAPI)
* API Gateway
* IAM role for Bedrock access

There are  **no scheduled jobs or databases** .

---

## 4. Lambda Function

### 4.1 WatchlistAPIFunction (Single Function)

 **Purpose** :

* Fetch live RSS feeds at request time
* Deduplicate and normalize news
* Invoke Amazon Bedrock via Strands
* Score and rank stocks
* Return intraday watchlist synchronously

 **Trigger** :

* API Gateway (`GET /watchlist`)

 **Execution Characteristics** :

* Cold start tolerant
* Max execution time: 10–15 seconds
* Entire flow runs in-memory

---

### 4.2 NewsAnalysisFunction

 **Purpose** :

* Read aggregated RSS payload
* Invoke Amazon Bedrock via Strands SDK
* Extract structured intraday intelligence

 **LLM Output Schema** :

```json
{
  "symbol": "string",
  "event_type": "EARNINGS | ORDER | REGULATORY | MACRO | OTHER",
  "direction": "Bullish | Bearish | Neutral",
  "impact_strength": 1,
  "confidence": 0.0,
  "reason": "string"
}
```

 **LLM Constraints** :

* News is pre-market only
* Focus strictly on same-day intraday tradability
* Ignore long-term fundamentals

---

### 4.3 ScoringFunction

 **Purpose** :

* Compute bias scores
* Rank stocks
* Generate final intraday watchlist

 **Scoring Logic** :

```text
Bias Score = impact_strength × confidence
```

 **Filtering Rules** :

* Bias Score ≥ 2.5 → High priority
* Bias Score 1.5–2.4 → Medium priority

---

### 4.4 WatchlistAPIFunction

 **Purpose** :

* Expose daily watchlist via REST API
* Support dashboard and alert delivery

 **Framework** :

* FastAPI

 **Endpoints** :

* `GET /watchlist/today`
* `GET /health`

---

## 5. Amazon Bedrock & Strands Integration

### 5.1 Strands SDK Responsibilities

* Prompt construction
* Model invocation
* Response validation
* Structured JSON parsing
* Retry & fallback handling

### 5.2 Prompting Strategy

The prompt explicitly states:

* News source is RSS
* Market has not opened
* Analysis is intraday-only

This avoids hallucination and long-term bias.

---

## 6. Data Handling Design

* RSS news is fetched live per API call
* No raw or processed news is persisted
* Watchlist exists only in API response

This enforces:

* Zero state
* No historical dependency
* Simplified compliance

---

## 7. Execution Model

* No scheduling
* No orchestration
* Client decides **when** to call the API

Typical usage:

* Manual call between 8:30–9:10 AM IST
* UI / bot can cache response externally if needed

------|-----|
| 08:00 | RSS ingestion |
| 08:30 | LLM analysis |
| 08:45 | Scoring & ranking |
| 09:00 | Watchlist available |

---

## 8. Security & IAM

### IAM Principles

* Least privilege
* Single execution role

### Required Permissions

* `bedrock:InvokeModel`
* CloudWatch Logs

No database or scheduler permissions required.

---

## 9. Observability & Monitoring

* CloudWatch Logs per Lambda
* Metrics:
  * RSS fetch failures
  * Bedrock latency
  * Cost per run
* Dead Letter Queues (DLQ) for failures

---

## 10. Error Handling & Resilience

* RSS fetch timeout (2–3 seconds per feed)
* Skip unavailable feeds
* Fallback to latest S3 cache if live RSS fails
* Graceful degradation: publish empty watchlist if no strong news

---

## 11. Deployment Flow

```bash
sam build
sam deploy --guided
```

Environments:

* dev
* prod

---

## 12. Cost Considerations

* RSS feeds are free
* Bedrock calls limited to pre-market window
* Batched LLM calls to minimize tokens

Estimated MVP cost: **Very low (< $1/day)**

---

## 13. Future Enhancements

* Persist analyzed news (not raw RSS)
* Sector-level sentiment aggregation
* Opening-range confirmation (news + price action)
* Post-market feedback loop

---

## 14. Summary

This updated design:

* Uses **live RSS feeds** instead of persistent news storage
* Persists only **actionable intelligence**
* Remains cost-efficient, scalable, and production-ready

> The system focuses on one goal:
> **Deliver a reliable, pre-market intraday watchlist driven purely by news.**
