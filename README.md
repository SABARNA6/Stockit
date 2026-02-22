# Stockit - AI-Powered Stock Analysis Platform

A comprehensive stock analysis platform powered by real-time data, AI-driven sentiment analysis, and intelligent trading strategies. Built with a modern frontend and scalable Flask backend.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)
- [Usage Guide](#usage-guide)
- [Docker Deployment](#docker-deployment)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

**Stockit** is an intelligent stock analysis platform that combines:
- **Real-time Stock Data**: Integration with NSE India (National Stock Exchange) and Yahoo Finance
- **AI Sentiment Analysis**: FinBERT-powered analysis of financial news for sentiment detection
- **Smart Trading Strategies**: Automated generation of short-term, swing, and long-term trading suggestions
- **Interactive Dashboard**: Modern, responsive UI for comprehensive stock analysis
- **Technical Analysis**: Price charts, volume analysis, and historical data visualization

Perfect for investors, traders, and financial analysts who want data-driven insights at their fingertips.

---

## ✨ Features

### Frontend (Client)
- 🔍 **Real-time Stock Search**: Instant search across Nifty 50 companies
- 📊 **Interactive Price Charts**: Line and candlestick charts with multiple timeframes (1M, 3M, 6M, 1Y)
- 📰 **News & Sentiment Analysis**: Real-time news feed with AI-powered sentiment scoring
- 💹 **Financial Metrics**: Comprehensive display of Revenue, Net Profit, EBITDA, and more
- 📈 **Trading Strategies**: AI-generated trading recommendations based on technical and sentiment analysis
- 📊 **Volume Analysis**: Identify volume spikes and trading patterns
- 🎨 **Modern UI**: Clean, professional design inspired by Screener.in

### Backend (Server)
- 🏦 **Multi-Source Data Integration**: NSE, Yahoo Finance, and custom Google Sheets data
- 🤖 **FinBERT Sentiment Analysis**: State-of-the-art NLP for financial news classification
- 📈 **Historical Data**: Complete OCHLV (Open, Close, High, Low, Volume) data
- 🔐 **CORS Support**: Secure cross-origin requests
- 📡 **RESTful API**: Well-documented endpoints for all data needs
- ⚡ **Caching & Optimization**: Efficient data fetching and processing

---

## 🛠 Tech Stack

### Frontend
- **HTML5** - Semantic markup
- **CSS3** - Responsive design with modern features
- **JavaScript (ES6+)** - Modular, component-based architecture
- **Chart.js** - Interactive data visualization
- **Fetch API** - Modern HTTP client

### Backend
- **Python 3.10** - Core programming language
- **Flask** - Lightweight web framework
- **Flask-CORS** - Cross-origin request handling
- **yfinance** - Yahoo Finance data integration
- **nsepython** - NSE India API client
- **pandas** - Data manipulation and analysis
- **requests** - HTTP client for API calls
- **gradio_client** - FinBERT sentiment analysis client
- **python-dotenv** - Environment variable management

### AI/ML
- **FinBERT** - Hugging Face's financial BERT model for sentiment analysis
- **Gradio** - Model serving and API wrapper

### DevOps
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

---

## 📁 Project Structure

```
Stockit/
├── README.md                           # This file
├── docker-compose.yml                  # Docker compose configuration
├── Dockerfile                          # Root Dockerfile for unified build
│
├── client/                             # Frontend application
│   ├── index.html                      # Main dashboard UI
│   ├── README.md                       # Frontend documentation
│   ├── Dockerfile                      # Frontend container setup
│   ├── css/
│   │   └── style.css                   # Styling and responsive design
│   ├── js/
│   │   ├── app.js                      # Application logic (479 lines)
│   │   └── api.js                      # API client (71 lines)
│   └── assets/                         # Static images/icons
│
├── backend/                            # Flask API server
│   ├── app.py                          # Main Flask application (318 lines)
│   ├── functions.py                    # Core analysis functions (230 lines)
│   ├── requirements.txt                # Python dependencies
│   ├── Dockerfile                      # Backend container setup
│   ├── .env                            # Environment variables (git-ignored)
│   └── __pycache__/                    # Python cache
│
├── FinBERT_FinancialSentimentAnalysis/ # Sentiment analysis module
│   ├── app.py                          # Gradio app for FinBERT
│   ├── README.md                       # FinBERT documentation
│   └── requirements.txt                # FinBERT dependencies
│
├── MVP/                                # Prototype versions
│   └── Stockit_MVP.html                # Original MVP interface
│
└── frontend/                           # Alternative frontend folder (deprecated)
    └── [legacy files]
```

### Key Files Description

| File | Purpose |
|------|---------|
| `backend/app.py` | Flask server with 10+ API endpoints |
| `backend/functions.py` | Core functions for data fetching & analysis |
| `client/js/app.js` | Main application logic & UI rendering |
| `client/js/api.js` | API wrapper with error handling |
| `client/index.html` | Responsive HTML dashboard |
| `docker-compose.yml` | Orchestrates backend & frontend services |

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js (optional, for frontend serving)
- Docker & Docker Compose (for containerized deployment)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Option 1: Local Setup (Development)

#### Step 1: Clone & Navigate
```bash
cd "My BACKUP/Consultancy Project/Stockit"
```

#### Step 2: Install Backend Dependencies
```bash
cd backend
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 3: Setup Environment Variables
Create `.env` file in `backend/` directory:
```env
NEWS_API_KEY=your_newsapi_key_here
GOOGLE_SHEETS_URL=your_google_sheets_api_url
```

#### Step 4: Start Backend Server
```bash
cd backend
python app.py
```
Backend will run on: `http://localhost:5000`

#### Step 5: Serve Frontend
```bash
# In a new terminal
cd client
# Using Python 3:
python -m http.server 8000
```
Frontend will be available at: `http://localhost:8000`

---

### Option 2: Docker Deployment (Production)

#### Using Docker Compose (Recommended)
```bash
# Build and start all services
docker-compose up --build

# Frontend:  http://localhost:10000
# Backend:   http://localhost:5000
```

#### Using Dockerfile (Unified)
```bash
# Build the image
docker build -t stockit:latest .

# Run the container
docker run -p 10000:10000 -e FLASK_ENV=production stockit:latest
```

#### Environment Variables for Docker
Create `.env` file in project root:
```env
FLASK_ENV=production
GOOGLE_SHEETS_URL=your_google_sheets_api_url
NEWS_API_KEY=your_newsapi_key_here
```

---

## 📡 API Endpoints

### Base URL
```
http://localhost:5000/api
```

### Endpoints

#### 1. **Nifty 50 Companies**
```http
GET /api/nifty50
```
**Description**: Get list of all Nifty 50 companies  
**Response**: 
```json
[
    {
        "Symbol": "ADANIPORTS",
        "Company Name": "Adani Ports and Special Economic Zone",
        "Speciality": "Ports & Logistics"
    }
]
```

#### 2. **Company Information**
```http
GET /api/company/info?symbol=TCS
```
**Description**: Get company details and current price  
**Parameters**: 
- `symbol` (required): Stock ticker (e.g., TCS, RELIANCE, INFY)

**Response**:
```json
{
    "Company Name": "Tata Consultancy Services Limited",
    "Symbol": "TCS.NS",
    "Price": 4085.55,
    "Short Summary": "TCS is a leading global IT services & consulting..."
}
```

#### 3. **Stock History (OCHLV)**
```http
GET /api/company/history?symbol=RELIANCE&start=2024-01-01&end=2024-12-31
```
**Description**: Get historical stock data  
**Parameters**:
- `symbol` (required): Stock ticker
- `start` (required): Start date (YYYY-MM-DD)
- `end` (required): End date (YYYY-MM-DD)

**Response**:
```json
[
    {
        "Date": "2024-01-01",
        "Open": 2885.50,
        "Close": 2910.25,
        "High": 2920.00,
        "Low": 2880.00,
        "Volume": 15432100
    }
]
```

#### 4. **Financial Metrics**
```http
GET /api/company/financials?symbol=INFY
```
**Description**: Get financial metrics (Revenue, Net Profit, EBITDA, etc.)  
**Parameters**:
- `symbol` (required): Stock ticker

**Response**:
```json
{
    "Revenue": 21156000000,
    "Net Profit": 4156000000,
    "EBITDA Margin": 21.5,
    "P/E Ratio": 18.5,
    "Market Cap": 650000000000
}
```

#### 5. **Company Search (with News & Sentiment)**
```http
GET /api/company/search?symbol=RELIANCE
```
**Description**: Search company and get news with AI sentiment analysis  
**Parameters**:
- `symbol` (required): Stock ticker

**Response**:
```json
{
    "data": [
        {
            "title": "Reliance Industries Announces Q4 Results",
            "sentiment": "Positive",
            "confidence": 0.87,
            "pubdate": "2024-01-15T10:30:00Z",
            "summary": "Strong Q4 performance with 15% YoY growth...",
            "symbol": "RELIANCE"
        }
    ]
}
```

#### 6. **Sentiment Analysis (Full News Analysis)**
```http
GET /api/news/analyze-full?symbol=TCS
```
**Description**: Comprehensive news sentiment analysis using FinBERT  
**Parameters**:
- `symbol` (required): Stock ticker

**Response**: Same as Company Search endpoint

---

## 🔐 Environment Variables

### Backend Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEWS_API_KEY` | API key for news source | `abc123xyz` |
| `GOOGLE_SHEETS_URL` | Google Sheets query endpoint | `https://script.google.com/macros/...` |
| `FLASK_ENV` | Environment mode | `production` or `development` |
| `PORT` | Port number (default: 5000) | `5000` |

### Setting Environment Variables

#### Local (.env file)
```bash
# backend/.env
NEWS_API_KEY=your_api_key
GOOGLE_SHEETS_URL=your_sheets_url
```

#### Docker (docker-compose.yml)
```yaml
environment:
  - FLASK_ENV=production
  - NEWS_API_KEY=${NEWS_API_KEY}
  - GOOGLE_SHEETS_URL=${GOOGLE_SHEETS_URL}
```

---

## 💡 Usage Guide

### For End Users

1. **Search for a Stock**
   - Enter company name or ticker in search box
   - Select from Nifty 50 suggestions

2. **View Analytics**
   - Check real-time price and key metrics
   - View company overview and financials
   - Analyze multi-timeframe price charts

3. **Read Sentiment**
   - Look at overall sentiment (Positive/Neutral/Negative)
   - Check individual news articles with confidence scores
   - Make informed trading decisions

4. **Follow Trading Strategies**
   - Review AI-generated short-term strategies
   - Check swing trading recommendations
   - Evaluate long-term investment outlook

### For Developers

#### Adding New Data Sources
1. Create function in `backend/functions.py`
2. Add Flask route in `backend/app.py`
3. Call from frontend `client/js/api.js`
4. Render in `client/js/app.js`

#### Customizing Frontend
- Styling: Edit `client/css/style.css`
- Logic: Modify `client/js/app.js`
- API calls: Update `client/js/api.js`

#### Debugging
- Backend logs: Check terminal output when running `python app.py`
- Frontend logs: Open browser DevTools (F12 → Console)
- API responses: Use browser Network tab to inspect requests/responses

---

## 🐳 Docker Deployment

### Prerequisites
- Docker installed and running
- Docker Compose (comes with Docker Desktop)

### Deploy with Docker Compose

```bash
# Build images
docker-compose build

# Start services
docker-compose up

# In background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Docker Compose Services

| Service | Port | Purpose |
|---------|------|---------|
| `backend` | 5000 | Flask API server |
| `frontend` | 10000 | Frontend web interface |

### Custom Docker Build

```dockerfile
# Build
docker build -t stockit:latest .

# Run
docker run -p 10000:10000 \
  -e FLASK_ENV=production \
  -e GOOGLE_SHEETS_URL="your_url" \
  stockit:latest
```

---

## 🐛 Troubleshooting

### Frontend Issues

**Issue**: "Cannot read properties of undefined"
- **Solution**: Ensure backend is running on http://localhost:5000
- **Check**: Browser Console (F12) for detailed error messages

**Issue**: Charts not displaying
- **Solution**: Verify `chart.js` is loaded in index.html
- **Check**: Network tab for failed resource loads

**Issue**: News showing "No title"
- **Solution**: API response might have spaced keys (e.g., `"title "`)
- **Check**: Browser Network tab → inspect API response

### Backend Issues

**Issue**: "ModuleNotFoundError"
- **Solution**: Install dependencies: `pip install -r requirements.txt`
- **Verify**: `pip list | grep -E "flask|yfinance|pandas"`

**Issue**: Port 5000 already in use
- **Solution**: 
  ```bash
  # Kill process on port 5000
  lsof -ti:5000 | xargs kill -9  # macOS/Linux
  netstat -ano | findstr :5000   # Windows (then taskkill)
  ```

**Issue**: FinBERT sentiment returns "Neutral" for all
- **Solution**: Verify Gradio client is installed: `pip install gradio_client`

### API Issues

**Issue**: 404 errors for `/api/*` endpoints
- **Solution**: Verify `static_folder='../client'` in app.py
- **Check**: Backend is serving frontend files correctly

**Issue**: CORS errors
- **Solution**: Flask-CORS is properly configured
- **Check**: `CORS(app)` is called in app.py

---

## 📚 Additional Resources

### Documentation Files
- Frontend Details: See `client/README.md`
- FinBERT Setup: See `FinBERT_FinancialSentimentAnalysis/README.md`

### External APIs & Libraries
- [NSEPython Documentation](https://github.com/NSEPython/NSEPython)
- [yfinance Documentation](https://yfinance.readthedocs.io/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [FinBERT Model](https://huggingface.co/ProsusAI/finbert)
- [Chart.js Documentation](https://www.chartjs.org/)

### Useful Commands

```bash
# Backend
cd backend && python app.py              # Start backend
pip install -r requirements.txt          # Install dependencies
python -m pip freeze > requirements.txt  # Update requirements

# Frontend
cd client && python -m http.server 8000  # Serve frontend
npm install                              # If using npm

# Docker
docker-compose up --build                # Build and start
docker-compose ps                        # View running services
docker logs stockit_backend_1            # View backend logs
docker-compose down                      # Stop all services

# Development
python -m pytest backend/tests/          # Run tests (if available)
python app.py --debug                    # Run in debug mode
```

---

## 🔮 Future Enhancements

- [ ] User authentication & portfolios
- [ ] Watchlist functionality
- [ ] Advanced technical indicators (RSI, MACD, Bollinger Bands)
- [ ] Real-time stock alerts
- [ ] Export to PDF/Excel reports
- [ ] Mobile app (React Native/Flutter)
- [ ] Multi-market support (BSE, international exchanges)
- [ ] Machine learning price predictions
- [ ] Backtesting engine for strategies
- [ ] Social sentiment analysis (Twitter, Reddit)

---

## 📄 License

This project is provided as-is for educational and commercial use.

---

## 👥 Support

For issues, questions, or contributions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review API endpoint documentation
3. Check browser console for detailed errors
4. Verify all dependencies are installed

---

**Built with ❤️ for investors and traders.**  
*Last Updated: February 2026*
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
