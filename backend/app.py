from flask import Flask, jsonify, request
from flask_cors import CORS
import functions

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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

@app.route('/api/company/news', methods=['GET'])
def news():
    """
    Get news for a symbol.
    Query Params: symbol
    Example: /api/company/news?symbol=TATAMOTORS
    """
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Symbol parameter is required"}), 400

    data = functions.get_news_data(symbol)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)