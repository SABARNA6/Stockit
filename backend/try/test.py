import yfinance as yf
import yfinance.base
import nsepython as nse
yff=yfinance.ticker.Ticker("TCS")
# print(yf.get_news())
ticer = yf.ticker.Ticker("TCS")
info = ticer.info
# print(info)
print(nse.index_info("TCS"))