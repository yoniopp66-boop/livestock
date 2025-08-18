import streamlit as st
import pandas as pd
import yfinance as yf
import finnhub
import datetime
import matplotlib.pyplot as plt
import requests

# --- API Keys ---
FINNHUB_API_KEY = 'd2h3pphr01qon4eacl30d2h3pphr01qon4eacl3g'
AI_API_KEY = 'c52961570ab5466badce46de90f8d380'

# Initialize Finnhub client
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

# --- Load Portfolio CSV ---
csv_path = '/mnt/data/from_2025-03-05_to_2025-08-17_MTc1NTQzNTg3NjEwNg.csv'
portfolio_df = pd.read_csv(csv_path)

# Expected CSV columns: Instrument, ISIN, Quantity, Price, Currency, PurchaseDate

# --- Helper Functions ---
@st.cache_data
def fetch_price(ticker):
    try:
        data = yf.Ticker(ticker).fast_info
        return data['last_price'] if 'last_price' in data else None
    except:
        return None

@st.cache_data
def fetch_historical(ticker, period='1y'):
    try:
        hist = yf.Ticker(ticker).history(period=period)
        return hist[['Close']]
    except:
        return pd.DataFrame()

@st.cache_data
def ai_insights(text):
    url = 'https://api.aimlapi.com/generate'  # example endpoint
    payload = {
        'api_key': AI_API_KEY,
        'prompt': f'Analyze this stock portfolio data and provide insights: {text}',
        'max_tokens': 300
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json().get('text', '')
    except:
        return 'AI Insights unavailable.'

# --- Streamlit Layout ---
st.set_page_config(page_title='📊 Portfolio Tracker', layout='wide')
st.title('📈 Portfolio Tracker with AI Insights')

# Fetch live prices and calculate total value
portfolio_df['CurrentPrice'] = portfolio_df['Instrument'].apply(fetch_price)
portfolio_df['TotalValue'] = portfolio_df['Quantity'] * portfolio_df['CurrentPrice']
portfolio_df['ProfitLoss'] = portfolio_df['TotalValue'] - (portfolio_df['Quantity'] * portfolio_df['Price'])

# Display Portfolio
st.subheader('Portfolio Overview')
st.dataframe(portfolio_df)

# Portfolio Metrics
st.subheader('Portfolio Metrics')
total_value = portfolio_df['TotalValue'].sum()
total_invested = (portfolio_df['Quantity'] * portfolio_df['Price']).sum()
total_profit = total_value - total_invested
st.metric('Total Invested', f'{total_invested:.2f} GBP')
st.metric('Current Value', f'{total_value:.2f} GBP')
st.metric('Total Profit / Loss', f'{total_profit:.2f} GBP')

# Charts
st.subheader('Portfolio Distribution')
fig, ax = plt.subplots()
ax.pie(portfolio_df['TotalValue'], labels=portfolio_df['Instrument'], autopct='%1.1f%%')
st.pyplot(fig)

st.subheader('Price History Charts')
for ticker in portfolio_df['Instrument']:
    hist = fetch_historical(ticker)
    if not hist.empty:
        st.line_chart(hist['Close'], use_container_width=True)

# AI Insights
st.subheader('AI Insights')
portfolio_text = portfolio_df.to_string()
insights = ai_insights(portfolio_text)
st.write(insights)
