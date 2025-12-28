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
    options=["BTC-USD", "ETH-USD", "XRP-USD", "AAPL", "TSLA", "NVDA", "MSFT", "AMZN"],
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

    # SMA20 & SMA50
    df['SMA20'] = df['Close'].rolling(20, min_periods=20).mean()
    df['SMA50'] = df['Close'].rolling(50, min_periods=50).mean()

    # RSI
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)

    # ATR
    if all(col in df.columns for col in ['High', 'Low']):
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    else:
        df['ATR'] = pd.Series([pd.NA] * len(df), index=df.index)

    # Signale nur setzen, wenn SMA20 und SMA50 gültig sind
    df['Signal'] = ''
    valid_idx = df['SMA20'].notna() & df['SMA50'].notna()
    df.loc[valid_idx & (df['SMA20'] > df['SMA50']), 'Signal'] = 'BUY'
    df.loc[valid_idx & (df['SMA20'] < df['SMA50']), 'Signal'] = 'SELL'

    return df

# --- Daten laden ---
all_data = {}
for asset in assets:
    st.write(f"Lade Daten für {asset}…")
    raw = yf.download(asset, period=period)
    df = compute_signals(raw)
    if df.empty:
        st.write(f"  → Keine ausreichenden Daten für {asset} (übersprungen).")
        continue
    all_data[asset] = df

# --- Signaltabelle mit Risiko ---
signal_rows = []
for name, df in all_data.items():
    # letzte gültige Zeile
    last_valid = df.dropna(subset=['Close', 'SMA20', 'SMA50']).tail(1)
    if last_valid.empty:
        continue
    last = last_valid.iloc[0]

    last_close = float(last['Close'])
    atr_val = float(last['ATR']) if not pd.isna(last['ATR']) else None
    signal = str(last['Signal']) if last['Signal'] else None

    stop_loss = take_profit = position_size = None
    if last_close is not None and atr_val is not None and signal is not None:
        if signal == 'BUY':
            stop_loss = last_close - atr_val
            take_profit = last_close + 2 * atr_val
        elif signal == 'SELL':
            stop_loss = last_close + atr_val
            take_profit = last_close - 2 * atr_val

        denom = abs(last_close - stop_loss) if stop_loss is not None else None
        if denom and denom > 1e-12:
            position_size = (capital * risk_per_trade) / denom

    signal_rows.append([
        name,
        round(last_close, 2),
        signal if signal else 'N/A',
        round(stop_loss, 2) if stop_loss else 'N/A',
        round(take_profit, 2) if take_profit else 'N/A',
        round(position_size, 8) if position_size else 'N/A'
    ])

# --- Signaltabelle anzeigen ---
st.subheader('🔍 Aktuelle Signale mit Risiko-Management')
signal_df = pd.DataFrame(signal_rows, columns=[
    'Asset', 'Preis', 'Signal', 'Stop-Loss', 'Take-Profit', 'Positionsgröße'
])

# Farbliche Hervorhebung
def highlight_signal(row):
    color = ''
    if row['Signal'] == 'BUY':
        color = 'background-color: #b6fcd5'
    elif row['Signal'] == 'SELL':
        color = 'background-color: #fcb6b6'
    return [color]*len(row)

st.dataframe(signal_df.style.apply(highlight_signal, axis=1))

# --- Charts ---
st.subheader('📊 Charts')
for name, df in all_data.items():
    st.write(f'### {name}')
    columns_to_plot = [col for col in ['Close', 'SMA20', 'SMA50', 'rsi'] if col in df.columns and df[col].notna().any()]
    if columns_to_plot:
        st.line_chart(df[columns_to_plot])
