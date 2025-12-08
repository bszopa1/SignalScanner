import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.title("📈 SignalScanner – Krypto & US-Aktien Signale")

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

# --- Cache für Daten ---
@st.cache_data
def load_data(ticker, period):
    df = yf.download(ticker, period=period)
    return df

# --- Funktion für Signale ---
def compute_signals(df, rsi_len=14):
    if 'Close' not in df.columns:
        return pd.DataFrame()  # Keine Close-Spalte vorhanden

    # Close-Spalte extrahieren
    close_col = df['Close']
    if isinstance(close_col, pd.DataFrame):
        close_col = close_col.iloc[:, 0]

    # In numeric umwandeln
    close_col = pd.to_numeric(close_col, errors='coerce')

    # Nur gültige Werte behalten
    valid_idx = close_col.notna()
    if valid_idx.sum() == 0:
        return pd.DataFrame()  # keine gültigen Werte vorhanden

    df = df.loc[valid_idx].copy()
    df['Close'] = close_col[valid_idx]

    # SMA
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()

    # RSI
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)

    # Signale
    df['Signal'] = ''
    df.loc[df['SMA20'] > df['SMA50'], 'Signal'] = 'BUY'
    df.loc[df['SMA20'] < df['SMA50'], 'Signal'] = 'SELL'

    return df

# --- Daten laden & Fortschritt anzeigen ---
all_data = {}
for a in assets:
    st.write(f"Lade Daten für {a}…")
    df = load_data(a, period)
    if df.empty:
        st.write(f"Keine Daten für {a} verfügbar.")
        continue
    df = compute_signals(df)
    if df.empty:
        st.write(f"Keine validen Close-Daten für {a}.")
        continue
    all_data[a] = df

# --- Signaltabelle ---
signal_rows = []
for name, df in all_data.items():
    last = df.tail(1).iloc[0]
    try:
        last_close = float(last['Close'])
    except (ValueError, TypeError):
        last_close = None
    signal_rows.append([
        name,
        round(last_close, 2) if last_close is not None else 'N/A',
        last['Signal']
    ])

st.subheader('🔍 Aktuelle Signale')
signal_df = pd.DataFrame(signal_rows, columns=['Asset', 'Preis', 'Signal'])
st.dataframe(signal_df)

# --- Charts ---
st.subheader('📊 Charts')
for name, df in all_data.items():
    st.write(f'### {name}')
    
    # MultiIndex-Spalten abflachen
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Nur existierende, numerische Spalten mit mindestens einem Wert plotten
    possible_cols = ['Close', 'SMA20', 'SMA50', 'rsi']
    columns_to_plot = [
        col for col in possible_cols
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]) and df[col].notna().any()
    ]
    
    if columns_to_plot:
        st.line_chart(df[columns_to_plot])
    else:
        st.write("Keine plottbaren Daten verfügbar.")
