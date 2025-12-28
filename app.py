import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.title("📈 SignalScanner – Krypto & US-Aktien Signale mit Risiko-Management")

# ==============================
# UI
# ==============================
capital = st.number_input("Kapital in USD:", value=1000.0)
risk_percent = st.slider("Max Risiko pro Trade (%):", 0.5, 10.0, 2.0)

assets = st.multiselect(
    "Wähle die Assets aus:",
    ["BTC-USD","ETH-USD","XRP-USD","AAPL","TSLA"],
    default=["BTC-USD","ETH-USD","XRP-USD"]
)

period = st.selectbox("Zeitraum:",["1y","6mo","3mo","1mo"], index=0)


# ==============================
# Signal Logik
# ==============================
def compute_signals(df):
    df = df.copy()

    # Falls Spalten anders heißen → absichern
    if "Close" not in df.columns:
        for c in df.columns:
            if "close" in c.lower():
                df.rename(columns={c:"Close"}, inplace=True)

    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()

    # RSI
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["Signal"] = "N/A"
    df.loc[df["SMA20"] > df["SMA50"], "Signal"] = "BUY"
    df.loc[df["SMA20"] < df["SMA50"], "Signal"] = "SELL"

    return df


# ==============================
# Daten laden & anzeigen
# ==============================
st.subheader("🔍 Aktuelle Signale mit Risiko-Management")

for a in assets:
    st.write(f"### {a}")
    st.write(f"Lade Daten für {a}…")

    df = yf.download(a, period=period)

    # --------- MultiIndex Fix ----------
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() for col in df.columns]

    # Spalten auf Standard-Namen mappen
    rename_map = {
        "Close": "Close",
        "Adj Close": "Close",
        "Close_Close": "Close",
        "Adj Close_Close": "Close",
        "High": "High",
        "High_High": "High",
        "Low": "Low",
        "Low_Low": "Low"
    }

    for k,v in rename_map.items():
        if k in df.columns:
            df.rename(columns={k:v}, inplace=True)

    if "Close" not in df.columns:
        st.error("❌ Keine Close-Daten – Asset übersprungen")
        continue

    df = compute_signals(df)
    last = df.iloc[-1]

    signal = str(last["Signal"])
    close = float(last["Close"])

    if signal == "BUY":
        color = "🟢"
    elif signal == "SELL":
        color = "🔴"
    else:
        color = "⚪"

    st.write(f"Signal: {color} **{signal}**")
    st.write(f"Letzter Preis: **{close:.2f} USD**")

    # Risiko Management
    risk_amount = capital * (risk_percent / 100)

    if signal == "BUY":
        stop = close * 0.95
    elif signal == "SELL":
        stop = close * 1.05
    else:
        stop = None

    if stop:
        distance = abs(close - stop)
        position_size = risk_amount / distance
        st.write(f"Stop Loss: **{stop:.2f} USD**")
        st.write(f"Positionsgröße: **{position_size:.2f} Stück**")

    # ==============================
    # Charts
    # ==============================
    st.write("### 📊 Charts")

    columns_to_plot = [c for c in ["Close","SMA20","SMA50"] if c in df.columns]

    if columns_to_plot:
        try:
            st.line_chart(df[columns_to_plot])
        except Exception as e:
            st.write("⚠️ Chart konnte nicht dargestellt werden:", e)
