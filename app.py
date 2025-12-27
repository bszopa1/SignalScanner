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
period = st.selectbox("Zeitraum:", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)

# --- Signale berechnen ---
def compute_signals(df, rsi_len=14):
    if df is None or df.empty or 'Close' not in df.columns:
        return pd.DataFrame()
    
    close_data = df['Close']
    if isinstance(close_data, pd.DataFrame) and close_data.shape[1] > 0:
        close_data = close_data.iloc[:, 0]
    elif not isinstance(close_data, pd.Series):
        close_data = pd.Series(close_data)
    
    close_data = pd.to_numeric(close_data, errors='coerce')
    df = df.loc[close_data.notna()].copy()
    df['Close'] = close_data.loc[df.index]
    
    if len(df) < 20:
        return pd.DataFrame()
    
    # SMA & RSI
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)
    
    # ATR
    if all(col in df.columns for col in ['High', 'Low']):
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    else:
        df['ATR'] = pd.Series([pd.NA] * len(df), index=df.index)
    
    # Signale
    df['Signal'] = ''
    df.loc[df['SMA20'] > df['SMA50'], 'Signal'] = 'BUY'
    df.loc[df['SMA20'] < df['SMA50'], 'Signal'] = 'SELL'
    
    return df

# --- Daten laden ---
all_data = {}
for asset in assets:
    st.write(f"Lade Daten für {asset}…")
    df = yf.download(asset, period=period)
    df = compute_signals(df)
    if df.empty:
        st.write(f"  → Keine ausreichenden Daten für {asset} (übersprungen).")
        continue
    all_data[asset] = df

# --- Signaltabelle mit Risiko ---
signal_rows = []
for name, df in all_data.items():
    last_row = df.tail(1)
    if last_row.empty:
        continue
    last = last_row.iloc[0]

    # --- last_close extrahieren ---
    last_close = last['Close']
    if isinstance(last_close, (pd.Series, pd.DataFrame)):
        last_close = last_close.iloc[0]
    last_close = float(last_close) if last_close is not None and not pd.isna(last_close) else None

    # --- ATR extrahieren ---
    atr_val = last.get('ATR', None)
    if isinstance(atr_val, (pd.Series, pd.DataFrame)):
        atr_val = atr_val.iloc[0]
    atr_val = float(atr_val) if atr_val is not None and not pd.isna(atr_val) else None

    # --- Signal extrahieren ---
    signal = last.get('Signal', None)
    if isinstance(signal, (pd.Series, pd.DataFrame)):
        signal = signal.iloc[0]
    signal = str(signal) if signal is not None and not pd.isna(signal) else None

    # --- Risiko-Management Berechnungen ---
    stop_loss = take_profit = position_size = None
    if last_close is not None and atr_val is not None and signal is not None:
        if signal == 'BUY':
            stop_loss = last_close - atr_val
            take_profit = last_close + 2 * atr_val
        else:
            stop_loss = last_close + atr_val
            take_profit = last_close - 2 * atr_val

        denom = abs(last_close - stop_loss)
        if denom > 1e-12:
            position_size = (capital * risk_per_trade) / denom

    signal_rows.append([
        name,
        round(last_close, 2) if last_close is not None else 'N/A',
        signal if signal is not None else 'N/A',
        round(stop_loss, 2) if stop_loss is not None else 'N/A',
        round(take_profit, 2) if take_profit is not None else 'N/A',
        round(position_size, 8) if position_size is not None else 'N/A'
    ])

# --- Signaltabelle anzeigen ---
st.subheader('🔍 Aktuelle Signale mit Risiko-Management')
signal_df = pd.DataFrame(signal_rows, columns=[
    'Asset', 'Preis', 'Signal', 'Stop-Loss', 'Take-Profit', 'Positionsgröße'
])

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
    columns_to_plot = [col for col in ['Close', 'SMA20', 'SMA50', 'rsi'] if col in df.columns]
    if columns_to_plot:
        st.line_chart(df[columns_to_plot])
