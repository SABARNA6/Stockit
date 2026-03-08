from nsepython import nsefetch
import pandas as pd
import yfinance as yf
import requests
import os
from gradio_client import Client
from dotenv import load_dotenv
load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
def get_nifty50_details():
    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
        json_data = nsefetch(url)
        
        if not json_data or 'data' not in json_data:
            print("Failed to fetch data")
            return []

        companies_list = []
        
        # The 'data' key contains the list of stocks.
        for item in json_data['data']:
            # Skip the index summary row if present
            if item['symbol'] == "NIFTY 50":
                continue
                
            # Extract details
            symbol = item.get('symbol')
            # Company name usually in 'meta' -> 'companyName'
            company_name = item.get('meta', {}).get('companyName') 
            # Industry/Speciality usually in 'meta' -> 'industry'
            speciality = item.get('meta', {}).get('industry')

            companies_list.append({
                "Symbol": symbol,
                "Company Name": company_name,
                "Speciality": speciality
            })
            
        return companies_list

    except Exception as e:
        print(f"Error fetching data: {e}")
        return []
    
def get_symbol_info(symbol):
    try:
        # Add .NS suffix for NSE stocks if not present
        ticker_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        return info

    except Exception as e:
        print(f"Error fetching info for {symbol}: {e}")
        return {}

def get_stock_history_ochlv(symbol, startDate, endDate):
    try:
        # Add .NS suffix for NSE stocks if not present
        ticker_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        
        ticker = yf.Ticker(ticker_symbol)
        
        # Download history
        history = ticker.history(start=startDate, end=endDate)
        
        if history.empty:
            print(f"No data found for {symbol} between {startDate} and {endDate}")
            return []

        # Reset index to make Date a column and converting to dictionary records
        history.reset_index(inplace=True)
        
        # Format Date to string immediately
        history['Date'] = history['Date'].dt.strftime('%Y-%m-%d')
        
        # Convert to list of dictionaries
        data_list = history[['Date', 'Open', 'Close', 'High', 'Low', 'Volume']].to_dict('records')
        
        return data_list

    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        return []
def get_finacial_metric(symbol):
    try:
        # Add .NS suffix for NSE stocks if not present
        ticker_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # Extract comprehensive financial metrics
        revenue = info.get('totalRevenue')
        net_profit = info.get('netIncomeToCommon')
        ebitda = info.get('ebitda')
        market_cap = info.get('marketCap')
        pe_ratio = info.get('trailingPE')
        pb_ratio = info.get('priceToBook')
        debt_to_equity = info.get('debtToEquity')
        roe = info.get('returnOnEquity')
        eps = info.get('trailingEps')
        dividend_yield = info.get('dividendYield')
        
        # Calculate additional metrics
        ebitda_margin = None
        if ebitda and revenue:
            ebitda_margin = (ebitda / revenue) * 100
            
        profit_margin = None
        if net_profit and revenue:
            profit_margin = (net_profit / revenue) * 100
        
        # Structure data as expected by frontend
        return {
            "profitability": {
                "revenue": revenue,
                "net_profit": net_profit,
                "ebitda": ebitda,
                "ebitda_margin": ebitda_margin,
                "profit_margin": profit_margin,
                "roe": roe,
                "eps": eps
            },
            "valuation": {
                "market_cap": market_cap,
                "pe_ratio": pe_ratio,
                "pb_ratio": pb_ratio,
                "dividend_yield": dividend_yield
            },
            "growth": {
                "revenue_growth": info.get('revenueGrowth'),
                "earnings_growth": info.get('earningsGrowth')
            },
            "financialHealth": {
                "debt_to_equity": debt_to_equity,
                "current_ratio": info.get('currentRatio'),
                "quick_ratio": info.get('quickRatio')
            }
        }

    except Exception as e:
        print(f"Error fetching financial metrics for {symbol}: {e}")
        return {}
    
def get_company_news(company_name):
    """
    Fetch news from NewsAPI using company name
    """

    try:
        url = "https://newsapi.org/v2/everything"

        params = {
            "q": company_name,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 5,
            "apiKey": NEWS_API_KEY
        }

        response = requests.get(url, params=params)

        print("Status Code:", response.status_code)
        print("Response:", response.text)  # 🔥 Debug

        data = response.json()

        if data.get("status") != "ok":
            print("NewsAPI error:", data)
            return []

        return data.get("articles", [])

    except Exception as e:
        print(f"Error fetching news: {e}")
        return []
def analyze_headlines_with_finbert(headlines):
    """
    Analyze list of headlines using FinBERT
    """

    try:
        client = Client("Sabarna6/FinBERT_FinancialSentimentAnalysis")

        sentiment_count = {"Positive": 0, "Negative": 0, "Neutral": 0}
        analyzed = []

        for headline in headlines:
            result = client.predict(
                text=headline,
                api_name="/predict"
            )

            # HF returns: [scores_dict, sentiment_string]
            scores = result[0]
            label = result[1]

            if label in sentiment_count:
                sentiment_count[label] += 1

            analyzed.append({
                "headline": headline,
                "sentiment": label,
                "confidence": scores.get(label)
            })

        overall = max(sentiment_count, key=sentiment_count.get)

        return {
            "summary": sentiment_count,
            "overall_sentiment": overall,
            "details": analyzed
        }

    except Exception as e:
        print(f"Error analyzing headlines: {e}")
        return {}

def get_news_data(symbol):
    try:
        # Add .NS suffix for NSE stocks if not present
        ticker_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        
        ticker = yf.Ticker(ticker_symbol)
        news = ticker.news
        
        return news

    except Exception as e:
        print(f"Error fetching news for {symbol}: {e}")
        return []
    
if __name__ == "__main__":
    # print("Fetching Nifty 50 Companies...")
    # companies = get_symbol_info("LT")
    
    # # Extract specific details
    # details = {
    #     "Company Name": companies.get('longName'),
    #     "Symbol": companies.get('symbol'),
    #     "Price": companies.get('currentPrice'),
    #     "Short Summary": companies.get('longBusinessSummary')
    # }
    # print(details)

    print("\nFetching Stock History for RELIANCE...")
    # Sample data for history
    history_data = get_stock_history_ochlv("RELIANCE", "2023-01-01", "2023-01-10")
    print(f"Retrieved {len(history_data)} records.")
    if history_data:
        print("First record:", history_data[0])
        
    print("\nFetching News for TCS...")
    news_data = get_news_data("TCS")
    print(f"Retrieved {len(news_data)} news items.")
    if news_data:
        # Print title of the first news item
        print("First news title:", news_data)