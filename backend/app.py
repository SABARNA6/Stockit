from flask import Flask, jsonify, request
from flask_cors import CORS
import functions

# For Knowivate News API
import requests

# For FinBERT Sentiment Analysis
import asyncio
import sys
import importlib
import types

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
def analyze_full_news():
    """
    Get news for a symbol and analyze with FinBERT.
    Query Params: symbol
    Example: /api/news/analyze-full?symbol=TCS
    """
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Symbol parameter is required"}), 400
    
    try:
        news_data = functions.get_news_data(symbol)
        
        if not news_data:
            return jsonify({"error": "No news found for this symbol"}), 200
        # news_data = functions.get_company_news(symbol)  # symbol OR company name
        headlines = []
        for item in news_data:
            # Direct title
            title = item.get('title')
            
            # Or nested under 'content'
            if not title and 'content' in item:
                title = item['content'].get('title')
            
            if title:
                headlines.append(title)

        if not headlines:
            return jsonify({"error": "No headlines found"}), 404

        analyzed = functions.analyze_headlines_with_finbert(headlines)
        
        return jsonify({
            "symbol": symbol,
            "news": news_data,
            "analysis": analyzed
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)
