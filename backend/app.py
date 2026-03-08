from flask import Flask, jsonify, request
from flask_cors import CORS
import functions
import os
import pandas as pd

import yfinance

# For Knowivate News API
import requests

# For FinBERT Sentiment Analysis
import asyncio
import sys
import importlib
import types

# Google Sheets API URL
GOOGLE_SHEETS_URL = os.environ.get('GOOGLE_SHEETS_URL', '')

gradio_client = None
if sys.version_info >= (3, 8):
    try:
        gradio_client = importlib.import_module('gradio_client')
    except ImportError:
        pass

app = Flask(__name__, static_folder='../client', static_url_path='')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/nifty50', methods=['GET'])
def nifty50():
    """Get list of Nifty 50 companies."""
    data = functions.get_nifty50_details()
    return jsonify(data)
@app.route('/api/test', methods=['GET'])
def news():
    symbol = request.args.get('symbol')
    return jsonify(yfinance.ticker.Ticker(symbol).news)

@app.route('/api/company/info', methods=['GET'])
def company_info():
    """
    Get company info.
    Query Params: symbol
    Example: /api/company/info?symbol=TCS
    """
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Symbol parameter is required"}), 400
    
    info = functions.get_symbol_info(symbol)
    
    # Filter for the specific details you requested earlier
    simple_details = {
        "Company Name": info.get('longName'),
        "Symbol": info.get('symbol'),
        "Price": info.get('currentPrice'),
        "Short Summary": info.get('longBusinessSummary')
    }
    
    return jsonify(simple_details)

@app.route('/api/company/history', methods=['GET'])
def stock_history():
    """
    Get historical OCHLV data.
    Query Params: symbol, start, end
    Example: /api/company/history?symbol=RELIANCE&start=2023-01-01&end=2023-01-10
    """
    symbol = request.args.get('symbol')
    start_date = request.args.get('start')
    end_date = request.args.get('end')

    if not symbol or not start_date or not end_date:
        return jsonify({"error": "Symbol, start, and end parameters are required"}), 400

    data = functions.get_stock_history_ochlv(symbol, start_date, end_date)
    return jsonify(data)

@app.route('/api/company/financials', methods=['GET'])
def financials():
    """
    Get financial metrics.
    Query Params: symbol
    Example: /api/company/financials?symbol=INFY
    """
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Symbol parameter is required"}), 400

    data = functions.get_finacial_metric(symbol)
    return jsonify(data)

@app.route('/api/company/search', methods=['GET'])
def search_company():
    """
    Search company - returns basic company info for the symbol.
    Query Params: symbol
    Example: /api/company/search?symbol=TCS
    """
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Symbol parameter is required"}), 400
    
    print(f"[search_company] Searching for symbol: {symbol}")
    
    try:
        # Get basic company info
        info = functions.get_symbol_info(symbol)
        if not info:
            return jsonify({"data": []}), 200
        
        # Return in expected format
        result = {
            "data": [{
                "symbol": symbol,
                "name": info.get('longName', symbol),
                "exchange": info.get('exchange', 'NSE'),
                "type": "EQUITY"
            }]
        }
        return jsonify(result)
    except Exception as e:
        print(f"[search_company] Error: {e}")
        return jsonify({"data": []}), 200

# @app.route('/api/company/news', methods=['GET'])
# def news():
#     """
#     Get news for a symbol.
#     Query Params: symbol
#     Example: /api/company/news?symbol=TATAMOTORS
#     """
#     symbol = request.args.get('symbol')
#     if not symbol:
#         return jsonify({"error": "Symbol parameter is required"}), 400

#     data = functions.get_news_data(symbol)
#     return jsonify(data)


# --- New Endpoints ---

# @app.route('/api/news/knowivate', methods=['GET'])
# def get_knowivate_news():
#     """
#     Get news from Knowivate API.
#     Query Params: query (optional)
#     Example: /api/news/knowivate?query=stock market
#     """
#     query = request.args.get('query', '')
#     url = f"https://developers.knowivate.com/news/get-news?query={query}"
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
#         return jsonify(response.json())
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


