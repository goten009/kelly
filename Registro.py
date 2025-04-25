import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import json

# === CONFIGURACIÓN DE GOOGLE SHEETS DESDE SECRETS ===
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
info = json.loads(st.secrets["GSPREAD_CREDENTIALS"])
creds = Credentials.from_service_account_info(info, scopes=SCOPE)
client = gspread.authorize(creds)
sheet = client.open("Control Apuestas Rentables").sheet1

# === FUNCIONES ===
def obtener_fila_libre():
    data = sheet.get_all_values()
    for i, fila in enumerate(data, start=1):
        if all(celda == '' for j, celda in enumerate(fila) if j < 6):  # Ignorar columna G
            return i
    return len(data) + 1

def registrar_apuesta(fecha, partido, cuota, monto, resultado):
    ganancia = round(monto * cuota if resultado == "ganada" else 0, 2)
    fila = [fecha, partido, cuota, monto, resultado, ganancia]
    fila_destino = obtener_fila_libre()
    sheet.update(f"A{fila_destino}:F{fila_destino}", [fila])
    return fila_destino, fila

def obtener_datos_dataframe():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def obtener_bankroll_actual(df):
    if not df.empty and 'Bankroll' in df.columns:
        return df['Bankroll'].iloc[-1]
    return 0

def calcular_estadisticas(df):
    ganadas = df[df['Resultado'] == 'ganada']
    perdidas = df[df['Resultado'] == 'perdida']
    total = len(ganadas) + len(perdidas)
    winrate = (len(ganadas) / total) * 100 if total > 0 else 0
    bankroll_inicial = df['Bankroll'].iloc[0] if 'Bankroll' in df.columns else 0
    bankroll_actual = df['Bankroll'].iloc[-1] if 'Bankroll' in df.columns else 0
    rentabilidad = ((bankroll_actual - bankroll_inicial) / bankroll_inicial * 100) if bankroll_inicial else 0
    return len(ganadas), len(perdidas), winrate, rentabilidad

# === INTERFAZ STREAMLIT ===
st.set_page_config(page_title="Control de Apuestas", page_icon="⚽", layout="centered")
st.title("📊 Control de Apuestas Rentables")

st.header("🧮 Calculadora Kelly Fraccional")
df = obtener_datos_dataframe()
bankroll = obtener_bankroll_actual(df)

partido_kelly = st.text_input("🏟️ Partido para calcular apuesta", placeholder="Ej: Liverpool vs West Ham")
cuota_kelly = st.number_input("🎯 Cuota de la apuesta", min_value=1.01, step=0.01, key="cuota_kelly")
probabilidad_kelly = st.slider("📊 Probabilidad estimada de éxito (%)", min_value=1, max_value=100, value=60, key="probabilidad_kelly")

p = probabilidad_kelly / 100
q = 1 - p
b = cuota_kelly - 1
try:
    f_kelly = ((b * p) - q) / b
    f_kelly_fraccional = f_kelly / 2 if f_kelly > 0 else 0
    monto_recomendado = int(round(bankroll * f_kelly_fraccional))
    st.success(f"💰 Monto sugerido por Kelly Fraccional: ${monto_recomendado:,}")
except:
    st.warning("No se puede calcular Kelly con estos datos.")

st.markdown("---")
st.header("📝 Registro de Apuestas")

with st.form("registro"):
    partido = st.text_input("🏟️ Partido", placeholder="Ej: Liverpool vs West Ham", key="registro_partido")
    cuota = st.number_input("🎯 Cuota total", min_value=1.01, step=0.01, key="registro_cuota")
    monto = st.number_input("💵 Monto apostado", min_value=1000.0, step=500.0)
    resultado = st.selectbox("📈 Resultado", ["ganada", "perdida"])
    enviar = st.form_submit_button("Registrar apuesta")

if enviar:
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    fila, datos = registrar_apuesta(fecha, partido, cuota, monto, resultado)
    st.success(f"Apuesta registrada en la fila {fila}: {datos}")

# Mostrar estadísticas
st.markdown("---")
ganadas, perdidas, winrate, rentabilidad = calcular_estadisticas(df)

col1, col2 = st.columns(2)
col1.metric("💰 Bankroll actual", f"${bankroll:,}")
col2.metric("📊 Rentabilidad Total", f"{rentabilidad:.2f}%")

col3, col4 = st.columns(2)
col3.metric("✅ Apuestas ganadas", ganadas)
col4.metric("❌ Apuestas perdidas", perdidas)

st.metric("🎯 Winrate", f"{winrate:.2f}%")

st.dataframe(df)
