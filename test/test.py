import yfinance as yf

ticker = yf.Ticker("POLYCAB.NS")   # use .NS for NSE
news = ticker.get_news(count=10, tab="news")
print(news)
