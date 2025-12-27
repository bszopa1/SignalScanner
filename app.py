import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.title("📈 SignalScanner – Krypto & US-Aktien Signale mit Risiko-Management")

# --- Kapital & Risiko ---
capital = st.number_input("Kapital in USD:", value=1000, step=100)
risk_per_trade = st.slider("Max Risiko pro Trade (%):", 0.5, 10.0, 2.0) / 100

# --- Assets ---
assets = st.multiselect(
    "Wähle Assets:",
    [
        "BTC-USD","ETH-USD","XRP-USD",
        "AAPL","TSLA","NVDA","MSFT","AMZN"
    ],
    default=["BTC-USD","ETH-USD","XRP-USD","AAPL","TSLA"]
)

# --- Zeitraum ---
period = st.selectbox("Zeitraum:",
                      ["1mo","3mo","6mo","1y","2y","5y","max"],
                      index=3)

# ---------------- SIGNAL FUNKTION ----------------
def compute_signals(df):
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Minimum Data
    if len(df) < 50:
        return pd.DataFrame()

    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["rsi"] = ta.rsi(df["Close"], length=14)

    if all(x in df.columns for x in ["High","Low","Close"]):
        df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
    else:
        df["ATR"] = pd.NA

    df["Signal"] = "N/A"
    df.loc[df["SMA20"] > df["SMA50"], "Signal"] = "BUY"
    df.loc[df["SMA20"] < df["SMA50"], "Signal"] = "SELL"

    return df


# ---------------- DATEN LADEN ----------------
all_data = {}
for a in assets:
    st.write(f"Lade Daten für {a} …")
    df = yf.download(a, period=period)

    if df.empty:
        st.write(f"⚠️ Keine Daten für {a}")
        continue

    df = compute_signals(df)

    if df.empty:
        st.write(f"⚠️ Zu wenige Daten für {a}")
        continue

    all_data[a] = df


# ---------------- SIGNAL TABELLE ----------------
signal_rows = []

for name, df in all_data.items():
    last = df.iloc[-1]

    close = float(last["Close"])
    atr = last["ATR"]

    signal = last["Signal"]
    if pd.isna(signal) or signal == "N/A":
        signal = None

    stop_loss = take_profit = position_size = None

    if signal and not pd.isna(atr):
        atr = float(atr)

        if signal == "BUY":
            stop_loss = close - atr
            take_profit = close + 2*atr
        else:
            stop_loss = close + atr
            take_profit = close - 2*atr

        risk = abs(close - stop_loss)
        if risk > 0:
            position_size = (capital * risk_per_trade) / risk

    signal_rows.append([
        name,
        round(close,2),
        signal if signal else "N/A",
        round(stop_loss,2) if stop_loss else "N/A",
        round(take_profit,2) if take_profit else "N/A",
        round(position_size,6) if position_size else "N/A"
    ])

st.subheader("🔍 Aktuelle Signale")
signal_df = pd.DataFrame(signal_rows,
                         columns=["Asset","Preis","Signal","Stop-Loss","Take-Profit","Positionsgröße"])

def highlight(row):
    if row["Signal"] == "BUY":
        return ["background-color:#b6fcd5"] * len(row)
    if row["Signal"] == "SELL":
        return ["background-color:#fcb6b6"] * len(row)
    return [""] * len(row)

st.dataframe(signal_df.style.apply(highlight, axis=1))


# ---------------- CHARTS ----------------
st.subheader("📊 Charts")
for name, df in all_data.items():
    st.write(f"### {name}")
    st.line_chart(df[["Close","SMA20","SMA50"]])
