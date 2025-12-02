# LLM/Agent Architecture Documentation

## Overview

MarketGPT uses Large Language Models (LLMs) as intelligent agents to analyze financial news and extract actionable insights. The system employs a **Retrieval-Augmented Generation (RAG)** approach where news articles are first stored in a vector database, then retrieved and analyzed by the LLM to generate recommendations and answer questions.

## LLM Usage in MarketGPT

### 1. Stock Recommendation Extraction (`extract_stock_recommendations`)

**Purpose:** Analyze today's news articles to identify buy/sell signals for specific stocks.

**Flow:**
```
Today's Articles (ChromaDB)
  ↓
Batch Processing (5 articles per batch)
  ↓
LLM Analysis (with structured prompt)
  ↓
JSON Response Parsing
  ↓
Validation & Storage (SQLite)
```

**Current Process:**
1. Fetches all articles published today from ChromaDB
2. Processes articles in batches of 5 to avoid overwhelming the LLM
3. Sends each batch to the LLM with a structured prompt
4. LLM returns JSON array of recommendations
5. Recommendations are stored directly in SQLite (with minimal validation)

**Prompt Structure:**
- **System Message:** Defines the agent as a financial analyst with specific rules
- **User Message:** Contains article titles, URLs, and content (truncated to 1000 chars)

**Current Issues:**
- ❌ No validation of ticker symbols
- ❌ No filtering of non-tradeable entities (countries, currencies, etc.)
- ❌ Weak prompt instructions about what constitutes a valid stock
- ❌ No format validation before storage
- ❌ Temperature set to 0.7 (may be too high for structured output)

### 2. Q&A Chat Interface (`/ask` route)

**Purpose:** Answer user questions about the market using retrieved news articles.

**Flow:**
```
User Question
  ↓
Semantic Search (Vector Similarity)
  ↓
Retrieve Top 5 Articles
  ↓
LLM Analysis (with context)
  ↓
Formatted Response (Markdown)
```

**Current Process:**
1. User submits a question
2. Question is embedded using SentenceTransformers
3. Vector search finds top 25 articles, then filters to top 5 by date
4. Articles are sent to LLM as context
5. LLM generates answer based on retrieved context
6. Response is rendered as markdown

**Prompt Structure:**
- **System Message:** Defines agent as MarketGPT financial assistant
- **User Message:** Includes article context and user question

### 3. Market Report Summarization (`summarize_market_report`)

**Purpose:** Generate a concise summary of the daily market report.

**Flow:**
```
Market Report (Markdown)
  ↓
LLM Analysis
  ↓
Summary (Markdown)
```

## Current Prompt for Stock Recommendations

```python
"""You are a financial analyst. Analyze news articles and identify any stock buy/sell signals. 
Be careful to not make up ticker symbols or to suggest buy/sell recommendations on things that 
are not stocks, bonds, mutual funds, or ETFs. If you are unsure, do not provide a suggestion.

Look for:
- Company earnings beats/misses
- Analyst upgrades/downgrades
- New product launches or innovations
- Regulatory approvals/rejections
- Management changes
- Market share gains/losses
- Financial guidance changes

Respond ONLY with a JSON array of recommendations. Each recommendation should have:
{
  "company": "Company Name",
  "ticker": "STOCK_SYMBOL",
  "recommendation": "BUY" or "SELL",
  "reason": "Brief reason for recommendation",
  "confidence": "HIGH", "MEDIUM", or "LOW",
  "article_title": "Article title",
  "article_url": "Article URL"
}

If no clear recommendations, return empty array [].
DO NOT include any text outside the JSON array. Especially do not include any markdown or HTML 
formatting like backticks. Do not explain your reasoning or provide any additional commentary. 
Just return the JSON array."""
```

## Problems with Current Implementation

### 1. **Weak Validation Rules**
- Prompt says "be careful" but doesn't provide concrete examples
- No explicit list of what NOT to recommend (countries, currencies, commodities, etc.)
- No ticker format validation

### 2. **No Pre-Storage Validation**
- Recommendations are stored directly without checking:
  - If ticker is a valid format (1-5 uppercase letters)
  - If company name is reasonable
  - If recommendation type is valid
  - If the entity is actually tradeable

### 3. **Temperature Too High**
- Temperature of 0.7 can lead to creative but incorrect responses
- For structured JSON output, lower temperature (0.2-0.3) is better

### 4. **No Examples in Prompt**
- LLMs perform better with few-shot examples
- Should include examples of valid and invalid recommendations

## Recommended Improvements

### 1. Enhanced Prompt with Examples

Add concrete examples and validation rules:

