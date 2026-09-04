import streamlit as st
import pandas as pd
import datetime
import requests

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(page_title="MLB & Liga MX Analytics Pro", layout="wide", page_icon="⚾")

if "tracker_apuestas" not in st.session_state:
    st.session_state.tracker_apuestas = []

st.title("🎯 Analizador Deportivo Quirúrgico - MLB & Liga MX")
st.caption("Proyecciones cuantitativas basadas en volumen de picheos, contexto de Playoffs y API oficial MLB.")

tab1, tab2, tab3 = st.tabs(["⚾ MLB Pitcher Projections", "⚽ Liga MX Calculator", "📈 Tracker de Aciertos"])

# ---------------------------------------------------------
# TAB 1: MLB PITCHER PROJECTIONS (SISTEMA QUIRÚRGICO)
# ---------------------------------------------------------
with tab1:
    st.header("⚾ Modelo Cuantitativo de Ponches (MLB Septiembre)")
    st.write("Ajuste preciso por tasa K/9, tendencia del rival y factor de manejo de bullpen de septiembre.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Parámetros del Lanzador")
        k_per_9 = st.number_input("Promedio de K por cada 9 entradas (K/9 del Pitcher):", value=9.5, step=0.1, help="Consulta la métrica K/9 actual del abridor.")
        ip_promedio = st.number_input("Promedio de Entradas Lanzadas por Salida (IP):", value=5.2, step=0.1)
        k_linea_casa = st.number_input("Línea de Ponches (Ks) de la Casa de Apuestas:", value=5.5, step=0.5)

    with col2:
        st.subheader("2. Contexto Rival y Septiembre")
        tendencia_rival = st.selectbox(
            "Tasa de Ponches del Equipo Rival:",
            ["Propenso al Ponche (K% Alto > 24%)", "Promedio Liga (K% 20% - 24%)", "Contacto Alto / Difícil de Ponchar (K% < 20%)"]
        )
        situacion_septiembre = st.selectbox(
            "Contexto de Tabla / Manejo de Mánager (Septiembre):",
            [
                "🔥 En Pelea de Comodín / División (Urgencia Máxima - Conteo Alto de Picheos)",
                "🛡️ Clasificado Amarrado (Cuidando Brazos - Máximo 75-80 Picheos)",
                "⚾ Eliminado / Probando Prospectos (Sin Presión / Rutina Normal)"
            ]
        )

    # ---------------------------------------------------------
    # MATRIZ DE CÁLCULO CIENTÍFICO
    # ---------------------------------------------------------
    # 1. Base por K/9 e IP
    base_ks_esperados = (k_per_9 / 9.0) * ip_promedio

    # 2. Factor Rival
    factor_rival = 1.0
    if "Alto" in tendencia_rival:
        factor_rival = 1.12
    elif "Contacto Alto" in tendencia_rival:
        factor_rival = 0.88

    # 3. Factor Urgencia / Septiembre (Manejo de Pitches)
    factor_septiembre = 1.0
    explicacion_contexto = ""
    if "🔥" in situacion_septiembre:
        factor_septiembre = 1.15
        explicacion_contexto = "El mánager exigirá al abridor hasta 95-105 picheos. Mayor proyección de outs y ponches."
    elif "🛡️" in situacion_septiembre:
        factor_septiembre = 0.82
        explicacion_contexto = "Riesgo alto de extracción en la 4ta o 5ta entrada para descansar el brazo hacia octubre."
    else:
        factor_septiembre = 0.95
        explicacion_contexto = "Inning limits estándar y rotación compartida con relevistas jóvenes."

    # Proyección Final
    k_proyectados = round(base_ks_esperados * factor_rival * factor_septiembre, 2)
    edge = round(k_proyectados - k_linea_casa, 2)

    st.markdown("---")
    st.subheader("📊 Diagnóstico del Análisis")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("K Base Teórico", round(base_ks_esperados, 2))
    m2.metric("Línea Casa", f"{k_linea_casa}")
    m3.metric("Proyección Final", f"{k_proyectados} Ks")
    
    if edge >= 0.8:
        m4.metric("Valor Detectado", "OVER 🟢", delta=f"+{edge} Ks de ventaja")
    elif edge <= -0.8:
        m4.metric("Valor Detectado", "UNDER 🔴", delta=f"{edge} Ks de ventaja")
    else:
        m4.metric("Valor Detectado", "SIN VENTAJA ⚪", delta=f"{edge} Ks (Línea Ajustada)")

    st.info(f"📌 **Nota del Análisis de Septiembre:** {explicacion_contexto}")

