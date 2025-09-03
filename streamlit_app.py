# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px

# ---------- Config ----------
CSV_URL = "https://raw.githubusercontent.com/Crismtc/binance-p2p/main/data/p2p_bob_usdt.csv"
st.set_page_config(page_title="Binance P2P — BOB → USDT", layout="wide")
st.title("💵 Binance P2P — BOB → USDT (Tendencia de mercado)")

# ---------- Cargar y preparar datos (robusto) ----------
@st.cache_data(ttl=60)  # cache por 60s para no recargar en cada interacción
def load_and_prepare(url):
    df = pd.read_csv(url)

    # buscar columna de fecha/hora entre las más comunes
    posibles = ["datetime_utc", "timestamp", "datetime", "date", "time"]
    dtcol = None
    for c in posibles:
        if c in df.columns:
            dtcol = c
            break

    if dtcol is None:
        raise ValueError(f"No se encontró columna de fecha/hora. Columnas disponibles: {', '.join(df.columns)}")

    # convertir a datetime (asumir UTC si tiene offset o forzar utc)
    df[dtcol] = pd.to_datetime(df[dtcol], errors="coerce", utc=True)

    # quitar filas sin fecha válida
    df = df.dropna(subset=[dtcol]).reset_index(drop=True)
    if df.empty:
        raise ValueError("El CSV no contiene filas con fecha válida.")

    # generar columna con hora Bolivia
    df["datetime_bo"] = df[dtcol].dt.tz_convert("America/La_Paz")

    # separar fecha y hora
    df["Fecha"] = df["datetime_bo"].dt.date
    df["Hora"] = df["datetime_bo"].dt.strftime("%H:%M:%S")

    # asegurar columnas numéricas que usaremos (convertir si vienen como strings)
    numeric_cols = [
        "buy_min", "buy_max", "buy_median", "buy_avg",
        "sell_min", "sell_max", "sell_median", "sell_avg",
        "market_median"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            # si faltan, crear columna vacía para evitar KeyError más abajo
            df[col] = pd.NA

    return df

# cargar
try:
    df = load_and_prepare(CSV_URL)
except Exception as e:
    st.error(f"Error cargando CSV: {e}")
    st.stop()

# ---------- Filtro de fechas ----------
min_date, max_date = df["datetime_bo"].min().date(), df["datetime_bo"].max().date()
start_date, end_date = st.date_input(
    "📅 Selecciona rango de fechas:",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

mask = (df["datetime_bo"].dt.date >= start_date) & (df["datetime_bo"].dt.date <= end_date)
df_filtered = df.loc[mask].copy().sort_values("datetime_bo", ascending=False)

if df_filtered.empty:
    st.info("No hay datos en el rango de fechas seleccionado.")
else:
    # ---------- Gráfico de tendencia ----------
    st.subheader("📈 Tendencia (Market Median)")
    fig = px.line(
        df_filtered,
        x="datetime_bo",
        y="market_median",
        title="Tendencia del tipo de cambio (BOB → USDT)",
        labels={"datetime_bo": "Fecha (Hora Bolivia)", "market_median": "Market Median (BOB/USDT)"},
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---------- Estadísticas rápidas ----------
    col1, col2, col3 = st.columns(3)
    with col1:
        last_val = df_filtered["market_median"].dropna().iloc[0] if not df_filtered["market_median"].dropna().empty else None
        st.metric("Último valor", f"{last_val:.3f} BOB/USDT" if last_val is not None else "N/D")
    with col2:
        max_val = df["market_median"].max()
        st.metric("Máximo histórico", f"{max_val:.3f} BOB/USDT" if pd.notna(max_val) else "N/D")
    with col3:
        min_val = df["market_median"].min()
        st.metric("Mínimo histórico", f"{min_val:.3f} BOB/USDT" if pd.notna(min_val) else "N/D")

    # ---------- Indicador de tendencia ----------
    st.subheader("Tendencia y alertas")
    if len(df_filtered) >= 2 and df_filtered["market_median"].dropna().shape[0] >= 2:
        values = df_filtered["market_median"].dropna().values
        if values[0] > values[1]:
            st.success("📈 Tendencia actual: AL ALZA")
        elif values[0] < values[1]:
            st.warning("📉 Tendencia actual: A LA BAJA")
        else:
            st.info("➡️ Tendencia lateral / sin cambio reciente")
    else:
        st.info("No hay suficientes puntos para determinar tendencia.")

    # ---------- Alerta de compra (última media hora y promedio 7 días) ----------
    st.subheader("💡 Alertas de compra")
    # última media hora (en datetime_bo)
    last_time = df["datetime_bo"].max()
    window_30m = last_time - pd.Timedelta(minutes=30)
    df_30 = df[df["datetime_bo"] >= window_30m]
    if not df_30.empty and df_30["market_median"].dropna().shape[0] > 0:
        avg_30 = df_30["market_median"].mean()
        last_price = df["market_median"].dropna().iloc[-1] if not df["market_median"].dropna().empty else None
        st.write(f"Último precio (última fila): {last_price:.3f} | Promedio última 30 min: {avg_30:.3f}")
        if last_price is not None and last_price < avg_30 * 0.995:
            st.success("🟢 Precio muy bajo para comprar dólares (>=0.5% por debajo del promedio 30m).")
        else:
            st.info("Precio dentro del rango normal respecto a la última media hora.")
    else:
        st.info("No hay suficientes datos en la última media hora para calcular la alerta.")

    # alerta adicional vs promedio 7 días
    df_last7 = df[df["datetime_bo"] >= (df["datetime_bo"].max() - pd.Timedelta(days=7))]
    if not df_last7.empty and df_last7["market_median"].dropna().shape[0] > 0:
        avg_7 = df_last7["market_median"].mean()
        last_price = df["market_median"].dropna().iloc[-1] if not df["market_median"].dropna().empty else None
        if last_price is not None and last_price < avg_7:
            st.warning(f"⚠️ El precio actual ({last_price:.3f}) está por debajo del promedio de 7 días ({avg_7:.3f}).")
        else:
            st.info(f"ℹ️ Precio actual ({last_price:.3f}) vs promedio 7d ({avg_7:.3f}).")

    # ---------- Tabla con columnas seleccionadas (fecha y hora en hora Bolivia) ----------
    st.subheader("📊 Registros históricos (filtrados)")
    cols_mostrar = [
        "Fecha", "Hora", "asset", "fiat",
        "buy_min", "buy_max", "buy_median", "buy_avg",
        "sell_min", "sell_max", "sell_median", "sell_avg",
        "market_median"
    ]
    # Asegurar que todas las columnas existan
    cols_mostrar = [c for c in cols_mostrar if c in df_filtered.columns]
    st.dataframe(df_filtered[cols_mostrar].reset_index(drop=True), use_container_width=True)

    st.caption("Datos obtenidos de Binance P2P vía GitHub Actions (auto-actualizados cada 30 min).")
