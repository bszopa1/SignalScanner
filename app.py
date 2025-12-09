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
    # Abfangen: kein Data / keine Close-Spalte
    if df is None or df.empty or 'Close' not in df.columns:
        return pd.DataFrame()

    close_data = df['Close']

    # MultiIndex / DataFrame in Series konvertieren
    if isinstance(close_data, pd.DataFrame):
        if close_data.shape[1] == 0:
            return pd.DataFrame()
        close_data = close_data.iloc[:, 0]
    elif not isinstance(close_data, pd.Series):
        close_data = pd.Series(close_data)

    # numerisch konvertieren
    close_data = pd.to_numeric(close_data, errors='coerce')

    # Nur Zeilen behalten, die gültigen Close haben
    valid_idx = close_data.notna()
    if not valid_idx.any():
        return pd.DataFrame()
    df = df.loc[valid_idx].copy()
    df['Close'] = close_data.loc[df.index]

    # Mindestens 20 Punkte für SMA20 brauchen
    if len(df) < 20:
        return pd.DataFrame()

    # Indikatoren
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)

    # ATR nur berechnen, wenn High/Low vorhanden
    if all(col in df.columns for col in ['High', 'Low']):
        # ta.atr liefert eine Series
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    else:
        df['ATR'] = pd.Series([pd.NA] * len(df), index=df.index)

    # Signale (Spaltenweise - OK)
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
    # sichere letzte Zeile
    last_row = df.tail(1)
    if last_row.empty:
        continue
    last = last_row.iloc[0]  # Serie mit Indices = Spaltennamen

    # --- last_close sicher extrahieren ---
    last_close_raw = last.get('Close', None)
    # Falls Series/DataFrame in last_close_raw -> ersten Wert nehmen
    if isinstance(last_close_raw, (pd.Series, pd.DataFrame, list, tuple)):
        try:
            last_close_raw = last_close_raw.values[0] if hasattr(last_close_raw, 'values') else last_close_raw[0]
        except Exception:
            last_close_raw = None
    try:
        last_close = float(last_close_raw) if last_close_raw is not None and not pd.isna(last_close_raw) else None
    except Exception:
        last_close = None

    # --- ATR sicher extrahieren (letzter ATR-Wert) ---
    atr_val = None
    atr_raw = last.get('ATR', None)
    if isinstance(atr_raw, (pd.Series, pd.DataFrame, list, tuple)):
        try:
            atr_raw = atr_raw.values[0] if hasattr(atr_raw, 'values') else atr_raw[0]
        except Exception:
            atr_raw = None
    if atr_raw is not None and not pd.isna(atr_raw):
        try:
            atr_val = float(atr_raw)
        except Exception:
            atr_val = None

    # --- Signal sicher extrahieren ---
    sig_raw = last.get('Signal', None)
    if isinstance(sig_raw, (pd.Series, pd.DataFrame, list, tuple)):
        try:
            sig_raw = sig_raw.values[0] if hasattr(sig_raw, 'values') else sig_raw[0]
        except Exception:
            sig_raw = None
    signal = str(sig_raw) if sig_raw is not None and not pd.isna(sig_raw) else None

    # --- Risiko-Management Berechnungen (nur wenn gültig) ---
    stop_loss = take_profit = position_size = None
    if last_close is not None and atr_val is not None and signal is not None:
        # Vermeide Division durch 0
        if signal == 'BUY':
            stop_loss = last_close - atr_val
            take_profit = last_close + 2 * atr_val
        else:  # SELL
            stop_loss = last_close + atr_val
            take_profit = last_close - 2 * atr_val

        denom = abs(last_close - stop_loss) if stop_loss is not None else None
        if denom and denom > 1e-12:
            position_size = (capital * risk_per_trade) / denom
        else:
            position_size = None

    signal_rows.append([
        name,
        round(last_close, 2) if last_close is not None else 'N/A',
        signal if signal is not None else 'N/A',
        round(stop_loss, 2) if stop_loss is not None else 'N/A',
        round(take_profit, 2) if take_profit is not None else 'N/A',
        round(position_size, 8) if position_size is not None else 'N/A'  # 8 Dez. bei Krypto praktisch
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
    columns_to_plot = [col for col in ['Close', 'SMA20', 'SMA50', 'rsi'] if col in df.columns]
    if columns_to_plot:
        st.line_chart(df[columns_to_plot])