# ---------------------------------------------------------
# TAB 2: LIGA MX CALCULATOR
# ---------------------------------------------------------
with tab2:
    st.header("⚽ Calculadora de Expectativa - Liga MX")
    
    col_a, col_b = st.columns(2)
    with col_a:
        equipo_l = st.text_input("Local", "América")
        g_l = st.number_input("Prom. Goles Favor (Local)", value=1.8, step=0.1)
        c_l = st.number_input("Prom. Córners Favor (Local)", value=5.5, step=0.1)
    with col_b:
        equipo_v = st.text_input("Visitante", "Guadalajara")
        g_v = st.number_input("Prom. Goles Favor (Visitante)", value=1.1, step=0.1)
        c_v = st.number_input("Prom. Córners Favor (Visitante)", value=4.2, step=0.1)

    exp_goles = round(g_l + g_v, 2)
    exp_corners = round(c_l + c_v, 1)

    st.markdown("---")
    res1, res2 = st.columns(2)
    res1.metric("Proyección Goles Totales", f"{exp_goles}")
    res2.metric("Proyección Córners Totales", f"{exp_corners}")

# ---------------------------------------------------------
# TAB 3: TRACKER DE ACIERTOS & VERIFICACIÓN API MLB
# ---------------------------------------------------------
with tab3:
    st.header("📈 Tracker de Aciertos & Verificación en Vivo de MLB")
    
    st.subheader("🔍 Consultar Marcadores y Boxscore de Ayer")
    if st.button("📡 Cargar Resultados Reales de MLB de Ayer"):
        ayer = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={ayer}"
        try:
            res = requests.get(url).json()
            games = res.get("dates", [{}])[0].get("games", [])
            if games:
                st.success(f"Se obtuvieron {len(games)} partidos jugados el {ayer}:")
                for g in games:
                    home = g["teams"]["home"]["team"]["name"]
                    away = g["teams"]["away"]["team"]["name"]
                    score_h = g["teams"]["home"].get("score", 0)
                    score_a = g["teams"]["away"].get("score", 0)
                    st.write(f"• **{away}** ({score_a}) vs **{home}** ({score_h}) - Finalizado")
            else:
                st.warning(f"No hay registros de juegos para la fecha {ayer}.")
        except Exception as e:
            st.error("Error conectando a la API de MLB.")

    st.markdown("---")
    st.subheader("📝 Bitácora de Registro Manual")
    
    with st.form("form_tracker"):
        f1, f2, f3 = st.columns(3)
        dep = f1.selectbox("Deporte", ["MLB", "Liga MX"])
        pick_txt = f2.text_input("Apuesta / Pick (Ej: Skubal OVER 5.5 Ks)")
        est = f3.selectbox("Estado", ["Pendiente ⏳", "Ganada 🟢", "Perdida 🔴"])
        
        btn_sub = st.form_submit_button("Guardar en Tracker")
        if btn_sub and pick_txt:
            st.session_state.tracker_apuestas.append({
                "Fecha": datetime.date.today().strftime("%Y-%m-%d"),
                "Deporte": dep,
                "Pick": pick_txt,
                "Estado": est
            })
            st.success("Registrado correctamente.")

    if st.session_state.tracker_apuestas:
        df_log = pd.DataFrame(st.session_state.tracker_apuestas)
        st.dataframe(df_log, use_container_width=True)
        
        g = len(df_log[df_log["Estado"] == "Ganada 🟢"])
        p = len(df_log[df_log["Estado"] == "Perdida 🔴"])
        tot = g + p
        wr = round((g / tot) * 100, 1) if tot > 0 else 0.0
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Aciertos 🟢", g)
        k2.metric("Fallos 🔴", p)
        k3.metric("% Efectividad (Win Rate)", f"{wr}%")
