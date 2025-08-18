import time
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st

st.set_page_config(page_title="Live Stock & Portfolio Dashboard", layout="wide")
st.title("📈 Live Stock & Portfolio Dashboard")

# --- Sidebar controls ---
with st.sidebar:
    tickers_text = st.text_input(
        "Tickers (comma-separated)", 
        "AAPL, MSFT, TSLA, BP.L"
    )
    tickers = [t.strip().upper() for t in tickers_text.split(",") if t.strip()]
    period = st.selectbox("History range", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=3)
    interval_map = {"1d":"5m", "5d":"15m", "1mo":"1h", "3mo":"1d", "6mo":"1d", "1y":"1d"}
    interval = interval_map[period]

    refresh_secs = st.slider("Auto-refresh (seconds)", 10, 120, 60)
    auto_refresh = st.checkbox("Enable auto-refresh", value=True)

# Auto-refresh (safe & lightweight)
try:
    from streamlit_autorefresh import st_autorefresh
    if auto_refresh:
        st_autorefresh(interval=refresh_secs * 1000, key="auto")
except Exception:
    st.info("Auto-refresh helper not installed; page won’t auto-update. Click ‘Rerun’ to refresh.")

# --- Cached data loader ---
@st.cache_data(ttl=120, show_spinner=False)
def load_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False, threads=True)
    if isinstance(df, pd.DataFrame) and not df.empty:
        df = df.dropna()
    return df

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["Close"]
    # Moving Averages
    out["MA20"] = close.rolling(20).mean()
    out["MA50"] = close.rolling(50).mean()
    out["MA200"] = close.rolling(200).mean()
    # RSI(14)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss.replace(0, np.nan))
    out["RSI"] = 100 - (100 / (1 + rs))
    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    out["MACD"] = ema12 - ema26
    out["Signal"] = out["MACD"].ewm(span=9, adjust=False).mean()
    return out

# --- Top metrics row ---
metrics_cols = st.columns(min(4, max(1, len(tickers))))
latest_prices = {}  # for portfolio calc

for i, t in enumerate(tickers):
    df = load_history(t, period, interval)
    if df.empty:
        metrics_cols[i % len(metrics_cols)].warning(f"{t}: no data")
        continue

    last = df["Close"].iloc[-1]
    prev = df["Close"].iloc[-2] if len(df) > 1 else last
    chg = last - prev
    pct = (chg / prev) * 100 if prev else 0
    latest_prices[t] = float(last)

    with metrics_cols[i % len(metrics_cols)]:
        st.metric(label=t, value=f"{last:,.2f}", delta=f"{chg:,.2f} ({pct:.2f}%)")

st.caption(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# --- Charts per ticker (with indicators) ---
for t in tickers:
    df = load_history(t, period, interval)
    if df.empty:
        continue
    df = add_indicators(df)

    with st.expander(f"📊 {t} — charts & indicators", expanded=False):
        # Price + MAs
        st.line_chart(df[["Close", "MA20", "MA50", "MA200"]])

        # MACD
        st.line_chart(df[["MACD", "Signal"]])

        # RSI
        st.line_chart(df[["RSI"]])

# --- Portfolio tracker ---
st.header("💼 Portfolio")
if not tickers:
    st.info("Add tickers above to start a portfolio.")
else:
    # Prefill editable table
    if "portfolio_df" not in st.session_state:
        st.session_state.portfolio_df = pd.DataFrame({
            "Symbol": tickers,
            "Quantity": [0]*len(tickers),
            "AvgCost": [0.0]*len(tickers)
        })

    # Ensure table includes any new tickers the user typed
    existing = set(st.session_state.portfolio_df["Symbol"].str.upper())
    missing = [t for t in tickers if t not in existing]
    if missing:
        add_rows = pd.DataFrame({"Symbol": missing, "Quantity": [0]*len(missing), "AvgCost":[0.0]*len(missing)})
        st.session_state.portfolio_df = pd.concat([st.session_state.portfolio_df, add_rows], ignore_index=True)

    edited = st.data_editor(
        st.session_state.portfolio_df,
        num_rows="dynamic",
        use_container_width=True,
        key="portfolio_editor"
    )
    st.session_state.portfolio_df = edited

    # Compute live valuation
    port = edited.copy()
    port["Symbol"] = port["Symbol"].str.upper()
    port["LastPrice"] = port["Symbol"].map(latest_prices).fillna(0.0)
    port["PositionValue"] = port["Quantity"] * port["LastPrice"]
    port["UnrealizedPnL"] = (port["LastPrice"] - port["AvgCost"]) * port["Quantity"]

    total_val = port["PositionValue"].sum()
    total_pnl = port["UnrealizedPnL"].sum()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"Total Portfolio Value: **${total_val:,.2f}**")
    with c2:
        st.subheader(f"Unrealized P/L: **${total_pnl:,.2f}**")

    st.dataframe(port, use_container_width=True)
2) Update requirements.txt
Replace its contents with:

nginx
Edit
streamlit
yfinance
pandas
numpy
streamlit-autorefresh
