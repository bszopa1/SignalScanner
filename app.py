# streamlit_crypto_scanner_app.py
# Mobiler Streamlit-Crypto-Scanner für BTC, ETH, XRP
# Benötigte Pakete:
# pip install streamlit yfinance pandas pandas_ta plotly python-dotenv

import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Crypto Signal Scanner", layout="centered")

# ---------------------- Sidebar / Einstellungen ----------------------
st.sidebar.header("Einstellungen")
with st.sidebar.form(key='settings'):
    tickers = st.multiselect('Ausgewählte Assets',
                              options=['BTC-USD', 'ETH-USD', 'XRP-USD', 'AAPL', 'TSLA', 'NVDA', 'MSFT', 'AMZN'],
                              default=['BTC-USD','ETH-USD','XRP-USD','AAPL','TSLA'])
    period = st.selectbox('Zeitraum laden', ['1mo','3mo','6mo','1y','2y','5y'], index=3)
    interval = st.selectbox('Interval', ['1d','1h','30m'], index=0)
    rsi_len = st.number_input('RSI Länge', min_value=5, max_value=50, value=14)
    ma_short = st.number_input('MA kurz (z.B. 50)', min_value=5, max_value=200, value=50)
    ma_long = st.number_input('MA lang (z.B. 200)', min_value=10, max_value=500, value=200)
    bb_len = st.number_input('Bollinger Länge', min_value=5, max_value=100, value=20)
    bb_std = st.number_input('Bollinger StdDev', min_value=1.0, max_value=5.0, value=2.0)
    submit = st.form_submit_button('Anwenden')

st.title('📈 Mobiler Crypto Signal Scanner')
st.markdown('Echtzeit-ähnliche Signale mit einfachen technischen Indikatoren (EOD / Intraday).')

# ---------------------- Hilfsfunktionen ----------------------

def fetch_data(ticker, period='1y', interval='1d'):
    df = yf.download(ticker, period=period, interval=interval, progress=False, threads=False)
    if df.empty:
        return df
    df = df.dropna()
    return df


def add_indicators(df, rsi_len=14, ma_short=50, ma_long=200, bb_len=20, bb_std=2.0):
    df = df.copy()
    # Moving averages
    df[f'ma_{ma_short}'] = df['Close'].rolling(ma_short).mean()
    df[f'ma_{ma_long}'] = df['Close'].rolling(ma_long).mean()
    # RSI
    df['rsi'] = ta.rsi(df['Close'], length=rsi_len)
    # MACD
    macd = ta.macd(df['Close'])
    if 'MACDh_12_26_9' in macd:
        df['macd_hist'] = macd['MACDh_12_26_9']
    else:
        df['macd_hist'] = ta.macd(df['Close'])['MACDh_12_26_9']
    # Bollinger
    bb = ta.bbands(df['Close'], length=bb_len, std=bb_std)
    df['bb_upper'] = bb[f'BBU_{bb_len}_{bb_std}']
    df['bb_lower'] = bb[f'BBL_{bb_len}_{bb_std}']
    df['bb_mid'] = bb[f'BBM_{bb_len}_{bb_std}']
    return df


def generate_signals(df, ma_short=50, ma_long=200):
    df = df.copy()
    df['signal_score'] = 0
    # Trend: MA short > MA long
    df.loc[df[f'ma_{ma_short}'] > df[f'ma_{ma_long}'], 'signal_score'] += 1
    # RSI nicht überkauft (konfigurierbar, hier < 60)
    df.loc[df['rsi'] < 60, 'signal_score'] += 1
    # MACD Histogramm positiv
    df.loc[df['macd_hist'] > 0, 'signal_score'] += 1
    # Preis oberhalb kurzer MA
    df.loc[df['Close'] > df[f'ma_{ma_short}'], 'signal_score'] += 1
    # Bollinger: Preis über unterer Band (kein Extrema)
    df.loc[df['Close'] > df['bb_lower'], 'signal_score'] += 1
    # Buy when score >= threshold
    df['buy_signal'] = df['signal_score'] >= 3
    # Mark the exact buy moments (cross from False to True)
    df['buy_event'] = df['buy_signal'] & (~df['buy_signal'].shift(1).fillna(False))
    return df

# ---------------------- Main UI ----------------------

col1, col2 = st.columns([2,1])

