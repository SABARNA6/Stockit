# from helpers.stock_helper import *
# # from

# # print(get_news("TCS",get_realtime_stock))
# print(get_realtime_stock("TCSs"))
import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

symbol = input("Enter the Symbol")
google_sheet = os.getenv("GOOGLE_SHEETS_URL")
url = f"{google_sheet}?symbol={symbol}"
response = requests.get(url)

print(response.text)

