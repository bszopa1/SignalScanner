import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.title("📈 SignalScanner – Krypto & US-Aktien Signale")

# --- Asset Auswahl ---
assets = st.multiselect(
    "Wähle die Assets aus:",
    options=["BTC-USD", "ETH-USD", "XRP-USD", "AAPL", "TSLA", "NVDA", "MSFT", "AMZN"],
    default=["BTC-USD", "ETH-USD", "XRP-USD", "AAPL", "TSLA"]
)

# --- Zeitraum ---
period = st.selectbox(
    "Zeitraum:",
    ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
    index=3
)

# --- Cache für Daten ---
@st.cache_data
def load_data(ticker, period):
    df = yf.download(ticker, period=period)
    return df

# --- Funktion für Signale ---
def compute_signals(df, rsi_len=14):
    if 'Close' not in df.columns:
        return df

    # Close als 1D-Serie sicherstellen
    close_col = df['Close']
    if isinstance(close_col, pd.DataFrame):
        close_col = close_col.iloc[:, 0]

    close_col = pd.to_numeric(close_col, errors='coerce')
    df = df.assign(Close=close_col)
    df = df.dropna(subset=['Close'])

    # SMA
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()

    # RSI
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)

    # Signale
    df['Signal'] = ''
    df.loc[df['SMA20'] > df['SMA50'], 'Signal'] = 'BUY'
    df.loc[df['SMA20'] < df['SMA50'], 'Signal'] = 'SELL'

    return df

# --- Daten laden & Fortschritt anzeigen ---
all_data = {}
for a in assets:
    st.write(f"Lade Daten für {a}…")
    df = load_data(a, period)
    if df.empty or 'Close' not in df.columns:
        st.write(f"Keine Daten für {a} verfügbar.")
        continue
    df = compute_signals(df)
    if df.empty:
        continue
    all_data[a] = df

# --- Signaltabelle ---
signal_rows = []
for name, df in all_data.items():
    last = df.tail(1).iloc[0]
    try:
        last_close = float(last['Close'])
    except (ValueError, TypeError):
        last_close = None
    signal_rows.append([
        name,
        round(last_close, 2) if last_close is not None else 'N/A',
        last['Signal']
    ])

st.subheader('🔍 Aktuelle Signale')
signal_df = pd.DataFrame(signal_rows, columns=['Asset', 'Preis', 'Signal'])
st.dataframe(signal_df)

# --- Charts ---
st.subheader('📊 Charts')
for name, df in all_data.items():
    st.write(f'### {name}')
    st.line_chart(df[['Close', 'SMA20', 'SMA50', 'rsi']])
