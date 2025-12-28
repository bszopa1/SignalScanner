import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="SignalScanner", layout="wide")

st.title("📈 SignalScanner – Krypto & US-Aktien Signale mit Risiko-Management")

# --- Kapital & Risiko ---
capital = st.number_input("Kapital in USD:", value=1000, step=100)
risk_per_trade = st.slider("Max Risiko pro Trade (%):", 0.5, 10.0, 2.0) / 100

# --- Asset Auswahl ---
assets = st.multiselect(
    "Wähle die Assets aus:",
    options=[
        "BTC-USD", "ETH-USD", "XRP-USD",
        "AAPL", "TSLA", "NVDA", "MSFT", "AMZN"
    ],
    default=["BTC-USD", "ETH-USD", "XRP-USD", "AAPL", "TSLA"]
)

# --- Zeitraum ---
period = st.selectbox(
    "Zeitraum:",
    ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
    index=3
)


# ==============================
# SIGNAL FUNKTION
# ==============================
def compute_signals(df):
    if df is None or df.empty:
        return pd.DataFrame()

    # MultiIndex zu normalen Columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(c).strip() for c in df.columns]

    # sichere Close-Spalte finden
    for c in ["Close", "Adj Close", "Close_Close", "Adj Close_Close"]:
        if c in df.columns:
            df["Close_safe"] = pd.to_numeric(df[c], errors="coerce")
            break
    else:
        return pd.DataFrame()

    df = df.dropna(subset=["Close_safe"]).copy()

    if len(df) < 60:
        return pd.DataFrame()

    df["SMA20"] = df["Close_safe"].rolling(20).mean()
    df["SMA50"] = df["Close_safe"].rolling(50).mean()
    df["RSI"] = ta.rsi(df["Close_safe"], length=14)

    if all(x in df.columns for x in ["High", "Low"]):
        df["ATR"] = ta.atr(df["High"], df["Low"], df["Close_safe"], length=14)
    else:
        df["ATR"] = None

    df["Signal"] = "NEUTRAL"
    df.loc[df["SMA20"] > df["SMA50"], "Signal"] = "BUY"
    df.loc[df["SMA20"] < df["SMA50"], "Signal"] = "SELL"

    return df


# ==============================
# DATEN LADEN
# ==============================
all_data = {}

for a in assets:
    st.write(f"Lade Daten für **{a}** …")
    raw = yf.download(a, period=period)
    df = compute_signals(raw)

    if df.empty:
        st.write(f"→ Keine ausreichenden Daten für {a}")
        continue

    all_data[a] = df


# ==============================
# SIGNAL TABELLE
# ==============================
signal_rows = []

for name, df in all_data.items():
    last = df.iloc[-1]

    price = float(last["Close_safe"])
    signal = str(last["Signal"])
    atr = last["ATR"] if pd.notna(last["ATR"]) else None

    stop = tp = size = "N/A"

    if atr and atr > 0:
        if signal == "BUY":
            stop = price - atr
            tp = price + atr * 2
        elif signal == "SELL":
            stop = price + atr
            tp = price - atr * 2

        risk_per_unit = abs(price - stop)
        if risk_per_unit > 0:
            size = (capital * risk_per_trade) / risk_per_unit

    signal_rows.append([
        name,
        round(price, 2),
        signal,
        round(stop, 2) if stop != "N/A" else "N/A",
        round(tp, 2) if tp != "N/A" else "N/A",
        round(size, 6) if size != "N/A" else "N/A"
    ])

st.subheader("🔍 Aktuelle Signale")

signal_df = pd.DataFrame(signal_rows,
                         columns=["Asset", "Preis", "Signal", "Stop-Loss", "Take-Profit", "Positionsgröße"])


def highlight(row):
    if row["Signal"] == "BUY":
        return ["background-color:#b6fcd5"] * len(row)
    if row["Signal"] == "SELL":
        return ["background-color:#fcb6b6"] * len(row)
    return [""] * len(row)


st.dataframe(signal_df.style.apply(highlight, axis=1), use_container_width=True)


# ==============================
# CHARTS
# ==============================
st.subheader("📊 Charts")

for name, df in all_data.items():
    st.write(f"### {name}")

    # sichere Chart-Daten
    cols = ["Close_safe"]
    if "SMA20" in df.columns: cols.append("SMA20")
    if "SMA50" in df.columns: cols.append("SMA50")

    chart = df[cols].rename(columns={"Close_safe": "Close"})

    st.line_chart(chart)
