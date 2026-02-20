import yfinance
import yfinance.base
yf=yfinance.ticker.Ticker("TCS")
print(yf.get_news())