with col1:
    st.subheader('Signaltabelle')
    summary_rows = []

    for t in tickers:
        with st.spinner(f'Lade {t} ...'):
            df = fetch_data(t, period=period, interval=interval)
        if df.empty:
            st.warning(f'Keine Daten für {t} (Intervall {interval}, Zeitraum {period}).')
            continue
        df = add_indicators(df, rsi_len=rsi_len, ma_short=ma_short, ma_long=ma_long, bb_len=bb_len, bb_std=bb_std)
        df = generate_signals(df, ma_short=ma_short, ma_long=ma_long)
        last = df.iloc[-1]
        last_buy = df.loc[df['buy_event']].index.max() if df['buy_event'].any() else None
        last_buy_str = last_buy.strftime('%Y-%m-%d %H:%M') if last_buy is not None else '—'
        summary_rows.append({
            'Ticker': t,
            'Letzter Preis': round(last['Close'],6),
            'Signal Score': int(last['signal_score']),
            'Buy jetzt?': bool(last['buy_signal']),
            'Letztes Buy Event': last_buy_str
        })

    summary_df = pd.DataFrame(summary_rows)
    st.table(summary_df)

    st.markdown('''
    **Legende**: Signal Score summiert einfache Regeln (MA-Trend, RSI, MACD-Hist, Close>MA50, Close>BB-Lower).
    `Buy jetzt?` ist True, wenn Score >= 3. Das ist ein einfacher Startpunkt — bitte backtesten!
    ''')

with col2:
    st.subheader('Erläuterung')
    st.write('Die Regeln sind bewusst einfach gehalten. Du kannst Werte in der Sidebar anpassen.')
    st.write('Hinweis: Dieses Tool bietet keine Finanzberatung. Backtests und Money-Management sind wichtig.')

# ---------------------- Charting für Auswahl ----------------------
st.divider()
st.subheader('Interaktiver Chart')
selected = st.selectbox('Wähle ein Asset für Chart', tickers)

if selected:
    df = fetch_data(selected, period=period, interval=interval)
    if not df.empty:
        df = add_indicators(df, rsi_len=rsi_len, ma_short=ma_short, ma_long=ma_long, bb_len=bb_len, bb_std=bb_std)
        df = generate_signals(df, ma_short=ma_short, ma_long=ma_long)

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'))
        # MA lines
        fig.add_trace(go.Scatter(x=df.index, y=df[f'ma_{ma_short}'], name=f'MA{ma_short}', line=dict(width=1)))
        fig.add_trace(go.Scatter(x=df.index, y=df[f'ma_{ma_long}'], name=f'MA{ma_long}', line=dict(width=1)))
        # Bollinger
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_upper'], name='BB Upper', line=dict(width=1), opacity=0.5))
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_mid'], name='BB Mid', line=dict(width=1), opacity=0.5))
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_lower'], name='BB Lower', line=dict(width=1), opacity=0.5))
        # Buy markers
        buys = df[df['buy_event']]
        if not buys.empty:
            fig.add_trace(go.Scatter(x=buys.index, y=buys['Close'], mode='markers', name='Buy', marker=dict(symbol='triangle-up', size=10)))

        fig.update_layout(height=520, margin=dict(l=10,r=10,t=30,b=10), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # Indicators below
        c1, c2 = st.columns(2)
        with c1:
            st.line_chart(df['rsi'].rename('RSI'))
        with c2:
            st.line_chart(df['macd_hist'].rename('MACD Hist'))

    else:
        st.warning('Keine Daten für dieses Asset.')

# ---------------------- Alerts (optional) ----------------------
st.divider()
st.subheader('Alerts (optional)')
st.write('Du kannst Telegram-Alerts aktivieren: Bot-Token + Chat-ID in ENV setzen oder hier eintragen.')
use_telegram = st.checkbox('Telegram aktivieren', value=False)
if use_telegram:
    telegram_token = st.text_input('Telegram Bot Token (botxxxx:...)')
    telegram_chat = st.text_input('Chat ID')
    alert_button = st.button('Test-Alert senden')
    if alert_button:
        if telegram_token and telegram_chat:
            import requests
            msg = f'Test Alert from Crypto Signal Scanner @ {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}'
            url = f'https://api.telegram.org/bot{telegram_token}/sendMessage'
            try:
                r = requests.post(url, data={'chat_id': telegram_chat, 'text': msg}, timeout=10)
                if r.status_code == 200:
                    st.success('Test-Alert gesendet — prüfe Telegram.')
                else:
                    st.error('Fehler beim Senden. Prüfe Token / Chat-ID.')
            except Exception as e:
                st.error('Fehler: ' + str(e))
        else:
            st.error('Bitte Token und Chat-ID angeben.')

# ---------------------- Footer / Run Hinweise ----------------------
st.markdown('---')
st.markdown('**Wie starten?**

1. Speichere diese Datei als `app.py`.
2. Installiere Abhängigkeiten: `pip install streamlit yfinance pandas pandas_ta plotly python-dotenv`.
3. Starte lokal: `streamlit run app.py` und öffne die Network-URL auf deinem Handy (gleiches WLAN) oder deploye auf Streamlit Cloud.
')

st.caption('Dieses Tool ist ein Prototyp — immer erst backtesten bevor echtes Geld eingesetzt wird.')
