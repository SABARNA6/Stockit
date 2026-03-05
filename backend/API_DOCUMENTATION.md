# Stockit Backend API Documentation

## Base URL
```
http://localhost:5000
```

## Overview
The Stockit API provides endpoints for retrieving stock market data, financial metrics, news analysis, and sentiment analysis using FinBERT for Indian stock market (NSE - National Stock Exchange).

---

## Endpoints

### 1. Serve Index

**Endpoint:** `GET /`

**Description:** Serves the frontend static files (index.html)

**Response:** HTML file (Frontend application)

---

### 2. Get Nifty 50 Companies

**Endpoint:** `GET /api/nifty50`

**Method:** GET

**Description:** Retrieves a list of all Nifty 50 companies with basic information.

**Query Parameters:** None

**Response:** 
```json
[
  {
    "Symbol": "RELIANCE",
    "Company Name": "Reliance Industries Limited",
    "Speciality": "Oil & Gas"
  },
  {
    "Symbol": "TCS",
    "Company Name": "Tata Consultancy Services",
    "Speciality": "Information Technology"
  }
]
```

**Error Responses:**
- `500 Internal Server Error` - If data fetch fails

**Example cURL:**
```bash
curl http://localhost:5000/api/nifty50
```

---

### 3. Get News (Test Endpoint)

**Endpoint:** `GET /api/test`

**Method:** GET

**Description:** Retrieves raw news data for a given stock symbol using Yahoo Finance.

**Query Parameters:**
| Parameter | Type   | Required | Description          |
|-----------|--------|----------|----------------------|
| symbol    | string | Yes      | Stock ticker symbol  |

**Response:**
```json
[
  {
    "uuid": "abc123...",
    "title": "Company announces Q3 results",
    "link": "https://...",
    "source": "Reuters",
    "providerPublishTime": 1704067200
  }
]
```

**Error Responses:**
- `400 Bad Request` - If symbol parameter is missing

**Example cURL:**
```bash
curl "http://localhost:5000/api/test?symbol=RELIANCE"
```

---

### 4. Get Company Info

**Endpoint:** `GET /api/company/info`

**Method:** GET

**Description:** Retrieves detailed information about a company including name, current price, and business summary.

**Query Parameters:**
| Parameter | Type   | Required | Description                    |
|-----------|--------|----------|--------------------------------|
| symbol    | string | Yes      | Stock ticker symbol (e.g., TCS) |

**Response:**
```json
{
  "Company Name": "Tata Consultancy Services Limited",
  "Symbol": "TCS",
  "Price": 3850.50,
  "Short Summary": "TCS is an IT services company..."
}
```

**Error Responses:**
- `400 Bad Request` - If symbol parameter is missing

**Example cURL:**
```bash
curl "http://localhost:5000/api/company/info?symbol=TCS"
```

---

### 5. Get Stock History (OCHLV Data)

**Endpoint:** `GET /api/company/history`

**Method:** GET

**Description:** Retrieves historical stock price data (Open, Close, High, Low, Volume) for a given date range.

**Query Parameters:**
| Parameter | Type   | Required | Description                           |
|-----------|--------|----------|---------------------------------------|
| symbol    | string | Yes      | Stock ticker symbol                   |
| start     | string | Yes      | Start date (format: YYYY-MM-DD)       |
| end       | string | Yes      | End date (format: YYYY-MM-DD)         |

**Response:**
```json
[
  {
    "Date": "2023-01-01",
    "Open": 2500.00,
    "Close": 2520.50,
    "High": 2540.00,
    "Low": 2495.00,
    "Volume": 15000000
  },
  {
    "Date": "2023-01-02",
    "Open": 2520.50,
    "Close": 2535.25,
    "High": 2545.00,
    "Low": 2515.00,
    "Volume": 18000000
  }
]
```

**Error Responses:**
- `400 Bad Request` - If any required parameters are missing

**Example cURL:**
```bash
curl "http://localhost:5000/api/company/history?symbol=RELIANCE&start=2023-01-01&end=2023-01-31"
```

---

### 6. Get Financial Metrics

**Endpoint:** `GET /api/company/financials`

**Method:** GET

**Description:** Retrieves key financial metrics for a company including revenue, net profit, and EBITDA margin.

**Query Parameters:**
| Parameter | Type   | Required | Description              |
|-----------|--------|----------|--------------------------|
| symbol    | string | Yes      | Stock ticker symbol      |

**Response:**
```json
{
  "Revenue": 150000000000,
  "Net Profit": 35000000000,
  "EBITDA Margin": 22.5
}
```

**Error Responses:**
- `400 Bad Request` - If symbol parameter is missing
- `500 Internal Server Error` - If financial data is unavailable

**Example cURL:**
```bash
curl "http://localhost:5000/api/company/financials?symbol=INFY"
```

---

### 7. Search Company

**Endpoint:** `GET /api/company/search`

**Method:** GET

**Description:** Searches for company information. First attempts to fetch from Google Sheets API (if configured), then falls back to news analysis if no results are found.

**Query Parameters:**
| Parameter | Type   | Required | Description         |
|-----------|--------|----------|---------------------|
| symbol    | string | Yes      | Stock ticker symbol |

**Response:** 
```json
{
  "data": [
    {
      "confidence": 0.87,
      "pubdate": "2024-01-15",
      "sentiment": "Positive",
      "summary": "Company announces strong Q3 earnings...",
      "symbol": "ADANIPORTS",
      "title": "ADANIPORTS: Record Q3 Performance"
    }
  ]
}
```

**Error Responses:**
- `400 Bad Request` - If symbol parameter is missing

