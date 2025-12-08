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
        return pd.DataFrame()

    close_col = df['Close']
    if isinstance(close_col, pd.DataFrame):
        close_col = close_col.iloc[:, 0]

    close_col = pd.to_numeric(close_col, errors='coerce')
    df = df.loc[close_col.notna()].copy()
    if df.empty:
        return pd.DataFrame()
    df['Close'] = close_col[close_col.notna()]

    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)

    df['Signal'] = ''

    for pos in range(len(df)):
        close_val = df['Close'].iloc[pos]
        sma20_val = df['SMA20'].iloc[pos] if not pd.isna(df['SMA20'].iloc[pos]) else None
        sma50_val = df['SMA50'].iloc[pos] if 'SMA50' in df.columns and not pd.isna(df['SMA50'].iloc[pos]) else None
        rsi_val = df['rsi'].iloc[pos] if 'rsi' in df.columns else None

        # --- Kurzfrist (weniger als 50 Datenpunkte oder SMA50 fehlt)
        if len(df) < 50 or sma50_val is None:
            if sma20_val is not None:
                if close_val > sma20_val:
                    df.iloc[pos, df.columns.get_loc('Signal')] = 'BUY (Short)'
                else:
                    df.iloc[pos, df.columns.get_loc('Signal')] = 'SELL (Short)'

        # --- Langfrist (50+ Datenpunkte, SMA50 vorhanden)
        else:
            if sma20_val is not None and sma50_val is not None:
                if sma20_val > sma50_val:
                    df.iloc[pos, df.columns.get_loc('Signal')] = 'BUY (RSI ok)' if rsi_val is not None and rsi_val < 70 else 'BUY (RSI hoch)'
                elif sma20_val < sma50_val:
                    df.iloc[pos, df.columns.get_loc('Signal')] = 'SELL (RSI ok)' if rsi_val is not None and rsi_val > 30 else 'SELL (RSI niedrig)'

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
    
    # MultiIndex abflachen
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Nur existierende, numerische Spalten plotten
    possible_cols = ['Close', 'SMA20', 'SMA50', 'rsi']
    columns_to_plot = [
        col for col in possible_cols
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]) and df[col].notna().any()
    ]
    
    if columns_to_plot:
        st.line_chart(df[columns_to_plot])
    else:
        st.write("Keine plottbaren Daten verfügbar.")
