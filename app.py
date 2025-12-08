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
    # Prüfen, ob 'Close' existiert und Daten hat
    if 'Close' not in df.columns or df['Close'].empty:
        return df

    # MultiIndex oder DataFrame abfangen
    close_data = df['Close']
    if isinstance(close_data, pd.DataFrame):
        close_data = close_data.iloc[:, 0]  # erste Spalte nehmen

    # In Series umwandeln, falls nötig
    if not isinstance(close_data, pd.Series):
        close_data = pd.Series(close_data)

    # In numerisch konvertieren
    df['Close'] = pd.to_numeric(close_data, errors='coerce')
    df = df.dropna(subset=['Close'])

    # Frühzeitig abbrechen, wenn zu kurz für SMA/ATR
    if len(df) < 20:
        return df

    # SMA
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()

    # RSI
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)

    # ATR
    if 'High' in df.columns and 'Low' in df.columns:
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    else:
        df['ATR'] = None

    # Signale
    df['Signal'] = ''
    df.loc[df['SMA20'] > df['SMA50'], 'Signal'] = 'BUY'
    df.loc[df['SMA20'] < df['SMA50'], 'Signal'] = 'SELL'

    return df

# --- Daten laden ---
all_data = {}
for a in assets:
    st.write(f"Lade Daten für {a}…")
    df = yf.download(a, period=period)
    if df.empty or 'Close' not in df.columns:
        continue
    df = compute_signals(df)
    if df.empty:
        continue
    all_data[a] = df

# --- Signaltabelle mit Risiko ---
signal_rows = []
for name, df in all_data.items():
    last = df.tail(1).iloc[0]

    last_close = last['Close'] if pd.notna(last['Close']) else None
    atr = last['ATR'] if 'ATR' in last and pd.notna(last['ATR']) else None
    signal = last['Signal'] if last['Signal'] else None

    if last_close and atr and signal:
        if signal == 'BUY':
            stop_loss = last_close - atr
            take_profit = last_close + 2 * atr
        else:  # SELL / Short
            stop_loss = last_close + atr
            take_profit = last_close - 2 * atr

        position_size = (capital * risk_per_trade) / abs(last_close - stop_loss)
    else:
        stop_loss = take_profit = position_size = None

    signal_rows.append([
        name,
        round(last_close, 2) if last_close else 'N/A',
        signal if signal else 'N/A',
        round(stop_loss, 2) if stop_loss else 'N/A',
        round(take_profit, 2) if take_profit else 'N/A',
        round(position_size, 4) if position_size else 'N/A'
    ])

# --- Signaltabelle anzeigen ---
st.subheader('🔍 Aktuelle Signale mit Risiko-Management')
signal_df = pd.DataFrame(signal_rows, columns=[
    'Asset', 'Preis', 'Signal', 'Stop-Loss', 'Take-Profit', 'Positionsgröße'
])
st.dataframe(signal_df)

# --- Charts ---
st.subheader('📊 Charts')
for name, df in all_data.items():
    st.write(f'### {name}')
    columns_to_plot = [col for col in ['Close', 'SMA20', 'SMA50', 'rsi'] if col in df.columns]
    if columns_to_plot:
        st.line_chart(df[columns_to_plot])