@app.route('/api/news/analyze-full', methods=['GET'])
def analyze_full_news(symbol=None):
    # Get symbol from parameter if not provided (for direct calls), otherwise from request args
    if not symbol:
        symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Symbol parameter is required"}), 400

    print(f"[analyze_full_news] Starting analysis for symbol: {symbol}")
    
    try:
        news_data = functions.get_news_data(symbol)
        print(f"[analyze_full_news] Retrieved {len(news_data) if news_data else 0} news items")

        if not news_data:
            print(f"[analyze_full_news] No news found for {symbol}")
            # Return empty data instead of error  
            return jsonify({"data": []}), 200

        # Extract headlines
        headlines = []
        for item in news_data:
            title = item.get('content', {}).get('title')
            if title:
                headlines.append(title)

        if not headlines:
            print(f"[analyze_full_news] No headlines extracted from news data")
            # Return empty data instead of 404
            return jsonify({"data": []}), 200

        print(f"[analyze_full_news] Extracted {len(headlines)} headlines, analyzing sentiment...")
        analyzed = functions.analyze_headlines_with_finbert(headlines)
        print(f"[analyze_full_news] Sentiment analysis completed")

        # ✅ Build required output format
        # Helper function to safely get value from dict with potential spaces in keys
        def safe_get(d, *possible_keys):
            if not d:
                return None
            # Try exact keys first
            for key in possible_keys:
                if key in d:
                    return d[key]
            # Try keys with trailing space
            for key in possible_keys:
                spaced_key = key.strip() + " "
                if spaced_key in d:
                    return d[spaced_key]
            return None
        
        formatted_data = []

        for idx, (news_item, analysis_item) in enumerate(zip(news_data, analyzed["details"])):
            content = news_item.get("content", {})
            
            # Debug: print source data structure
            if idx == 0:
                print(f"[analyze_full_news] Sample content keys: {list(content.keys())}")
                print(f"[analyze_full_news] Sample analysis_item keys: {list(analysis_item.keys())}")
            
            # Ensure sentiment is always a proper string value
            # Try to get sentiment from analysis_item with or without spaces
            sentiment = safe_get(analysis_item, "sentiment") or "Neutral"
            
            # Clean sentiment
            sentiment = str(sentiment).strip()
            if not sentiment:
                sentiment = "Neutral"
            # Capitalize sentiment properly
            sentiment = sentiment.capitalize()
            
            # Ensure confidence is a float between 0 and 1
            confidence = safe_get(analysis_item, "confidence") or 0
            if confidence is None:
                confidence = 0
            else:
                try:
                    confidence = float(confidence)
                    if confidence > 1:
                        confidence = confidence / 100
                except (ValueError, TypeError):
                    confidence = 0
            
            # Extract title, summary, pubdate with fallback for spaced keys
            title = safe_get(content, "title", "title ") or "No title"
            summary = safe_get(content, "summary", "summary ") or ""
            pubdate = safe_get(content, "pubDate", "pubdate", "pubdate ") or ""
            
            # Ensure title is string
            title = str(title).strip() if title else "No title"
            summary = str(summary).strip() if summary else ""
            pubdate = str(pubdate).strip() if pubdate else ""

            formatted_data.append({
                "confidence": confidence,
                "pubdate": pubdate,
                "sentiment": sentiment,
                "summary": summary,
                "symbol": symbol,
                "title": title
            })

        result = {
            "data": formatted_data
        }
        print(f"[analyze_full_news] Returning {len(formatted_data)} formatted news items")
        return jsonify(result)

    except Exception as e:
        print(f"[analyze_full_news] Error: {e}")
        import traceback
        traceback.print_exc()
        # Return empty data with error message instead of 500
        return jsonify({"data": [], "error": str(e)}), 200
    

