import streamlit as st
import yfinance as yf
import pandas as pd

# --- App Title ---
st.title("📈 SignalScanner – Krypto & US-Aktien Signale")

# --- Asset Auswahl ---
assets = st.multiselect(
    "Wähle die Assets aus:",
    options=[
        'BTC-USD', 'ETH-USD', 'XRP-USD',
        'AAPL', 'TSLA', 'NVDA', 'MSFT', 'AMZN'
    ],
    default=['BTC-USD', 'ETH-USD', 'XRP-USD', 'AAPL', 'TSLA']
)

# --- Zeitraum ---
period = st.selectbox(
    "Zeitraum:",
    ['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'],
    index=3
)

# --- Funktion für Signale ---
def compute_signals(df):
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()

    df["Signal"] = ""
    df.loc[df["SMA20"] > df["SMA50"], "Signal"] = "BUY"
    df.loc[df["SMA20"] < df["SMA50"], "Signal"] = "SELL"

    return df

# --- Daten laden ---
all_data = {}
for a in assets:
    df = yf.download(a, period=period)
    if df.empty or 'Close' not in df.columns:
        continue
    df = compute_signals(df)
    all_data[a] = df

# --- Signaltabelle ---
signal_rows = []
for name, df in all_data.items():
    last = df.tail(1).iloc[0]
    try:
        last_close = float(last["Close"])
    except (ValueError, TypeError):
        last_close = None
    signal_rows.append([
        name,
        round(last_close, 2) if last_close is not None else "N/A",
        last["Signal"]
    ])

st.subheader("🔍 Aktuelle Signale")
signal_df = pd.DataFrame(signal_rows, columns=["Asset", "Preis", "Signal"])
st.dataframe(signal_df)

# --- Charts ---
st.subheader("📊 Charts")
for name, df in all_data.items():
    st.write(f"### {name}")
    st.line_chart(df[["Close", "SMA20", "SMA50"]])
импортируйте стримит как ст
импорт yfinance как yf
импортируйте панд как pd

# -- Название приложения ---
st.title ("📈 SignalScanner - Крипто и US-Aktien Signale")

# --- Актив Аусваль --
активы = st.multiselect(
"Wähle die Assets aus:",
options=[
«BTC-USD», «ETH-USD», «XRP-USD»,
«AAPL», «TSLA», «NVDA», «MSFT», «AMZN»
],
default=['BTC-USD', 'ETH-USD', 'XRP-USD', 'AAPL', 'TSLA']
)

# -- Зейтраум --
период = st.selectbox(
"Zeitraum:",
['1mo', '3mo', '6mo', '1y', '2y', '5y', 'макс'],
индекс=3
)

# -- Funktion für Signale --
def compute_signals(df):
df["SMA20"] = df["Закрыть"].rolling(20).mean()
df["SMA50"] = df["Закрыть"].rolling(50).mean()

df["Сигнал"] = ""
df.loc[df["SMA20"] > df["SMA50"], "Сигнал"] = "КУПИТЬ"
df.loc[df["SMA20"] <df["SMA50"], "Сигнал"] = "Продажа"

верни дф

# --- Датен Ладен --
all_data = {}
для активов a:
df = yf.download(a, период=период)
если df.empty или «Закрыть» нет в df.columns:
продолжайте
df = compute_signals(df)
all_data[a] = df

# --- Сигнальтабель --
signal_rows = []
Для имени, df в all_data.items():
last = df.tail(1).iloc[0]
Попробуйте:
last_close =float(last["Close"])
за исключением (ValueError, TypeError):
last_close = Нет
signal_rows.append([[
Имя,
Round(last_close, 2) если last_close не является No больше "N/A",
последний["Сигнал"]
])

st.subheader ("🔍 Aktuelle Signale")
signal_df = pd. DataFrame(signal_rows, столбцы=["Актив", "Прейс", "Сигнал"])
st.dataframe(signal_df)

# --- Графики ---
st.subheader ("📊 диаграммы")
Для имени, df в all_data.items():
st.write(f"### {имя}")
st.line_chart(df[["Закрыть", "SMA20", "SMA50"]) 
