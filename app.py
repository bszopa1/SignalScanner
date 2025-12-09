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

    close_data = df['Close']

    if isinstance(close_data, pd.DataFrame):
        if close_data.shape[1] == 0:
            return pd.DataFrame()
        close_data = close_data.iloc[:, 0]
    elif not isinstance(close_data, pd.Series):
        close_data = pd.Series(close_data)

    close_data = pd.to_numeric(close_data, errors='coerce')

    valid_idx = close_data.notna()
    if not valid_idx.any():
        return pd.DataFrame()

    df = df.loc[valid_idx].copy()
    df['Close'] = close_data.loc[df.index]

    if len(df) < 20:
        return pd.DataFrame()

    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)

    if all(col in df.columns for col in ['High', 'Low']):
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    else:
        df['ATR'] = pd.Series([pd.NA] * len(df), index=df.index)

    df['Signal'] = ''
    df.loc[df['SMA20'] > df['SMA50'], 'Signal'] = 'BUY'
    df.loc[df['SMA20'] < df['SMA50'], 'Signal'] = 'SELL'

    return df

# --- Daten laden ---
all_data = {}
for a in assets:
    st.write(f"Lade Daten für {a}…")
    raw = yf.download(a, period=period)
    df = compute_signals(raw)
    if df.empty:
        st.write(f"  → Keine ausreichenden Daten für {a} (übersprungen).")
        continue
    all_data[a] = df

# --- Signaltabelle mit Risiko ---
signal_rows = []
for name, df in all_data.items():

    last_row = df.tail(1)
    if last_row.empty:
        continue
    last = last_row.iloc[0]

    # Close
    last_close_raw = last.get('Close', None)
    if isinstance(last_close_raw, (pd.Series, pd.DataFrame, list, tuple)):
        try:
            last_close_raw = last_close_raw.values[0] if hasattr(last_close_raw, "values") else last_close_raw[0]
        except:
            last_close_raw = None

    try:
        last_close = float(last_close_raw) if last_close_raw is not None and not pd.isna(last_close_raw) else None
    except:
        last_close = None

    # ATR
    atr_raw = last.get("ATR", None)
    if isinstance(atr_raw, (pd.Series, pd.DataFrame, list, tuple)):
        try:
            atr_raw = atr_raw.values[0] if hasattr(atr_raw, 'values') else atr_raw[0]
        except:
            atr_raw = None

    try:
        atr_val = float(atr_raw) if atr_raw is not None and not pd.isna(atr_raw) else None
    except:
        atr_val = None

    # Signal
    sig_raw = last.get("Signal", None)
    if isinstance(sig_raw, (pd.Series, pd.DataFrame, list, tuple)):
        try:
            sig_raw = sig_raw.values[0] if hasattr(sig_raw, 'values') else sig_raw[0]
        except:
            sig_raw = None

    signal = str(sig_raw) if sig_raw is not None and not pd.isna(sig_raw) else None

    # --- Risiko-Berechnung ---
    stop_loss = take_profit = position_size = None

    if last_close is not None and atr_val is not None and isinstance(signal, str):

        if signal == "BUY":
            stop_loss = last_close - atr_val
            take_profit = last_close + 2 * atr_val
        elif signal == "SELL":
            stop_loss = last_close + atr_val
            take_profit = last_close - 2 * atr_val

        denom = abs(last_close - stop_loss) if stop_loss is not None else None
        if denom is not None and denom > 0:
            position_size = (capital * risk_per_trade) / denom

    signal_rows.append([
        name,
        round(last_close, 2) if last_close is not None else "N/A",
        signal if signal is not None else "N/A",
        round(stop_loss, 2) if stop_loss is not None else "N/A",
        round(take_profit, 2) if take_profit is not None else "N/A",
        round(position_size, 8) if position_size is not None else "N/A"
    ])

# --- Anzeige ---
st.subheader("🔍 Aktuelle Signale mit Risiko-Management")
signal_df = pd.DataFrame(signal_rows, columns=[
    "Asset", "Preis", "Signal", "Stop-Loss", "Take-Profit", "Positionsgröße"
])

def highlight_signal(row):
    if row["Signal"] == "BUY":
        return ['background-color: #b6fcd5'] * len(row)
    elif row["Signal"] == "SELL":
        return ['background-color: #fcb6b6'] * len(row)
    return [''] * len(row)

st.dataframe(signal_df.style.apply(highlight_signal, axis=1))

# --- Charts ---
st.subheader("📊 Charts")
for name, df in all_data.items():
    st.write(f"### {name}")
    cols = [c for c in ["Close", "SMA20", "SMA50", "rsi"] if c in df.columns]
    if cols:
        st.line_chart(df[cols])