@app.route('/api/news/analyze', methods=['POST'])
def analyze_news_sentiment():
    """
    Analyze news sentiment using FinBERT (Gradio API).
    Request JSON: { "text": "news text here" }
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' in request body"}), 400

    text = data['text']

    # Use Gradio Client (async)
    if gradio_client is None:
        return jsonify({"error": "gradio_client not installed. Please install gradio_client."}), 500

    async def analyze():
        client = await gradio_client.Client.connect("Sabarna6/FinBERT_FinancialSentimentAnalysis")
        result = await client.predict("/predict", {{"text": text}})
        return result.data

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        sentiment = loop.run_until_complete(analyze())
        return jsonify(sentiment)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# NEW ENDPOINTS: /api/stocks/* - Frontend expects these routes
# ============================================================================

@app.route('/api/stocks/<symbol>', methods=['GET'])
def get_stock_overview(symbol):
    """Get stock overview/info."""
    try:
        info = functions.get_symbol_info(symbol)
        return jsonify({"data": info})
    except Exception as e:
        print(f"[get_stock_overview] Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stocks/<symbol>/sparkline', methods=['GET'])
def get_stock_sparkline(symbol):
    """Get sparkline data for mini chart."""
    try:
        points = request.args.get('points', 12, type=int)
        # Add .NS suffix for NSE stocks
        ticker_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        ticker = yfinance.Ticker(ticker_symbol)
        hist = ticker.history(period='3mo')
        if hist.empty:
            return jsonify({"data": []}), 200
        # Return last N points
        data = hist['Close'].tail(points).tolist()
        return jsonify({"data": data})
    except Exception as e:
        print(f"[get_stock_sparkline] Error: {e}")
        return jsonify({"data": []}), 200

@app.route('/api/stocks/<symbol>/chart', methods=['GET'])
def get_stock_chart(symbol):
    """Get chart data for selected timeframe."""
    try:
        timeframe = request.args.get('timeframe', '3M')
        # Map timeframe to period
        period_map = {'1W': '1wk', '1M': '1mo', '3M': '3mo', '6M': '6mo', '1Y': '1y', 'ALL': 'max'}
        period = period_map.get(timeframe, '3mo')
        
        # Add .NS suffix for NSE stocks
        ticker_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        ticker = yfinance.Ticker(ticker_symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return jsonify({"candles": []}), 200
        
        # Convert to frontend expected format
        candles = []
        for date, row in hist.iterrows():
            candles.append({
                'timestamp': int(date.timestamp() * 1000),  # Convert to milliseconds
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close'])
            })
        
        return jsonify({"candles": candles})
    except Exception as e:
        print(f"[get_stock_chart] Error: {e}")
        return jsonify({"candles": []}), 200

@app.route('/api/stocks/<symbol>/volume', methods=['GET'])
def get_stock_volume(symbol):
    """Get volume data."""
    try:
        timeframe = request.args.get('timeframe', '3M')
        period_map = {'1W': '1wk', '1M': '1mo', '3M': '3mo', '6M': '6mo', '1Y': '1y', 'ALL': 'max'}
        period = period_map.get(timeframe, '3mo')
        
        # Add .NS suffix for NSE stocks
        ticker_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        ticker = yfinance.Ticker(ticker_symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return jsonify({"volumes": [], "avgVolume": 0}), 200
        
        # Convert to frontend expected format
        volumes = []
        total_volume = 0
        for date, row in hist.iterrows():
            volume = int(row['Volume'])
            volumes.append({
                'timestamp': int(date.timestamp() * 1000),  # Convert to milliseconds
                'volume': volume
            })
            total_volume += volume
        
        avg_volume = total_volume / len(volumes) if volumes else 0
        
        return jsonify({"volumes": volumes, "avgVolume": int(avg_volume)})
    except Exception as e:
        print(f"[get_stock_volume] Error: {e}")
        return jsonify({"volumes": [], "avgVolume": 0}), 200

@app.route('/api/stocks/<symbol>/trends', methods=['GET'])
def get_stock_trends(symbol):
    """Get trend signals."""
    try:
        # Add .NS suffix for NSE stocks
        ticker_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        ticker = yfinance.Ticker(ticker_symbol)
        hist = ticker.history(period='3mo')
        
        if hist.empty or len(hist) < 2:
            return jsonify({"data": {"trend": "Neutral", "current_price": 0, "ma_20": 0, "ma_50": 0}}), 200
        
        # Simple trend calculation
        current = float(hist['Close'].iloc[-1])
        ma_20 = float(hist['Close'].tail(min(20, len(hist))).mean())
        ma_50 = float(hist['Close'].tail(min(50, len(hist))).mean()) if len(hist) >= 50 else ma_20
        
        trend = "Uptrend" if current > ma_20 > ma_50 else "Downtrend" if current < ma_20 < ma_50 else "Neutral"
        
        data = {
            'trend': trend,
            'current_price': current,
            'ma_20': ma_20,
            'ma_50': ma_50
        }
        return jsonify({"data": data})
    except Exception as e:
        print(f"[get_stock_trends] Error: {e}")
        return jsonify({"data": {"trend": "Neutral", "current_price": 0, "ma_20": 0, "ma_50": 0}}), 200

@app.route('/api/stocks/<symbol>/recommendation', methods=['GET'])
def get_stock_recommendation(symbol):
    """Get investment recommendation."""
    try:
        info = functions.get_symbol_info(symbol)
        # Use recommendationKey if available
        recommendation = info.get('recommendationKey', 'hold')
        
        data = {
            'recommendation': recommendation,
            'target_price': info.get('targetMeanPrice'),
            'number_of_analysts': info.get('numberOfAnalystOpinions')
        }
        return jsonify({"data": data})
    except Exception as e:
        print(f"[get_stock_recommendation] Error: {e}")
        return jsonify({"data": {"recommendation": "hold", "target_price": None, "number_of_analysts": 0}}), 200

@app.route('/api/stocks/<symbol>/fundamentals', methods=['GET'])
def get_stock_fundamentals(symbol):
    """Get fundamental metrics."""
    try:
        data = functions.get_finacial_metric(symbol)
        return jsonify({"data": data})
    except Exception as e:
        print(f"[get_stock_fundamentals] Error: {e}")
        return jsonify({"data": {}}), 200

@app.route('/api/stocks/<symbol>/news', methods=['GET'])
def get_stock_news(symbol):
    """Get news for stock."""
    try:
        # Use the existing analyze_full_news function
        news_data = functions.get_news_data(symbol)
        if not news_data:
            return jsonify({"data": []})
        
        # Extract headlines for sentiment analysis
        headlines = [item.get('content', {}).get('title') for item in news_data if item.get('content', {}).get('title')]
        
        if headlines:
            analyzed = functions.analyze_headlines_with_finbert(headlines)
            formatted_data = []
            for news_item, analysis_item in zip(news_data, analyzed.get("details", [])):
                content = news_item.get("content", {})
                formatted_data.append({
                    "title": content.get("title", ""),
                    "summary": content.get("summary", ""),
                    "pubdate": content.get("pubDate", ""),
                    "sentiment": analysis_item.get("sentiment", "Neutral"),
                    "confidence": analysis_item.get("confidence", 0)
                })
            return jsonify({"data": formatted_data})
        else:
            return jsonify({"data": []})
    except Exception as e:
        print(f"[get_stock_news] Error: {e}")
        return jsonify({"data": []}), 200

@app.route('/api/stocks/<symbol>/historical', methods=['GET'])
def get_stock_historical(symbol):
    """Get historical data with pagination."""
    try:
        period = request.args.get('period', '1mo')
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 8, type=int)
        
        # Add .NS suffix for NSE stocks
        ticker_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        ticker = yfinance.Ticker(ticker_symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return jsonify({
                "prices": [],
                "pagination": {"page": page, "limit": limit, "total": 0}
            }), 200
        
        # Reverse to show newest first
        hist = hist.iloc[::-1]
        
        # Calculate change percentages
        hist['ChangePercent'] = hist['Close'].pct_change() * 100
        
        # Paginate
        start = (page - 1) * limit
        end = start + limit
        paginated = hist.iloc[start:end]
        
        prices = []
        for date, row in paginated.iterrows():
            change_pct = float(row['ChangePercent']) if not pd.isna(row['ChangePercent']) else 0.0
            prices.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']),
                'changePercent': change_pct
            })
        
        return jsonify({
            "prices": prices,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(hist)
            }
        }), 200
    except Exception as e:
        print(f"[get_stock_historical] Error: {e}")
        return jsonify({
            "prices": [],
            "pagination": {"page": page, "limit": limit, "total": 0}
        }), 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)
