import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Portfolio Tracker", layout="wide")

st.title("📊 Portfolio Tracker")

st.sidebar.header("Add Stock to Portfolio")
ticker = st.sidebar.text_input("Ticker (e.g. AAPL, TSLA, MSFT.L)")
quantity = st.sidebar.number_input("Quantity", min_value=0, step=1)
purchase_price = st.sidebar.number_input("Purchase Price (per share)", min_value=0.0, step=0.01)
purchase_date = st.sidebar.date_input("Purchase Date", value=datetime(2024,1,1))

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

if st.sidebar.button("Add to Portfolio"):
    if ticker and quantity > 0:
        st.session_state.portfolio.append({
            "ticker": ticker.upper(),
            "quantity": quantity,
            "purchase_price": purchase_price,
            "purchase_date": purchase_date
        })

if not st.session_state.portfolio:
    st.info("Add some stocks from the sidebar to start tracking your portfolio.")
    st.stop()

# Fetch live data from Yahoo Finance
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.history(period="1d")
        if not info.empty:
            last_price = info["Close"].iloc[-1]
            return last_price
        else:
            return None
    except Exception as e:
        return None

portfolio_data = []

for stock in st.session_state.portfolio:
    current_price = fetch_data(stock["ticker"])
    if current_price:
        value_now = current_price * stock["quantity"]
        cost_basis = stock["purchase_price"] * stock["quantity"]
        pl = value_now - cost_basis
        pl_pct = (pl / cost_basis * 100) if cost_basis > 0 else 0
        portfolio_data.append({
            "Ticker": stock["ticker"],
            "Quantity": stock["quantity"],
            "Purchase Price": stock["purchase_price"],
            "Purchase Date": stock["purchase_date"],
            "Current Price": round(current_price,2),
            "Current Value": round(value_now,2),
            "P/L": round(pl,2),
            "P/L %": round(pl_pct,2)
        })
    else:
        portfolio_data.append({
            "Ticker": stock["ticker"],
            "Quantity": stock["quantity"],
            "Purchase Price": stock["purchase_price"],
            "Purchase Date": stock["purchase_date"],
            "Current Price": "N/A",
            "Current Value": "N/A",
            "P/L": "N/A",
            "P/L %": "N/A"
        })

# Display portfolio
df = pd.DataFrame(portfolio_data)
st.subheader("Portfolio Overview")
st.dataframe(df, use_container_width=True)

# Summary metrics
valid_entries = [row for row in portfolio_data if isinstance(row["P/L"], (int, float))]
if valid_entries:
    total_value = sum(row["Current Value"] for row in valid_entries)
    total_cost = sum(row["Purchase Price"] * row["Quantity"] for row in valid_entries)
    total_pl = total_value - total_cost
    total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Portfolio Value", f"${total_value:,.2f}")
    col2.metric("📈 Total P/L", f"${total_pl:,.2f}", f"{total_pl_pct:.2f}%")
    col3.metric("📊 Number of Holdings", len(valid_entries))

# Historical chart per stock
st.subheader("Stock Performance Charts")
for stock in st.session_state.portfolio:
    st.write(f"### {stock['ticker']}")
    try:
        hist = yf.download(stock['ticker'], period="6mo", interval="1d")
        if not hist.empty:
            st.line_chart(hist['Close'])
        else:
            st.warning(f"No data available for {stock['ticker']}")
    except:
        st.warning(f"Error fetching data for {stock['ticker']}")