```python
"""You are a financial analyst specializing in stock recommendations. Your task is to analyze 
news articles and identify actionable buy/sell signals for publicly traded stocks ONLY.

CRITICAL RULES:
1. ONLY recommend stocks (publicly traded companies with ticker symbols)
2. DO NOT recommend: countries, currencies, commodities, cryptocurrencies, indices, sectors, 
   or any non-tradeable entities
3. Ticker symbols must be 1-5 uppercase letters (e.g., AAPL, TSLA, MSFT)
4. Company name must be the actual legal company name, not a country or concept
5. If an article mentions "Canada" or "oil prices" or "tech sector" - DO NOT create a 
   recommendation for these

VALID EXAMPLES:
✅ {"company": "Apple Inc", "ticker": "AAPL", "recommendation": "BUY", ...}
✅ {"company": "Tesla Inc", "ticker": "TSLA", "recommendation": "SELL", ...}

INVALID EXAMPLES (DO NOT CREATE THESE):
❌ {"company": "Canada", "ticker": "CAN", ...} - Canada is not a stock
❌ {"company": "Oil Sector", "ticker": "OIL", ...} - Sector is not a stock
❌ {"company": "Technology", "ticker": "TECH", ...} - Concept is not a stock
❌ {"company": "Bitcoin", "ticker": "BTC", ...} - Cryptocurrency is not a stock

Look for these signals:
- Company earnings beats/misses
- Analyst upgrades/downgrades with specific company names
- New product launches by named companies
- Regulatory approvals/rejections for specific companies
- Management changes at specific companies
- Market share gains/losses by named companies
- Financial guidance changes from specific companies

Respond ONLY with a valid JSON array. Each recommendation must have:
{
  "company": "Full Legal Company Name",
  "ticker": "TICKER (1-5 uppercase letters)",
  "recommendation": "BUY" or "SELL",
  "reason": "Brief specific reason",
  "confidence": "HIGH", "MEDIUM", or "LOW",
  "article_title": "Exact article title",
  "article_url": "Exact article URL"
}

If no valid stock recommendations found, return empty array: []

DO NOT include markdown, backticks, or any text outside the JSON array."""
```

### 2. Pre-Storage Validation Function

Add validation before storing:

```python
def validate_recommendation(rec):
    """
    Validate a recommendation before storing.
    Returns (is_valid, error_message)
    """
    # Check required fields
    required_fields = ["company", "ticker", "recommendation", "reason", "confidence", 
                      "article_title", "article_url"]
    for field in required_fields:
        if field not in rec or not rec[field]:
            return False, f"Missing required field: {field}"
    
    # Validate ticker format (1-5 uppercase letters)
    ticker = rec["ticker"].strip().upper()
    if not re.match(r'^[A-Z]{1,5}$', ticker):
        return False, f"Invalid ticker format: {ticker} (must be 1-5 uppercase letters)"
    
    # Validate recommendation type
    if rec["recommendation"].upper() not in ["BUY", "SELL"]:
        return False, f"Invalid recommendation type: {rec['recommendation']}"
    
    # Validate confidence level
    if rec["confidence"].upper() not in ["HIGH", "MEDIUM", "LOW"]:
        return False, f"Invalid confidence level: {rec['confidence']}"
    
    # Check for common invalid entities
    invalid_keywords = ["country", "currency", "commodity", "sector", "index", 
                       "market", "economy", "government", "federal", "central bank"]
    company_lower = rec["company"].lower()
    if any(keyword in company_lower for keyword in invalid_keywords):
        return False, f"Invalid entity type: {rec['company']} (appears to be a non-stock entity)"
    
    # Check for country names (common mistake)
    common_countries = ["canada", "mexico", "china", "japan", "germany", "france", 
                       "italy", "spain", "uk", "united kingdom", "australia", "brazil"]
    if company_lower in common_countries:
        return False, f"Invalid entity: {rec['company']} is a country, not a stock"
    
    return True, None
```

### 3. Lower Temperature for Structured Output

Change temperature from 0.7 to 0.2-0.3 for more deterministic JSON output.

### 4. Add Validation Logging

Log validation failures to help improve prompts:

```python
validated_recs = []
for rec in batch_recommendations:
    is_valid, error = validate_recommendation(rec)
    if is_valid:
        validated_recs.append(rec)
    else:
        print(f"[VALIDATION] Rejected recommendation: {error}")
        print(f"[VALIDATION] Recommendation: {rec}")
```

## Data Flow Diagram

```
┌─────────────────┐
│  News Articles  │
│   (ChromaDB)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Batch Articles │
│   (5 per batch) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Prompt     │
│  (Enhanced)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Response   │
│  (JSON Array)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Validation     │
│  (Pre-Storage)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite Storage │
│  (Valid Only)   │
└─────────────────┘
```

## Configuration

**Temperature Settings:**
- Stock Recommendations: 0.2-0.3 (structured output)
- Q&A Chat: 0.7 (conversational)
- Report Summarization: 0.5 (balanced)

**Batch Sizes:**
- Stock Recommendations: 5 articles per batch
- Q&A: Top 5 articles by relevance and date

## Future Enhancements

1. **Ticker Symbol Lookup:** Validate tickers against a real stock database
2. **Confidence Scoring:** Use multiple LLM passes to validate recommendations
3. **Entity Extraction:** Use NER to identify company names before recommendation
4. **Feedback Loop:** Track which recommendations were accurate to improve prompts
5. **Multi-Model Validation:** Use a second LLM to validate recommendations

