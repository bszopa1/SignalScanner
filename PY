import streamlit as st
import yfinance as yf
import pandas as pd

# --- App Title ---
st.title("📈 SignalScanner – Krypto & US-Aktien Signale")

# --- Asset Auswahl ---
assets = st.multiselect(
    "Wähle die Assets aus:",
    options=[
        'BTC-USD', 'ETH-USD', 'XRP-USD',
        'AAPL', 'TSLA', 'NVDA', 'MSFT', 'AMZN'
    ],
    default=['BTC-USD', 'ETH-USD', 'XRP-USD', 'AAPL', 'TSLA']
)

# --- Zeitraum ---
period = st.selectbox(
    "Zeitraum:",
    ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'],
    index=3
)

# --- Funktion für Signale ---
def compute_signals(df):
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()

    df["Signal"] = ""
    df.loc[df["SMA20"] > df["SMA50"], "Signal"] = "BUY"
    df.loc[df["SMA20"] < df["SMA50"], "Signal"] = "SELL"

    return df

# --- Daten laden ---
all_data = {}
for a in assets:
    df = yf.download(a, period=period)
    if not df.empty:
        df = compute_signals(df)
        all_data[a] = df

# --- Signaltabelle ---
signal_rows = []
for name, df in all_data.items():
    last = df.tail(1).iloc[0]
    signal_rows.append([
        name,
        round(last["Close"], 2),
        last["Signal"]
    ])

st.subheader("🔍 Aktuelle Signale")
signal_df = pd.DataFrame(signal_rows, columns=["Asset", "Preis", "Signal"])
st.dataframe(signal_df)

# --- Charts ---
st.subheader("📊 Charts")

for name, df in all_data.items():
    st.write(f"### {name}")
    st.line_chart(df[["Close", "SMA20", "SMA50"]])