**Example cURL:**
```bash
curl "http://localhost:5000/api/company/search?symbol=ADANIPORTS"
```

---

### 8. Analyze Full News

**Endpoint:** `GET /api/news/analyze-full`

**Method:** GET

**Description:** Fetches news articles for a symbol and performs sentiment analysis on each headline using FinBERT AI model. Provides detailed sentiment analysis with confidence scores.

**Query Parameters:**
| Parameter | Type   | Required | Description         |
|-----------|--------|----------|---------------------|
| symbol    | string | Yes      | Stock ticker symbol |

**Response:**
```json
{
  "data": [
    {
      "confidence": 0.92,
      "pubdate": "2024-01-20T10:30:00",
      "sentiment": "Positive",
      "summary": "Strong revenue growth reported",
      "symbol": "TATAMOTORS",
      "title": "TATAMOTORS Posts Strong Q3 Results"
    },
    {
      "confidence": 0.78,
      "pubdate": "2024-01-19T14:15:00",
      "sentiment": "Neutral",
      "summary": "Company initiates new project",
      "symbol": "TATAMOTORS",
      "title": "TATAMOTORS Announces New Venture"
    }
  ]
}
```

**Response Fields:**
- `confidence` (number): Confidence score of sentiment analysis (0-1)
- `pubdate` (string): Publication date/time
- `sentiment` (string): Sentiment classification (Positive, Negative, Neutral)
- `summary` (string): Brief summary of the news
- `symbol` (string): Stock ticker symbol
- `title` (string): News headline title

**Error Responses:**
- `400 Bad Request` - If symbol parameter is missing
- `200 OK` - Returns empty data array if no news found

**Example cURL:**
```bash
curl "http://localhost:5000/api/news/analyze-full?symbol=TCS"
```

---

### 9. Analyze News Sentiment (POST)

**Endpoint:** `POST /api/news/analyze`

**Method:** POST

**Description:** Analyzes sentiment of provided text using FinBERT AI model through Gradio API. Returns sentiment classification and confidence scores.

**Request Body:**
```json
{
  "text": "The company announced record profit margins this quarter"
}
```

**Response:**
```json
{
  "sentiment": "Positive",
  "confidence_positive": 0.94,
  "confidence_negative": 0.03,
  "confidence_neutral": 0.03
}
```

**Error Responses:**
- `400 Bad Request` - If 'text' field is missing from request body
- `500 Internal Server Error` - If gradio_client is not installed or API fails

**Example cURL:**
```bash
curl -X POST http://localhost:5000/api/news/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Strong quarterly earnings expected"}'
```

---

## Authentication

Currently, the API does **not** require authentication. All endpoints are publicly accessible.

---

## Error Handling

All endpoints follow standard HTTP error codes:

| Code | Description          |
|------|----------------------|
| 200  | Success              |
| 400  | Bad Request          |
| 500  | Internal Server Error|

Error responses return JSON in the format:
```json
{
  "error": "Error description message"
}
```

---

## CORS Configuration

The API has CORS (Cross-Origin Resource Sharing) enabled, allowing requests from frontend applications running on different origins.

---

## Environment Variables

The following environment variables should be set in `.env` file:

| Variable         | Description                              | Required |
|------------------|------------------------------------------|----------|
| GOOGLE_SHEETS_URL| URL for Google Sheets API integration    | Optional |
| NEWS_API_KEY     | API key for NewsAPI (if using news API)  | Optional |
| PORT             | Port number for the server (default: 5000)| Optional |

---

## Data Sources

1. **Yahoo Finance (yfinance)** - Stock prices, historical data, company info
2. **NSE Python (nsepython)** - Nifty 50 index data from National Stock Exchange
3. **FinBERT Model** - Sentiment analysis via Gradio API (Sabarna6/FinBERT_FinancialSentimentAnalysis)
4. **News API** - News articles (optional, configured via NEWS_API_KEY)
5. **Google Sheets** - Company lookup (optional, configured via GOOGLE_SHEETS_URL)

---

## Rate Limiting

No rate limiting is currently implemented. Please use the API responsibly.

---

## Examples

### Example 1: Get company info and analyze sentiment

```bash
# Get company info
curl "http://localhost:5000/api/company/info?symbol=INFY"

# Analyze news sentiment for the company
curl "http://localhost:5000/api/news/analyze-full?symbol=INFY"
```

### Example 2: Get historical data and financials

```bash
# Get 30 days of historical data
curl "http://localhost:5000/api/company/history?symbol=RELIANCE&start=2024-01-01&end=2024-01-31"

# Get financial metrics
curl "http://localhost:5000/api/company/financials?symbol=RELIANCE"
```

### Example 3: Analyze custom text sentiment

```bash
curl -X POST http://localhost:5000/api/news/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The company is expected to announce record revenues next quarter"
  }'
```

---

## Dependencies

- **Flask** - Web framework
- **Flask-CORS** - Cross-origin requests support
- **yfinance** - Yahoo Finance data
- **nsepython** - NSE India data
- **pandas** - Data processing
- **requests** - HTTP requests
- **gradio_client** - FinBERT sentiment analysis
- **python-dotenv** - Environment variable management

---

## Notes

- Stock symbols are for NSE (India stock exchange). The API automatically adds ".NS" suffix if not provided.
- Sentiment analysis uses FinBERT, a BERT model trained specifically for financial text.
- The `/api/news/analyze-full` endpoint combines news fetching with sentiment analysis for comprehensive analysis.
- All date formats should be in **YYYY-MM-DD** format.

---

## Version
API Version: 1.0
Last Updated: February 2026
