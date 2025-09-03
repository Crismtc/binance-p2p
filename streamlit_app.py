# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px

# 📌 URL del CSV en tu GitHub
CSV_URL = "https://raw.githubusercontent.com/Crismtc/binance-p2p/main/data/p2p_bob_usdt.csv"

st.set_page_config(page_title="Binance P2P — BOB → USDT", layout="wide")
st.title("💵 Binance P2P — BOB → USDT (Tendencia de mercado)")

# === 1. Cargar CSV ===
try:
    df = pd.read_csv(CSV_URL)

    # Convertir timestamp a datetime UTC
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    # Convertir a hora de Bolivia (GMT-4)
    df["datetime_bo"] = df["timestamp"].dt.tz_convert("America/La_Paz")

    # Separar fecha y hora
    df["Fecha"] = df["datetime_bo"].dt.date
    df["Hora"] = df["datetime_bo"].dt.strftime("%H:%M:%S")

except Exception as e:
    st.error(f"Error cargando CSV: {e}")
    st.stop()

# === 2. Filtro de fechas ===
min_date, max_date = df["datetime_bo"].min(), df["datetime_bo"].max()
start_date, end_date = st.date_input(
    "📅 Selecciona rango de fechas:",
    [min_date.date(), max_date.date()],
    min_value=min_date.date(),
    max_value=max_date.date()
)

mask = (df["datetime_bo"].dt.date >= start_date) & (df["datetime_bo"].dt.date <= end_date)
df_filtered = df.loc[mask]

# === 3. Gráfico de tendencia ===
fig = px.line(
    df_filtered,
    x="datetime_bo",
    y="market_median",
    title="📈 Tendencia del tipo de cambio (BOB → USDT)",
    labels={"datetime_bo": "Fecha", "market_median": "Mediana del mercado (BOB/USDT)"},
    markers=True
)
st.plotly_chart(fig, use_container_width=True)

# === 4. Estadísticas rápidas ===
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Último valor", f"{df['market_median'].iloc[-1]:.3f} BOB/USDT")
with col2:
    st.metric("Máximo histórico", f"{df['market_median'].max():.3f} BOB/USDT")
with col3:
    st.metric("Mínimo histórico", f"{df['market_median'].min():.3f} BOB/USDT")

# === 5. Indicador de tendencia ===
if len(df) > 1:
    if df["market_median"].iloc[-1] > df["market_median"].iloc[-2]:
        st.success("📈 Tendencia actual: AL ALZA")
    else:
        st.error("📉 Tendencia actual: A LA BAJA")

# === 6. Alerta de compra (promedio últimos 7 días) ===
df_last7 = df[df["datetime_bo"] >= (df["datetime_bo"].max() - pd.Timedelta(days=7))]
if not df_last7.empty:
    avg_last7 = df_last7["market_median"].mean()
    last_value = df["market_median"].iloc[-1]

    if last_value < avg_last7:
        st.warning(f"⚠️ Oportunidad: el valor actual ({last_value:.3f}) está por debajo del promedio de 7 días ({avg_last7:.3f}).")
    else:
        st.info(f"ℹ️ El valor actual ({last_value:.3f}) está por encima del promedio de 7 días ({avg_last7:.3f}).")

# === 7. Mostrar tabla con columnas seleccionadas ===
st.subheader("📊 Registros históricos (filtrados)")
cols_mostrar = [
    "Fecha", "Hora", "asset", "fiat",
    "buy_min", "buy_max", "buy_median", "buy_avg",
    "sell_min", "sell_max", "sell_median", "sell_avg",
    "market_median"
]

st.dataframe(
    df_filtered[cols_mostrar].sort_values(["Fecha", "Hora"], ascending=[False, False]),
    use_container_width=True
)

st.caption("Datos obtenidos de Binance P2P vía GitHub Actions (auto-actualizados cada 30 min).")
