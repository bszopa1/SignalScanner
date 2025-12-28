import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.title("📈 SignalScanner – Krypto & US-Aktien Signale mit Risiko-Management")

# =============================
# Kapital / Risiko
# =============================
capital = st.number_input("Kapital in USD:", value=1000, step=100)
risk_per_trade = st.slider("Max Risiko pro Trade (%):", 0.5, 10.0, 2.0) / 100

# =============================
# Asset Auswahl
# =============================
assets = st.multiselect(
    "Wähle die Assets aus:",
    ["BTC-USD","ETH-USD","XRP-USD","AAPL","TSLA","NVDA","MSFT","AMZN"],
    default=["BTC-USD","ETH-USD","XRP-USD","AAPL","TSLA"]
)

period = st.selectbox("Zeitraum:", ["1mo","3mo","6mo","1y","2y","5y","max"], index=3)


# =============================
# Signalberechnung
# =============================
def compute_signals(df):
    if df is None or df.empty or "Close" not in df.columns:
        return pd.DataFrame()

    df = df.copy()

    # Close sicher stellen
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna(subset=["Close"])

    if len(df) < 50:
        return pd.DataFrame()

    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["rsi"] = ta.rsi(df["Close"], length=14)

    if all(col in df.columns for col in ["High","Low"]):
        df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
    else:
        df["ATR"] = pd.NA

    df["Signal"] = ""
    df.loc[df["SMA20"] > df["SMA50"], "Signal"] = "BUY"
    df.loc[df["SMA20"] < df["SMA50"], "Signal"] = "SELL"

    return df


# =============================
# Daten laden
# =============================
all_data = {}

for a in assets:
    st.write(f"Lade Daten für {a}…")
    raw = yf.download(a, period=period)
    df = compute_signals(raw)

    if df.empty:
        st.write(f" → Keine ausreichenden Daten für {a}")
        continue

    all_data[a] = df


# =============================
# Signaltabelle
# =============================
signal_rows = []

for name, df in all_data.items():
    last = df.tail(1)

    if last.empty:
        continue

    last = last.iloc[0]

    price = float(last["Close"])
    atr = None if pd.isna(last["ATR"]) else float(last["ATR"])
    signal = last["Signal"]

    stop_loss = take_profit = position_size = "N/A"

    if atr and signal in ["BUY","SELL"]:
        if signal == "BUY":
            stop_loss = price - atr
            take_profit = price + 2 * atr
        else:
            stop_loss = price + atr
            take_profit = price - 2 * atr

        risk_per_unit = abs(price - stop_loss)
        if risk_per_unit > 0:
            position_size = (capital * risk_per_trade) / risk_per_unit

    signal_rows.append([
        name,
        round(price, 2),
        signal if signal else "N/A",
        round(stop_loss, 2) if stop_loss != "N/A" else "N/A",
        round(take_profit, 2) if take_profit != "N/A" else "N/A",
        round(position_size, 8) if position_size != "N/A" else "N/A"
    ])

st.subheader("🔍 Aktuelle Signale mit Risiko-Management")
signal_df = pd.DataFrame(signal_rows,
    columns=["Asset","Preis","Signal","Stop-Loss","Take-Profit","Positionsgröße"]
)

def highlight_signal(row):
    if row["Signal"] == "BUY":
        return ["background-color:#b6fcd5"]*len(row)
    elif row["Signal"] == "SELL":
        return ["background-color:#fcb6b6"]*len(row)
    return [""]*len(row)

st.dataframe(signal_df.style.apply(highlight_signal, axis=1))


# =============================
# CHARTS (jetzt fehlerfrei)
# =============================
st.subheader("📊 Charts")

for name, df in all_data.items():
    st.write(f"### {name}")

    # MultiIndex fix
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join([c for c in col if c]).strip() for col in df.columns]

    # passende Spalten suchen
    close_col = next((c for c in df.columns if "Close" in c), None)
    sma20 = next((c for c in df.columns if "SMA20" in c), None)
    sma50 = next((c for c in df.columns if "SMA50" in c), None)

    cols = [c for c in [close_col, sma20, sma50] if c]
    chart_df = df[cols].copy()

    rename_map = {}
    if close_col: rename_map[close_col] = "Close"
    if sma20: rename_map[sma20] = "SMA20"
    if sma50: rename_map[sma50] = "SMA50"

    chart_df.rename(columns=rename_map, inplace=True)

    st.line_chart(chart_df)
