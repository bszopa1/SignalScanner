import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import concurrent.futures

# ---------------------------------------------------------
# 🔥 Schneller & stabiler yfinance-Downloader (mit Cache)
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def fast_download(symbol, period):
    """Schnelles Laden mit Timeout und Fallback."""
    def safe_dl():
        try:
            return yf.download(symbol, period=period, progress=False, threads=False)
        except:
            return pd.DataFrame()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as exe:
        future = exe.submit(safe_dl)
        try:
            return future.result(timeout=3)       # ⏱️ maximal 3 Sekunden
        except:
            return pd.DataFrame()                # ❗ Timeout-Fallback


# ---------------------------------------------------------
# App Titel
# ---------------------------------------------------------
st.title("📈 SignalScanner – Krypto & US-Aktien Signale mit Risiko-Management")

# Kapital & Risiko
capital = st.number_input("Kapital in USD:", value=1000, step=100)
risk_per_trade = st.slider("Max Risiko pro Trade (%):", 0.5, 10.0, 2.0) / 100

# Asset Auswahl
assets = st.multiselect(
    "Wähle die Assets aus:",
    [
        "BTC-USD", "ETH-USD", "XRP-USD",
        "AAPL", "TSLA", "NVDA", "MSFT", "AMZN"
    ],
    default=["BTC-USD", "ETH-USD", "XRP-USD", "AAPL", "TSLA"]
)

# Zeitraum
period = st.selectbox(
    "Zeitraum:",
    ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
    index=3
)

# ---------------------------------------------------------
# Signalberechnung
# ---------------------------------------------------------
def compute_signals(df, rsi_len=14):

    if df is None or df.empty or "Close" not in df.columns:
        return pd.DataFrame()

    close = pd.to_numeric(df["Close"], errors="coerce")
    df = df.loc[close.notna()].copy()
    df["Close"] = close.loc[df.index]

    if len(df) < 20:
        return pd.DataFrame()

    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["rsi"] = ta.rsi(df["Close"], length=rsi_len)

    if all(c in df.columns for c in ["High", "Low"]):
        df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
    else:
        df["ATR"] = pd.NA

    df["Signal"] = ""
    df.loc[df["SMA20"] > df["SMA50"], "Signal"] = "BUY"
    df.loc[df["SMA20"] < df["SMA50"], "Signal"] = "SELL"

    return df

# ---------------------------------------------------------
# Daten laden
# ---------------------------------------------------------
all_data = {}
for a in assets:
    st.write(f"📡 Lade Daten für **{a}** …")
    raw = fast_download(a, period)

    if raw.empty:
        st.warning(f"⚠️ {a}: Keine Daten erhalten (Timeout / Yahoo langsam)")
        continue

    df = compute_signals(raw)
    if df.empty:
        st.warning(f"⚠️ {a}: Nicht genug Daten für Indikatoren")
        continue

    all_data[a] = df

# ---------------------------------------------------------
# Signaltabelle
# ---------------------------------------------------------
signal_rows = []

for name, df in all_data.items():
    last = df.iloc[-1]

    last_close = float(last["Close"]) if pd.notna(last["Close"]) else None
    atr_val = float(last["ATR"]) if pd.notna(last["ATR"]) else None
    signal = last["Signal"] if last["Signal"] else None

    stop_loss = take_profit = position_size = None

    if last_close and atr_val and signal:
        if signal == "BUY":
            stop_loss = last_close - atr_val
            take_profit = last_close + 2 * atr_val
        else:
            stop_loss = last_close + atr_val
            take_profit = last_close - 2 * atr_val

        denom = abs(last_close - stop_loss)
        if denom > 0:
            position_size = (capital * risk_per_trade) / denom

    signal_rows.append([
        name,
        round(last_close, 2) if last_close else "N/A",
        signal or "N/A",
        round(stop_loss, 2) if stop_loss else "N/A",
        round(take_profit, 2) if take_profit else "N/A",
        round(position_size, 8) if position_size else "N/A"
    ])

# Tabelle anzeigen
st.subheader("🔍 Aktuelle Signale mit Risiko-Management")
signal_df = pd.DataFrame(signal_rows, columns=[
    "Asset", "Preis", "Signal",
    "Stop-Loss", "Take-Profit", "Positionsgröße"
])

def highlight(row):
    if row["Signal"] == "BUY":
        return ["background-color: #b6fcd5"] * len(row)
    if row["Signal"] == "SELL":
        return ["background-color: #fcb6b6"] * len(row)
    return [""] * len(row)

st.dataframe(signal_df.style.apply(highlight, axis=1))

# ---------------------------------------------------------
# Charts
# ---------------------------------------------------------
st.subheader("📊 Charts")

for name, df in all_data.items():
    st.write(f"### {name}")
    cols = [c for c in ["Close", "SMA20", "SMA50", "rsi"] if c in df.columns]
    if cols:
        st.line_chart(df[cols])
