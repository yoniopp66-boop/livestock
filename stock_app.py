import streamlit as st
import yfinance as yf
import pandas as pd
import datetime as dt
import time

# --- SETTINGS ---
REFRESH_SECONDS = 60

st.set_page_config(page_title="Live Stock Tracker", layout="wide")

# --- HEADER ---
st.title("📈 Live Stock & Portfolio Dashboard")

# --- AUTO REFRESH ---
st_autorefresh = st.empty()
st_autorefresh.text(f"Auto-refreshing every {REFRESH_SECONDS} seconds...")
st_autorefresh = st_autorefresh

# --- INPUT ---
tickers = st.text_input("Enter stock tickers (comma separated)", "AAPL, MSFT, TSLA").upper().split(",")
portfolio_mode = st.checkbox("Track Portfolio (add quantities)")

portfolio_data = {}
if portfolio_mode:
    st.subheader("💼 Portfolio Input")
    for t in tickers:
        qty = st.number_input(f"Quantity of {t.strip()}", min_value=0, value=0)
        portfolio_data[t.strip()] = qty

# --- FETCH DATA ---
start = dt.datetime.now() - dt.timedelta(days=180)
end = dt.datetime.now()

@st.cache_data(ttl=REFRESH_SECONDS)
def load_data(ticker):
    try:
        data = yf.download(ticker, start=start, end=end, progress=False)
        return data
    except Exception as e:
        st.error(f"Failed to fetch {ticker}: {e}")
        return pd.DataFrame()

# --- SHOW DATA ---
portfolio_value = 0
cols = st.columns(len(tickers))

for i, ticker in enumerate(tickers):
    ticker = ticker.strip()
    if not ticker:
        continue
    data = load_data(ticker)

    if data.empty:
        continue

    # --- Indicators ---
    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA50"] = data["Close"].rolling(50).mean()
    data["MA200"] = data["Close"].rolling(200).mean()

    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    data["EMA12"] = data["Close"].ewm(span=12, adjust=False).mean()
    data["EMA26"] = data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD"] = data["EMA12"] - data["EMA26"]
    data["Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()

    # --- Charts ---
    with cols[i]:
        st.subheader(f"📊 {ticker}")
        st.line_chart(data[["Close", "MA20", "MA50", "MA200"]])
        st.line_chart(data[["MACD", "Signal"]])
        st.line_chart(data[["RSI"]])

    # --- Portfolio value ---
    if portfolio_mode and portfolio_data.get(ticker, 0) > 0:
        latest_price = data["Close"].iloc[-1]
        holding_value = portfolio_data[ticker] * latest_price
        portfolio_value += holding_value

# --- Portfolio Summary ---
if portfolio_mode:
    st.subheader("💼 Portfolio Summary")
    st.write(f"Total Portfolio Value: **${portfolio_value:,.2f}**")

# --- Auto refresh ---
st_autorefresh = st.empty()
st_autorefresh.text(f"Last refreshed: {dt.datetime.now().strftime('%H:%M:%S')}")
st.experimental_rerun()
