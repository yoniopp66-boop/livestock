import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import time

# --- CONFIG ---
REFRESH_INTERVAL = 60  # seconds

# --- APP ---
st.set_page_config(page_title="Live Stock Tracker", layout="wide")

st.title("📈 Live Stock Tracker")

# Sidebar inputs
st.sidebar.header("Portfolio Settings")
tickers = st.sidebar.text_input(
    "Enter tickers (comma separated)", "AAPL, MSFT, GOOGL"
)
portfolio = [t.strip().upper() for t in tickers.split(",") if t.strip()]

ma_days = st.sidebar.multiselect(
    "Select Moving Averages",
    [10, 20, 50, 100, 200],
    default=[20, 50]
)

refresh = st.sidebar.checkbox("Auto-refresh every 60s", value=True)

# Fetch data function
def get_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")
        return hist
    except Exception as e:
        st.error(f"Failed to fetch {ticker}: {e}")
        return None

# Display portfolio
for ticker in portfolio:
    st.subheader(f"📊 {ticker}")
    data = get_data(ticker)

    if data is not None and not data.empty:
        # Latest price
        latest_price = data["Close"].iloc[-1]
        st.metric("Latest Price", f"${latest_price:.2f}")

        # Moving averages
        for ma in ma_days:
            data[f"MA{ma}"] = data["Close"].rolling(ma).mean()

        # Chart
        st.line_chart(data[["Close"] + [f"MA{ma}" for ma in ma_days if f"MA{ma}" in data]])

        # Show recent data table
        st.dataframe(data.tail(10))

# Auto-refresh
if refresh:
    time.sleep(REFRESH_INTERVAL)
    st.rerun()
