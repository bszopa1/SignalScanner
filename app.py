import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="SignalScanner", layout="wide")

st.title("📈 SignalScanner – Krypto & US-Aktien Signale mit Risiko-Management")

# ---------------- UI ----------------
capital = st.number_input("Kapital in USD:", min_value=1.0, value=1000.0, step=100.0)
risk_percent = st.slider("Max Risiko pro Trade (%):", 0.5, 10.0, 1.0)

assets = st.multiselect(
    "Wähle die Assets aus:",
    ["BTC-USD", "ETH-USD", "XRP-USD", "AAPL", "TSLA"],
    default=["BTC-USD", "ETH-USD"]
)

period = st.selectbox("Zeitraum:", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)

st.write("---")

# ---------------- FUNCTIONS ----------------
def load_data(symbol):
    st.write(f"Lade Daten für {symbol}…")
    df = yf.download(symbol, period=period, interval="1d", auto_adjust=True)

    if df is None or df.empty:
        return None

    df.reset_index(inplace=True)

    for col in ["Close", "High", "Low"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.dropna(subset=["Close"], inplace=True)
    return df


def compute_signals(df):
    if df is None or len(df) < 10:
        return None

    # Dynamische Perioden
    if len(df) >= 50:
        fast = 20
        slow = 50
    else:
        fast = max(5, len(df)//4)
        slow = max(10, len(df)//2)

    df["SMA_fast"] = df["Close"].rolling(window=fast).mean()
    df["SMA_slow"] = df["Close"].rolling(window=slow).mean()

    df["Signal"] = "HOLD"
    df.loc[df["SMA_fast"] > df["SMA_slow"], "Signal"] = "BUY"
    df.loc[df["SMA_fast"] < df["SMA_slow"], "Signal"] = "SELL"

    last = df.iloc[-1]

    entry = last["Close"]
    stop_loss = last["Low"] * 0.98
    risk = entry - stop_loss

    position_size = 0
    if risk > 0:
        risk_amount = capital * (risk_percent / 100)
        position_size = risk_amount / risk

    return {
        "last_close": round(entry, 2),
        "signal": last["Signal"],
        "stop_loss": round(stop_loss, 2),
        "position_size": round(position_size, 2),
        "df": df
    }


# ---------------- MAIN ----------------
results = []
charts = {}

for asset in assets:
    df = load_data(asset)
    res = compute_signals(df)

    if res:
        results.append({
            "Asset": asset,
            "Preis": res["last_close"],
            "Signal": res["signal"],
            "Stop Loss": res["stop_loss"],
            "Positionsgröße": res["position_size"]
        })
        charts[asset] = res["df"]

# ---------------- OUTPUT ----------------
st.subheader("🔍 Aktuelle Signale mit Risiko-Management")

if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True)
else:
    st.write("❌ Keine ausreichenden Daten verfügbar.")

st.subheader("📊 Charts")

for asset, df in charts.items():
    st.write(f"### {asset}")
    chart = df[["Date", "Close", "SMA_fast", "SMA_slow"]].set_index("Date")
    st.line_chart(chart)
