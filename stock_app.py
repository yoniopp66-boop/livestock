import streamlit as st
import requests
import pandas as pd
import datetime

# Replace with your own Finnhub API key
API_KEY = "YOUR_API_KEY"
BASE_URL = "https://finnhub.io/api/v1"

st.title("📈 Live Stock Tracker")

# Input box for ticker symbol
ticker = st.text_input("Enter stock symbol (e.g., AAPL, MSFT, TSLA):", "AAPL")

def get_quote(symbol):
    url = f"{BASE_URL}/quote"
    params = {"symbol": symbol, "token": API_KEY}
    r = requests.get(url, params=params)
    if r.status_code == 200:
        return r.json()
    else:
        return None

if st.button("Get Live Price"):
    data = get_quote(ticker)
    if data:
        st.success(f"**{ticker}** Live Price: ${data['c']}")
        st.write(f"Open: {data['o']}")
        st.write(f"High: {data['h']}")
        st.write(f"Low: {data['l']}")
        st.write(f"Previous Close: {data['pc']}")
    else:
        st.error("Failed to fetch data. Check the ticker or API key.")
