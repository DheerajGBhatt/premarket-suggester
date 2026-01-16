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

Build an AI-powered system that analyzes **pre-market news only** and generates a **high-confidence intraday watchlist** with directional bias before market open.

The system does **not** predict prices or automate trades.

---

## 3. Goals & Non-Goals

### Goals

- Identify stocks likely to move intraday due to news
- Classify direction (Bullish / Bearish / Neutral)
- Estimate impact strength and confidence
- Generate a concise watchlist before market open

### Non-Goals

- No price prediction
- No automated trade execution
- No technical indicator analysis
- No long-term investment recommendations

---

## 4. Target Users

- Active intraday traders
- Proprietary trading desks (manual execution)
- Retail traders using price-action strategies

---

## 5. Key User Workflow

1. System ingests pre-market news (before 9:00 AM IST)
2. AI analyzes news for intraday relevance
3. Stocks are scored and ranked
4. Trader receives a prioritized watchlist
5. Trader confirms entries using price action after market open

---

## 6. Data Sources

### News Sources

- NSE & BSE corporate announcements
- Company earnings releases
- Financial news portals (Moneycontrol, Economic Times – Markets)
- Global market cues (US markets, commodities, indices)

### Constraints

- News must be published between previous market close and 9:00 AM IST

---

## 7. Core Features

### 7.1 News Ingestion

- Scheduled pre-market ingestion (Cron-based)
- Deduplication of identical news
- Company symbol mapping

### 7.2 AI News Analysis

AI extracts structured insights from unstructured news.

For each stock:

- Event type (Earnings, Order, Regulatory, Macro, etc.)
- Expected intraday direction (Bullish / Bearish / Neutral)
- Impact strength (1–5)
- Confidence score (0–1)
- One-line rationale

### 7.3 Bias Scoring Engine

Compute a bias score:

```
Bias Score = Impact Strength × Confidence
```

Threshold-based filtering:

- Bias Score ≥ 2.5 → High priority
- Bias Score 1.5–2.4 → Medium priority

### 7.4 Watchlist Generation

- Ranked list of 5–10 stocks
- Grouped by Bullish / Bearish
- Sector tagging (optional)

---

## 8. Output Format

### Example Output

```
🔥 Intraday Watchlist – Pre-Market News

1. TATASTEEL – BULLISH (High)
   Reason: Strong earnings beat with margin expansion

2. INFY – BEARISH (Medium)
   Reason: Weak guidance and cautious outlook
```

---

## 9. AI Prompting Strategy

The AI must:

- Ignore long-term fundamentals
- Focus only on same-day tradability
- Avoid speculative language
- Produce structured JSON output

---

## 10. Success Metrics

### Quantitative

- % of watchlist stocks showing ≥ 1% intraday move
- Directional accuracy (Bullish vs Bearish)
- Average move during first 90 minutes

### Qualitative

- Trader feedback on usefulness
- Reduction in pre-market analysis time

---

## 11. Risk & Constraints

- News interpretation is probabilistic, not deterministic
- False positives on low-liquidity stocks
- Overreaction to already-priced-in news

Mitigations:

- Liquidity filters
- Confidence thresholds
- Manual confirmation post-market open

---

## 12. Tech Stack (Proposed)

### Backend

- Python
- LLM API (GPT / Claude / Gemini)
- FastAPI

### Storage

- PostgreSQL (news + outputs)

### Delivery

- Web dashboard
- Telegram / Slack alerts

---

## 13. MVP Scope (Phase 1)

Included:

- Pre-market news ingestion
- AI-based analysis
- Watchlist generation
- Manual validation

Excluded:

- Live market data
- Trade execution
- Backtesting

---

## 14. Future Enhancements

- Sector-level sentiment aggregation
- Gap-up / gap-down validation
- Post-market performance feedback loop
- Hybrid model (news + early price action)

---

## 15. Timeline

| Phase                 | Duration |
| --------------------- | -------- |
| Data ingestion        | 1 day    |
| AI analysis & prompts | 1–2 days |
| Scoring & watchlist   | 1 day    |
| Alerts & UI           | 1 day    |

**Total MVP Time: ~5 days**

---

## 16. Final Note

This system is designed to **improve preparedness** , not replace trader judgment.

> "The edge is knowing _what to watch_ before the bell rings."
