# Stockit MVP - Frontend & Backend Integration Guide

## Overview
The Stockit MVP is a stock analysis application with:
- **Frontend**: Interactive HTML dashboard with price analysis, news sentiment analysis, financial parsing, and trading strategy generation
- **Backend**: Flask API server with NSE/equity data integration and FinBERT sentiment analysis

## Project Structure
```
Stockit/
├── frontend/
│   ├── index.html          # Main dashboard interface
│   ├── Stockit_MVP.html    # Backup copy
│   └── server.py           # Local HTTP server
├── backend/
│   ├── app.py              # Flask API server
│   ├── functions.py        # Core analysis functions
│   ├── requirements.txt    # Python dependencies
│   └── __pycache__/        # Compiled Python files
```

## Setup Instructions

### 1. Install Dependencies

#### Backend
```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Setup (Optional)
Create a `.env` file in the `backend` directory for API keys:
```
NEWS_API_KEY=your_newsapi_key_here
```

### 3. Start the Services

#### Option A: Terminal Approach (Recommended)

**Terminal 1 - Start Backend Server:**
```bash
cd backend
python app.py
```
The backend will run on `http://localhost:5000`

**Terminal 2 - Start Frontend Server:**
```bash
cd frontend
python server.py
```
The frontend will open on `http://localhost:8000`

#### Option B: Direct Browser Access
If you have a web server running, simply navigate to:
```
http://localhost:8000/index.html
```

## API Endpoints Available

### Company Data
- `GET /api/nifty50` - Get Nifty 50 companies list
- `GET /api/company/info?symbol=TCS` - Get company information
- `GET /api/company/history?symbol=RELIANCE&start=2026-01-01&end=2026-02-01` - Get historical OHLCV data
- `GET /api/company/financials?symbol=INFY` - Get financial metrics

### News & Sentiment Analysis
- `GET /api/news/analyze-full?symbol=TCS` - Get news and FinBERT sentiment analysis
- `POST /api/news/analyze` - Analyze news sentiment (JSON: `{"text": "..."}`)

## Frontend Features

### 1. Price Data Analysis
- **Input**: Stock symbol (e.g., TCS, RELIANCE) or CSV price data
- **Output**: 
  - Price trend (uptrend/downtrend/sideways)
  - Period returns, average volume, volatility
  - Interactive price charts with volume analysis
  - Candlestick patterns

### 2. News Sentiment Analysis
- **Input**: Stock symbol or news headlines
- **Output**:
  - Overall sentiment (positive/negative/neutral)
  - Sentiment breakdown with confidence scores
  - Keyword extraction
  - Headlines analysis with sentiment labels

### 3. Financial Data Parsing
- **Input**: Financial metrics in text format
- **Output**: Organized financial table with metrics and values

### 4. Trading Strategy Generator
- **Input**: Price trend + News sentiment
- **Output**:
  - Market outlook probability (bullish/bearish/consolidation)
  - Short-term trader strategies
  - Swing trader recommendations
  - Long-term investor guidance
  - Key insights and alerts

## Usage Examples

### Example 1: Analyze a Stock by Symbol
1. Open the frontend (http://localhost:8000)
2. Enter `TCS` in the Price Data input
3. Click "Analyze Price Data"
4. Enter `TCS` in the News input
5. Click "Analyze Sentiment"
6. Click "Generate Strategy" to see recommendations

### Example 2: Paste Custom Data
1. Copy OHLCV data (Date, Open, Close, High, Low, Volume)
2. Paste into Price Data field
3. Click "Analyze Price Data"

## Troubleshooting

### Backend not connecting
- Ensure Flask is running on port 5000
- Check firewall settings
- Verify all dependencies are installed

### No news data found
- Check if the stock symbol is valid (NSE symbol format)
- Try adding `.NS` suffix (e.g., TCS.NS)

### FinBERT not working
- Ensure `gradio_client` is installed
- Check internet connection (Gradio API requires external connection)

### CORS errors
- CORS is enabled in Flask (`flask-cors` installed)
- If issues persist, check browser console for specific errors

## Technical Details

### Frontend Technologies
- HTML5
- Vanilla JavaScript (no dependencies)
- CSS3 with variables and gradients
- Responsive design
- Dark theme with accent colors

### Backend Technologies
- Python Flask
- yfinance for stock data
- nsepython for NSE integration
- FinBERT (Gradio API) for sentiment analysis
- NewsAPI integration
- CORS enabled for cross-origin requests

### Data Flow
```
User Input
    ↓
Frontend (JavaScript)
    ↓
Backend API (Flask)
    ↓
Data Sources (yfinance, NSE, NewsAPI, FinBERT)
    ↓
Processed Results
    ↓
Frontend Display (Charts, Tables, Analysis)
```

## Future Enhancements
- Real-time data streaming
- Advanced technical indicators
- Portfolio backtesting
- Machine learning price predictions
- User authentication and saved analyses
- Mobile responsive optimization
- Export to PDF/CSV

## Support
For issues or questions, check the error console (F12 in browser) and backend terminal output for detailed error messages.
