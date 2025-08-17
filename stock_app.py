import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

st.title("📈 Live Stock Price Tracker")

# User input for ticker
ticker = st.text_input("Enter stock ticker (e.g., AAPL, TSLA, MSFT):", "AAPL")

try:
    stock = yf.Ticker(ticker)

    # Get recent data
    hist = stock.history(period="5d", interval="1h")

    if hist.empty:
        st.error("⚠️ No data found. Please check the ticker symbol.")
    else:
        st.subheader(f"Live Data for {ticker}")
        st.write(hist.tail())

        # Plot closing price
        st.subheader("Price Trend (Last 5 Days, Hourly)")
        fig, ax = plt.subplots()
        ax.plot(hist.index, hist["Close"], label="Close Price")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price (USD)")
        ax.legend()
        st.pyplot(fig)

except Exception as e:
    st.error(f"❌ Failed to fetch data: {e}")
