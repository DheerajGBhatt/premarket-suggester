"""LLM prompts for news analysis."""

SYSTEM_PROMPT = """You are a financial news analyst specializing in intraday trading for Indian stock markets (NSE/BSE).

Your role is to:
1. Extract relevant NSE/BSE stock symbols from news articles
2. Analyze the news for immediate intraday trading impact

Key Guidelines:
- Focus ONLY on same-day trading impact, not long-term fundamentals
- Consider immediate market reaction potential
- Be objective and avoid speculative language
- Ignore news that's already priced in or old
- Consider news timing relative to market hours
- Extract only valid NSE/BSE-listed stock symbols

You must respond with ONLY valid JSON, no additional text."""

ANALYSIS_PROMPT_TEMPLATE = """Analyze the following news for intraday trading impact:

Stock Symbol: {stock_symbol}
News Title: {news_title}
News Content: {news_content}

Provide your analysis in the following JSON format:
{{
  "event_type": "Earnings|Order|Regulatory|Macro|Other",
  "direction": "BULLISH|BEARISH|NEUTRAL",
  "impact_strength": <integer 1-5, where 1=minimal, 5=major>,
  "confidence": <float 0.0-1.0, your confidence in this analysis>,
  "rationale": "<one-line explanation, max 200 characters>"
}}

Analysis Rules:
1. event_type: Classify the news type
   - Earnings: Quarterly results, profit announcements
   - Order: New contracts, orders won/lost
   - Regulatory: Compliance, legal, regulatory changes
   - Macro: Market-wide events, economic indicators
   - Other: Everything else

2. direction: Expected intraday price movement
   - BULLISH: Likely to push price up today
   - BEARISH: Likely to push price down today
   - NEUTRAL: Minimal/unclear impact

3. impact_strength: Magnitude of expected impact (1-5)
   - 5: Major catalyst (>3% expected move)
   - 4: Strong catalyst (2-3% expected move)
   - 3: Moderate catalyst (1-2% expected move)
   - 2: Minor catalyst (<1% expected move)
   - 1: Negligible catalyst

4. confidence: Your confidence level (0.0-1.0)
   - 0.9-1.0: Very confident (clear, unambiguous news)
   - 0.7-0.89: Confident (news is clear but market reaction uncertain)
   - 0.5-0.69: Moderate confidence (mixed signals)
   - <0.5: Low confidence (unclear impact)

5. rationale: Concise explanation
   - One line, max 200 characters
   - State the key reason for your assessment
   - No speculation, only facts from the news

Respond with ONLY the JSON object, no additional text."""


def format_analysis_prompt(stock_symbol: str, news_title: str, news_content: str) -> str:
    """Format the analysis prompt with news details.

    Args:
        stock_symbol: Stock symbol
        news_title: News title
        news_content: News content

    Returns:
        str: Formatted prompt
    """
    return ANALYSIS_PROMPT_TEMPLATE.format(
        stock_symbol=stock_symbol or "Unknown",
        news_title=news_title[:500],  # Limit title length
        news_content=news_content[:2000]  # Limit content length for token optimization
    )


# Combined extraction and analysis prompt (single LLM call)
COMBINED_ANALYSIS_PROMPT_TEMPLATE = """Analyze the following news article for intraday trading:

News Title: {news_title}
News Content: {news_content}

Provide your analysis in the following JSON format:
{{
  "stock_symbol": "<NSE/BSE stock symbol or null if not applicable>",
  "event_type": "Earnings|Order|Regulatory|Macro|Other",
  "direction": "BULLISH|BEARISH|NEUTRAL",
  "impact_strength": <integer 1-5, where 1=minimal, 5=major>,
  "confidence": <float 0.0-1.0, your confidence in this analysis>,
  "rationale": "<one-line explanation, max 200 characters>"
}}

Stock Symbol Extraction Rules:
- Extract the PRIMARY NSE/BSE-listed stock symbol most relevant to this news
- If a company name is mentioned, return its correct NSE/BSE stock symbol (e.g., "Reliance Industries" → "RELIANCE")
- If no specific company is mentioned but sector impact is clear, return the most affected major stock
- Return null if no relevant Indian stock can be identified
- Ignore indices (NIFTY, SENSEX), commodities, or non-NSE/BSE stocks

Analysis Rules:
1. event_type: Classify the news type
   - Earnings: Quarterly results, profit announcements
   - Order: New contracts, orders won/lost
   - Regulatory: Compliance, legal, regulatory changes
   - Macro: Market-wide events, economic indicators
   - Other: Everything else

2. direction: Expected intraday price movement
   - BULLISH: Likely to push price up today
   - BEARISH: Likely to push price down today
   - NEUTRAL: Minimal/unclear impact

3. impact_strength: Magnitude of expected impact (1-5)
   - 5: Major catalyst (>3% expected move)
   - 4: Strong catalyst (2-3% expected move)
   - 3: Moderate catalyst (1-2% expected move)
   - 2: Minor catalyst (<1% expected move)
   - 1: Negligible catalyst

4. confidence: Your confidence level (0.0-1.0)
   - 0.9-1.0: Very confident
   - 0.7-0.89: Confident
   - 0.5-0.69: Moderate confidence
   - <0.5: Low confidence

5. rationale: Concise explanation (max 200 characters)

Respond with ONLY the JSON object, no additional text."""


def format_combined_analysis_prompt(news_title: str, news_content: str) -> str:
    """Format the combined extraction and analysis prompt.

    Args:
        news_title: News title
        news_content: News content

    Returns:
        str: Formatted prompt
    """
    return COMBINED_ANALYSIS_PROMPT_TEMPLATE.format(
        news_title=news_title[:500],
        news_content=news_content[:2000]
    )
