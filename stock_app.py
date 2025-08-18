import re
import time
import json
import numpy as np
import pandas as pd
import yfinance as yf
import requests
import streamlit as st

try:
    import pdfplumber  # PDF text extraction
    PDF_OK = True
except Exception:
    PDF_OK = False

# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Live Portfolio Tracker (PDF + ISIN)", layout="wide")

st.title("📈 Live Portfolio Tracker — PDF Upload • ISIN→Ticker • Multi‑Currency")
st.caption("Enter holdings manually or upload a PDF statement (Instrument → ISIN → Quantity → Price Currency). App resolves ISINs to tickers via OpenFIGI and fetches live data via Yahoo Finance.")

# Optional auto-refresh
with st.sidebar:
    st.header("⚙️ Settings")
    base_ccy = st.selectbox("Base currency", ["USD", "GBP", "EUR"], index=0)
    period = st.selectbox("History period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
    interval = st.selectbox("Chart interval", ["1d", "1h", "30m"], index=0)
    refresh_on = st.checkbox("Auto-refresh", value=False)
    refresh_secs = st.slider("Refresh seconds", 10, 180, 60)

# Auto-refresh using streamlit-autorefresh if present
try:
    from streamlit_autorefresh import st_autorefresh
    if refresh_on:
        st_autorefresh(interval=refresh_secs * 1000, key="auto")
except Exception:
    if refresh_on:
        st.info("Install optional dependency 'streamlit-autorefresh' to enable timed refresh.")

# =============================
# Helpers
# =============================
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")
NUM_RE = re.compile(r"^[0-9.,]+$")
PRICE_RE = re.compile(r"^([0-9.,]+)\s*([A-Za-z$€£]{1,4})?$")

@st.cache_data(ttl=3600)
def figi_map_isins(isins: list[str]) -> dict:
    """Batch map ISIN -> ticker with OpenFIGI. Uses st.secrets['OPENFIGI_API_KEY'] if present."""
    if not isins:
        return {}
    url = "https://api.openfigi.com/v3/mapping"
    headers = {"Content-Type": "application/json"}
    api_key = st.secrets.get("OPENFIGI_API_KEY") if hasattr(st, "secrets") else None
    if api_key:
        headers["X-OPENFIGI-APIKEY"] = api_key

    # Build payload in chunks of up to 100
    mapping = {}
    chunk = []
    for isin in isins:
        chunk.append({"idType": "ID_ISIN", "idValue": isin})
        if len(chunk) == 100:
            r = requests.post(url, headers=headers, data=json.dumps(chunk), timeout=20)
            data = r.json()
            for req, resp in zip(chunk, data):
                if isinstance(resp, dict) and resp.get("data"):
                    mapping[req["idValue"]] = resp["data"][0].get("ticker")
            chunk = []
    if chunk:
        r = requests.post(url, headers=headers, data=json.dumps(chunk), timeout=20)
        data = r.json()
        for req, resp in zip(chunk, data):
            if isinstance(resp, dict) and resp.get("data"):
                mapping[req["idValue"]] = resp["data"][0].get("ticker")
    return mapping

@st.cache_data(ttl=900)
def fx_series(from_ccy: str, to_ccy: str, period: str, interval: str) -> pd.Series:
    """Return FX series (from_ccy -> to_ccy) aligned to download period. If same currency, return 1s."""
    from_ccy = (from_ccy or "").upper()
    to_ccy = (to_ccy or "").upper()
    if not from_ccy or not to_ccy or from_ccy == to_ccy:
        # return a constant 1 series
        idx = yf.download("SPY", period=period, interval=interval, progress=False).index
        return pd.Series(1.0, index=idx)

    # Yahoo FX tickers like EURUSD=X, GBPUSD=X, JPYUSD=X
    pair = f"{from_ccy}{to_ccy}=X"
    df = yf.download(pair, period=period, interval=interval, auto_adjust=True, progress=False)
    if df is None or df.empty:
        # Try inverse then invert
        inv = f"{to_ccy}{from_ccy}=X"
        invdf = yf.download(inv, period=period, interval=interval, auto_adjust=True, progress=False)
        if invdf is None or invdf.empty:
            idx = yf.download("SPY", period=period, interval=interval, progress=False).index
            return pd.Series(1.0, index=idx)
        s = invdf["Close"]
        return 1.0 / s
    return df["Close"]

@st.cache_data(ttl=600)
def load_price_series(ticker: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False, threads=True)
    if isinstance(df, pd.DataFrame) and not df.empty:
        df = df.dropna()
    return df

@st.cache_data(ttl=120)
def latest_price_and_currency(ticker: str) -> tuple[float|None, str|None]:
    try:
        t = yf.Ticker(ticker)
        # fast_info is faster/safer than info
        fi = getattr(t, "fast_info", {}) or {}
        last = fi.get("last_price") or fi.get("last_close")
        ccy = fi.get("currency") or None
        if not last:
            h = t.history(period="5d")
            if not h.empty:
                last = float(h["Close"].iloc[-1])
        return (float(last) if last else None, ccy)
    except Exception:
        return (None, None)

# =============================
# PDF Upload & Parsing
# =============================
st.sidebar.subheader("📄 Upload PDF (optional)")
if not PDF_OK:
    st.sidebar.warning("Install 'pdfplumber' to enable PDF parsing.")
uploaded_pdf = st.sidebar.file_uploader("Broker statement (PDF)", type=["pdf"]) if PDF_OK else None


def parse_pdf_lines(txt: str) -> list[dict]:
    """Parse blocks of 4 lines: Instrument, ISIN, Quantity, Price Currency."""
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    out = []
    i = 0
    while i + 3 < len(lines):
        inst, maybe_isin, qty_line, price_line = lines[i:i+4]
        # Validate pattern; if no ISIN at i+1, advance by 1 and continue
        if not ISIN_RE.match(maybe_isin):
            i += 1
            continue
        # Quantity
        qty = None
        if NUM_RE.match(qty_line.replace(",", "")):
            try:
                qty = float(qty_line.replace(",", ""))
            except Exception:
                qty = None
        # Price + currency
        m = PRICE_RE.match(price_line)
        price_val, ccy = None, None
        if m:
            try:
                price_val = float(m.group(1).replace(",", ""))
            except Exception:
                price_val = None
            ccy = (m.group(2) or "").upper().replace("$", "USD").replace("£", "GBP").replace("€", "EUR") or None
        out.append({
            "Instrument": inst,
            "ISIN": maybe_isin,
            "Quantity": qty,
            "PurchasePrice": price_val,
            "PurchaseCcy": ccy,
        })
        i += 4
    return out

parsed_records: list[dict] = []
if uploaded_pdf is not None and PDF_OK:
    with pdfplumber.open(uploaded_pdf) as pdf:
        text_all = "\n".join([p.extract_text() or "" for p in pdf.pages])
    parsed_records = parse_pdf_lines(text_all)
    if not parsed_records:
        st.warning("Couldn’t detect holdings from the PDF. You can still enter them manually below.")
    else:
        st.success(f"Parsed {len(parsed_records)} holdings from PDF.")

# =============================
# Manual input (also used to edit parsed)
# =============================
st.subheader("📝 Holdings Input (edit or add)")
example = [
    {"Instrument": "Apple Inc.", "ISIN": "US0378331005", "Quantity": 10, "PurchasePrice": 150.0, "PurchaseCcy": "USD"},
    {"Instrument": "BP plc", "ISIN": "GB0007980591", "Quantity": 25, "PurchasePrice": 4.75, "PurchaseCcy": "GBP"},
]

if "holdings_df" not in st.session_state:
    st.session_state.holdings_df = pd.DataFrame(parsed_records if parsed_records else example)

# Merge parsed over existing if present
if parsed_records:
    uploaded_df = pd.DataFrame(parsed_records)
    st.session_state.holdings_df = uploaded_df

editable = st.data_editor(
    st.session_state.holdings_df,
    num_rows="dynamic",
    use_container_width=True,
    key="holdings_editor",
)

# Persist back
st.session_state.holdings_df = editable

# =============================
# Resolve ISIN -> Ticker
# =============================
st.subheader("🔎 Resolve ISIN to Ticker (OpenFIGI)")
all_isins = [x for x in editable["ISIN"].astype(str).tolist() if ISIN_RE.match(x)] if not editable.empty else []
res_map = figi_map_isins(all_isins) if all_isins else {}

# Allow manual overrides
editable["Ticker"] = editable["ISIN"].map(res_map)
editable["Ticker"] = editable["Ticker"].fillna("")
edited_with_tickers = st.data_editor(
    editable,
    num_rows="dynamic",
    use_container_width=True,
    key="tickers_editor",
)

# =============================
# Fetch live prices and compute portfolio
# =============================
st.subheader("💼 Live Portfolio")

rows = []
for _, r in edited_with_tickers.iterrows():
    ticker = (r.get("Ticker") or "").strip()
    isin = r.get("ISIN")
    qty = float(r.get("Quantity") or 0)
    ppx = r.get("PurchasePrice")
    pccy = r.get("PurchaseCcy") or base_ccy

    if not ticker:
        rows.append({
            "Instrument": r.get("Instrument"),
            "ISIN": isin,
            "Ticker": "",
            "Quantity": qty,
            "LastPrice": None,
            "PriceCcy": None,
            f"Value ({base_ccy})": 0.0,
            "Unrealized P/L": None,
        })
        continue

    last, price_ccy = latest_price_and_currency(ticker)
    # Fallback if currency unknown
    if price_ccy is None:
        price_ccy = base_ccy

    # Convert last to base currency
    fx = fx_series(price_ccy, base_ccy, period=period, interval=interval)
    fx_last = float(fx.iloc[-1]) if not fx.empty else 1.0
    last_base = (last or 0.0) * fx_last

    value_base = qty * last_base

    # Unrealized P/L (convert purchase price to base)
    pnl = None
    if ppx is not None:
        px_fx = fx_series(pccy, base_ccy, period=period, interval=interval)
        px_rate = float(px_fx.iloc[-1]) if not px_fx.empty else 1.0
        cost_base = qty * float(ppx) * px_rate
        pnl = value_base - cost_base

    rows.append({
        "Instrument": r.get("Instrument"),
        "ISIN": isin,
        "Ticker": ticker,
        "Quantity": qty,
        "LastPrice": last,
        "PriceCcy": price_ccy,
        f"Value ({base_ccy})": value_base,
        "Unrealized P/L": pnl,
    })

portfolio_df = pd.DataFrame(rows)
if not portfolio_df.empty:
    c1, c2, c3 = st.columns(3)
    with c1:
        total_val = float(portfolio_df[f"Value ({base_ccy})"].sum())
        st.metric(f"Total Value ({base_ccy})", f"{total_val:,.2f}")
    with c2:
        realized = float(portfolio_df["Unrealized P/L"].fillna(0).sum())
        st.metric("Unrealized P/L", f"{realized:,.2f}")
    with c3:
        n_pos = int((portfolio_df["Quantity"] > 0).sum())
        st.metric("Positions", f"{n_pos}")

    st.dataframe(portfolio_df, use_container_width=True)
else:
    st.info("Add tickers above or upload a PDF to see your live portfolio.")

# =============================
# Historical total portfolio curve
# =============================
st.subheader("📉 Historical Portfolio Value")

def portfolio_history(df: pd.DataFrame, base: str) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    parts = []
    for _, r in df.iterrows():
        ticker = (r.get("Ticker") or "").strip()
        if not ticker:
            continue
        qty = float(r.get("Quantity") or 0)
        # price series in native ccy
        px = load_price_series(ticker, period=period, interval=interval)
        if px is None or px.empty:
            continue
        last_ccy = latest_price_and_currency(ticker)[1] or base
        fx = fx_series(last_ccy, base, period=period, interval=interval)
        # align indices
        s = (px["Close"].reindex(fx.index, method="nearest") * fx).dropna()
        parts.append(qty * s)
    if not parts:
        return pd.Series(dtype=float)
    total = pd.concat(parts, axis=1).sum(axis=1)
    return total

hist_total = portfolio_history(edited_with_tickers, base=base_ccy)
if not hist_total.empty:
    st.line_chart(hist_total)
else:
    st.caption("No historical data to plot yet.")

# =============================
# (Optional) AI Insights — explain how to enable
# =============================
st.subheader("🤖 AI Insights (optional)")
st.markdown(
    """
    You can enable AI-generated summaries and risk insights by adding an OpenAI API key to **Secrets** and uncommenting the code below.

    1. In Streamlit Cloud: **App → Settings → Secrets** add:
       
       ```toml
       OPENAI_API_KEY = "sk-..."
       ```
    2. In this file, add `openai` to requirements and use the snippet shown to generate a summary.
    """
)

with st.expander("Show example code (disabled by default)"):
    st.code(
        """
# requirements.txt add: openai
# from openai import OpenAI
# client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
# prompt = f"Summarize risks and diversification for this portfolio: {portfolio_df.to_dict(orient='records')} base={base_ccy}"
# resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content": prompt}])
# st.write(resp.choices[0].message.content)
        """,
        language="python",
    )

st.caption("Last updated: " + time.strftime("%Y-%m-%d %H:%M:%S"))
