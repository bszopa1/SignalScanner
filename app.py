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

    # Close sichern
    close_data = df['Close']
    if isinstance(close_data, pd.DataFrame) and close_data.shape[1] > 0:
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

    # Indikatoren
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)

    # ATR nur berechnen, wenn High/Low vorhanden
    if all(col in df.columns for col in ['High', 'Low']):
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    else:
        df['ATR'] = pd.Series([pd.NA] * len(df), index=df.index)

    # Signale nur wenn SMA20 & SMA50 vorhanden
    df['Signal'] = ''
    mask_buy = df['SMA20'].notna() & df['SMA50'].notna() & (df['SMA20'] > df['SMA50'])
    mask_sell = df['SMA20'].notna() & df['SMA50'].notna() & (df['SMA20'] < df['SMA50'])
    df.loc[mask_buy, 'Signal'] = 'BUY'
    df.loc[mask_sell, 'Signal'] = 'SELL'

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

    # --- Close ---
    last_close = last['Close'] if not pd.isna(last['Close']) else None

    # --- ATR ---
    atr_val = None
    if 'ATR' in last and not pd.isna(last['ATR']):
        atr_val = last['ATR']

    # --- Signal ---
    signal = last['Signal'] if last['Signal'] else None

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
        round(last_close, 2) if last_close else 'N/A',
        signal if signal else 'N/A',
        round(stop_loss, 2) if stop_loss else 'N/A',
        round(take_profit, 2) if take_profit else 'N/A',
        round(position_size, 8) if position_size else 'N/A'
    ])

# --- Signaltabelle anzeigen ---
st.subheader('🔍 Aktuelle Signale mit Risiko-Management')
signal_df = pd.DataFrame(signal_rows, columns=['Asset', 'Preis', 'Signal', 'Stop-Loss', 'Take-Profit', 'Positionsgröße'])

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
