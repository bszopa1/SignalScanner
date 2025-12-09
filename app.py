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
    if df.empty or "Close" not in df.columns:
        return pd.DataFrame()

    close = df["Close"]

    # Series sicherstellen
    if isinstance(close, pd.DataFrame):
        if close.shape[1] > 0:
            close = close.iloc[:, 0]
        else:
            return pd.DataFrame()
    close = pd.to_numeric(close, errors="coerce")

    # NaNs filtern
    df = df.loc[close.notna()].copy()
    df["Close"] = close.loc[df.index]

    if len(df) < 20:
        return pd.DataFrame()

    # Indikatoren
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["rsi"] = ta.rsi(df["Close"], length=rsi_len)

    if "High" in df.columns and "Low" in df.columns:
        df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
    else:
        df["ATR"] = None

    # Signale setzen
    df["Signal"] = ""
    df.loc[df["SMA20"] > df["SMA50"], "Signal"] = "BUY"
    df.loc[df["SMA20"] < df["SMA50"], "Signal"] = "SELL"

    return df

# --- Daten laden ---
all_data = {}
for a in assets:
    st.write(f"Lade Daten für {a}…")
    df = yf.download(a, period=period)
    df = compute_signals(df)
    if df.empty:
        continue
    all_data[a] = df

# --- Signaltabelle ---
signal_rows = []

for name, df in all_data.items():
    last = df.tail(1).iloc[0]

    # CLOSE sicher extrahieren
    raw_close = last["Close"]
    if isinstance(raw_close, (pd.Series, pd.DataFrame)):
        raw_close = raw_close.squeeze()
    try:
        last_close = float(raw_close)
    except:
        last_close = None

    # ATR sicher extrahieren
    atr_val = None
    if "ATR" in df.columns:
        raw_atr = last["ATR"]
        if isinstance(raw_atr, (pd.Series, pd.DataFrame)):
            raw_atr = raw_atr.squeeze()
        try:
            atr_val = float(raw_atr)
        except:
            atr_val = None

    # Signal sicher lesen
    signal = last["Signal"] if isinstance(last["Signal"], str) else None
    if signal == "":
        signal = None

    # --- FIX: Keine bool Prüfung mehr auf Pandas-Objekten! ---
    if (
        last_close is not None
        and atr_val is not None
        and isinstance(signal, str)
    ):
        if signal == "BUY":
            stop_loss = last_close - atr_val
            take_profit = last_close + 2 * atr_val
        else:
            stop_loss = last_close + atr_val
            take_profit = last_close - 2 * atr_val

        position_size = (capital * risk_per_trade) / abs(last_close - stop_loss)
    else:
        stop_loss = take_profit = position_size = None

    signal_rows.append([
        name,
        round(last_close, 2) if last_close is not None else "N/A",
        signal if signal else "N/A",
        round(stop_loss, 2) if stop_loss is not None else "N/A",
        round(take_profit, 2) if take_profit is not None else "N/A",
        round(position_size, 4) if position_size is not None else "N/A"
    ])

# --- Tabelle anzeigen ---
st.subheader("🔍 Aktuelle Signale mit Risiko-Management")
signal_df = pd.DataFrame(signal_rows, columns=[
    "Asset", "Preis", "Signal", "Stop-Loss", "Take-Profit", "Positionsgröße"
])

def highlight_signal(row):
    if row["Signal"] == "BUY":
        return ["background-color: #b6fcd5"] * len(row)
    if row["Signal"] == "SELL":
        return ["background-color: #fcb6b6"] * len(row)
    return [""] * len(row)

st.dataframe(signal_df.style.apply(highlight_signal, axis=1))

# --- Charts ---
st.subheader("📊 Charts")
for name, df in all_data.items():
    st.write(f"### {name}")
    plot_cols = [c for c in ["Close", "SMA20", "SMA50", "rsi"] if c in df.columns]
    if plot_cols:
        st.line_chart(df[plot_cols])
