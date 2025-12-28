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

period = st.selectbox("Zeitraum:", ["3mo", "6mo", "1y", "2y"], index=2)

st.write("---")

# ---------------- FUNCTIONS ----------------
def load_data(symbol):
    st.write(f"Lade Daten für {symbol}…")
    df = yf.download(symbol, period=period, interval="1d", auto_adjust=True)

    if df is None or df.empty:
        return None

    df.reset_index(inplace=True)

    # ensure required columns exist
    needed = ["Date", "Close", "High", "Low"]
    if any(col not in df.columns for col in needed):
        return None

    # numeric safety
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df["High"] = pd.to_numeric(df["High"], errors="coerce")
    df["Low"] = pd.to_numeric(df["Low"], errors="coerce")

    df.dropna(subset=["Close"], inplace=True)
    return df


def compute_signals(df):
    if df is None or len(df) < 50:
        return None

    df["SMA20"] = df["Close"].rolling(window=20).mean()
    df["SMA50"] = df["Close"].rolling(window=50).mean()

    df["Signal"] = "HOLD"
    df.loc[df["SMA20"] > df["SMA50"], "Signal"] = "BUY"
    df.loc[df["SMA20"] < df["SMA50"], "Signal"] = "SELL"

    # letzte Zeile
    last = df.iloc[-1]

    entry_price = last["Close"]
    stop_loss = last["Low"] * 0.98
    risk = entry_price - stop_loss if stop_loss else None

    position_size = 0
    if risk and risk > 0:
        risk_amount = capital * (risk_percent / 100)
        position_size = risk_amount / risk

    return {
        "last_close": round(entry_price, 2),
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
    st.write("❌ Keine gültigen Daten gefunden.")

st.subheader("📊 Charts")

for asset, df in charts.items():
    st.write(f"### {asset}")

    plot_df = df[["Date", "Close", "SMA20", "SMA50"]].set_index("Date")
    st.line_chart(plot_df)
