import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- App Titel ---
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

# --- Signale berechnen ---
def compute_signals(df, rsi_len=14):
    if df is None or df.empty or 'Close' not in df.columns:
        return pd.DataFrame()

    df = df.copy()

    # Close bereinigen
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df[df["Close"].notna()]

    if len(df) < 50:
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


# --- Daten laden ---
all_data = {}
for a in assets:
    st.write(f"Lade Daten für {a}…")
    raw = yf.download(a, period=period)
    df = compute_signals(raw)
    if df.empty:
        st.write(f"→ Keine ausreichenden Daten für {a}.")
        continue
    all_data[a] = df


# --- Signaltabelle ---
signal_rows = []

for name, df in all_data.items():
    last = df.iloc[-1]

    # ---- sichere Werteextraktion ----
    def safe_float(v):
        try:
            return float(v) if v is not None and not pd.isna(v) else None
        except:
            return None

    last_close = safe_float(last.get("Close"))
    atr_val = safe_float(last.get("ATR"))

    # Signal sicher zu String konvertieren
    sig_raw = last.get("Signal")
    if isinstance(sig_raw, (pd.Series, list, tuple)):
        sig_raw = sig_raw[0]
    signal = str(sig_raw) if sig_raw and not pd.isna(sig_raw) else "N/A"

    stop_loss = take_profit = position_size = None

    if last_close and atr_val and signal in ("BUY", "SELL"):
        if signal == "BUY":
            stop_loss = last_close - atr_val
            take_profit = last_close + 2 * atr_val
        else:
            stop_loss = last_close + atr_val
            take_profit = last_close - 2 * atr_val

        risk = abs(last_close - stop_loss)
        if risk > 0:
            position_size = (capital * risk_per_trade) / risk

    signal_rows.append([
        name,
        round(last_close, 2) if last_close else "N/A",
        signal,
        round(stop_loss, 2) if stop_loss else "N/A",
        round(take_profit, 2) if take_profit else "N/A",
        round(position_size, 8) if position_size else "N/A"
    ])


# --- Tabelle anzeigen ---
st.subheader("🔍 Aktuelle Signale mit Risiko-Management")
signal_df = pd.DataFrame(signal_rows, columns=[
    "Asset", "Preis", "Signal", "Stop-Loss", "Take-Profit", "Positionsgröße"
])


def highlight_signal(row):
    if row["Signal"] == "BUY":
        return ["background-color:#b6fcd5"] * len(row)
    if row["Signal"] == "SELL":
        return ["background-color:#fcb6b6"] * len(row)
    return [""] * len(row)


st.dataframe(signal_df.style.apply(highlight_signal, axis=1))


# --- Charts ---
st.subheader("📊 Charts")
for name, df in all_data.items():
    st.write(f"### {name}")
    cols = [c for c in ["Close", "SMA20", "SMA50", "rsi"] if c in df.columns]
    if cols:
        st.line_chart(df[cols])
