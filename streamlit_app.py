# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="P2P BOB → USDT", layout="wide")
st.title("Binance P2P — BOB → USDT (tendencia)")

raw_url = st.text_input("Raw CSV URL (raw.githubusercontent.com)", 
                        "https://raw.githubusercontent.com/<TU_USER>/<TU_REPO>/main/data/p2p_bob_usdt.csv")

if raw_url:
    try:
        df = pd.read_csv(raw_url)
        df['datetime_utc'] = pd.to_datetime(df['datetime_utc'])
        df = df.sort_values('datetime_utc').reset_index(drop=True)
        df['datetime_local'] = df['datetime_utc'].dt.tz_localize('UTC').dt.tz_convert('America/La_Paz')
        df['price'] = df['market_median'].astype(float)
        df['SMA_7'] = df['price'].rolling(7, min_periods=1).mean()
        df['SMA_14'] = df['price'].rolling(14, min_periods=1).mean()
        df['SMA_30'] = df['price'].rolling(30, min_periods=1).mean()

        fig = px.line(df, x='datetime_local', y=['price','SMA_7','SMA_14','SMA_30'],
                      labels={'value':'BOB por 1 USDT', 'datetime_local':'Fecha (America/La_Paz)'},
                      title="Precio y medias móviles")
        st.plotly_chart(fig, use_container_width=True)

        latest = df.iloc[-1]
        pct = (latest['SMA_7'] - latest['SMA_30']) / latest['SMA_30'] if latest['SMA_30'] != 0 else 0
        trend = "Insuficientes datos"
        if pct > 0.002: trend = "Alcista"
        elif pct < -0.002: trend = "Bajista"
        else: trend = "Lateral"

        st.metric("Tendencia actual", trend)
        st.write("Últimas entradas")
        st.dataframe(df.tail(10))
    except Exception as e:
        st.error(f"Error cargando CSV: {e}")
