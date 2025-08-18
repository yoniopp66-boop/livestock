import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import datetime

st.set_page_config(page_title="Portfolio Tracker", layout="wide")

st.title("📊 Multi-Currency Portfolio Tracker")

# Sidebar for portfolio input
st.sidebar.header("Your Portfolio")
st.sidebar.markdown("Enter your holdings below:")

# Example portfolio structure
example = "AAPL,10,USD\nTSLA,5,USD\nBMW.DE,8,EUR\n9984.T,3,JPY"
portfolio_text = st.sidebar.text_area("Ticker,Quantity,Currency", example, height=150)

# Parse portfolio
portfolio = []
for line in portfolio_text.splitlines():
    try:
        ticker, qty, currency = [x.strip() for x in line.split(",")]
        portfolio.append({"ticker": ticker, "quantity": float(qty), "currency": currency})
    except:
        continue

# Fetch FX rates
def get_fx_rate(base, target="USD"):
    if base == target:
        return 1.0
    try:
        pair = f"{base}{target}=X"
        data = yf.Ticker(pair).history(period="1d")
        return data["Close"].iloc[-1]
    except:
        return None

# Portfolio DataFrame
records = []
for asset in portfolio:
    ticker = asset["ticker"]
    qty = asset["quantity"]
    cur = asset["currency"]

    try:
        data = yf.Ticker(ticker)
        hist = data.history(period="1y")
        price = hist["Close"].iloc[-1]

        # Convert to USD for total value
        fx_rate = get_fx_rate(cur, "USD")
        if fx_rate is None:
            continue

        value_local = qty * price
        value_usd = value_local * fx_rate

        records.append({
            "Ticker": ticker,
            "Currency": cur,
            "Quantity": qty,
            "Price (Local)": price,
            "Value (Local)": value_local,
            "Value (USD)": value_usd
        })
    except:
        continue

if records:
    df = pd.DataFrame(records)
    st.subheader("Current Portfolio")
    st.dataframe(df, use_container_width=True)

    total_value = df["Value (USD)"].sum()
    st.metric("Total Portfolio Value (USD)", f"${total_value:,.2f}")

    # Pie chart of allocations
    fig, ax = plt.subplots()
    ax.pie(df["Value (USD)"], labels=df["Ticker"], autopct="%1.1f%%")
    ax.set_title("Portfolio Allocation (USD)")
    st.pyplot(fig)

    # Show performance over time (historical portfolio value)
    st.subheader("Historical Portfolio Value (USD)")
    combined = pd.DataFrame()

    for asset in portfolio:
        ticker = asset["ticker"]
        qty = asset["quantity"]
        cur = asset["currency"]

        data = yf.Ticker(ticker).history(period="1y")["Close"]
        fx_rate = get_fx_rate(cur, "USD")
        if fx_rate is None:
            continue
        combined[ticker] = data * qty * fx_rate

    combined["Total"] = combined.sum(axis=1)
    st.line_chart(combined["Total"])

else:
    st.warning("⚠️ Please enter a valid portfolio above.")

# Placeholder for AI insights
st.subheader("🤖 AI Insights (Coming Soon)")
st.markdown("This section will analyze your portfolio using AI to suggest diversification, risk analysis, and growth opportunities.")
