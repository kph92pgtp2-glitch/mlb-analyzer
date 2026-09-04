import streamlit as st
import pandas as pd
import datetime
import requests

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(page_title="MLB Analytics Pro", layout="wide", page_icon="⚾")

if "tracker_apuestas" not in st.session_state:
    st.session_state.tracker_apuestas = []

st.title("⚾ MLB & Liga MX Analizador Pro")

tab1, tab2, tab3 = st.tabs(["⚾ MLB Cartelera del Día", "⚽ Liga MX Calculator", "📈 Tracker de Aciertos"])

# ---------------------------------------------------------
# FUNCIÓN AUXILIAR: OBTENER ESTADO DE PLAYOFFS / URGENCIA
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def obtener_contexto_equipos():
    """Consulta la API de Standings de MLB para etiquetar urgencia automática."""
    contexto = {}
    try:
        url = "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104"
        r = requests.get(url, timeout=5).json()
        records = r.get("records", [])
        for rec in records:
            team_records = rec.get("teamRecords", [])
            for tr in team_records:
                team_name = tr["team"]["name"]
                clinch_status = tr.get("clinchIndicator", "")
                gb = tr.get("gamesBack", "-")
                wc_gb = tr.get("wildCardGamesBack", "-")
                
                # Criterio de etiqueta de Septiembre
                if clinch_status in ["y", "z", "x"]:  # División o Wild Card amarrado
                    tag = "🛡️ Clasificado Amarrado (Cuidando Brazos)"
                    mult = 0.85
                elif (wc_gb != "-" and float(wc_gb if wc_gb != "-" else 99) <= 4.0) or (gb != "-" and float(gb if gb != "-" else 99) <= 3.0):
                    tag = "🔥 Pelea de Comodín/División (Urgencia Máxima)"
                    mult = 1.15
                else:
                    tag = "⚾ Posición Regular / Sin Presión Directa"
                    mult = 1.0
                    
                contexto[team_name] = {"tag": tag, "mult": mult}
    except Exception:
        pass
    return contexto

# ---------------------------------------------------------
# TAB 1: CARTELERA MLB AUTOMÁTICA CON INTELIGENCIA DE TABLA
# ---------------------------------------------------------
with tab1:
    st.header("⚾ Cartelera y Lanzadores Probables de Hoy")
    fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")
    st.caption(f"Partidos programados para hoy ({fecha_hoy}) | Análisis de Standings Automático 🤖")

    contexto_tabla = obtener_contexto_equipos()

    url_mlb = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha_hoy}&hydrate=probablePitcher,linescore"
    try:
        r = requests.get(url_mlb).json()
        games = r.get("dates", [{}])[0].get("games", [])
        
        if games:
            st.success(f"Se encontraron {len(games)} partidos para hoy.")
            for g in games:
                away_team = g["teams"]["away"]["team"]["name"]
                home_team = g["teams"]["home"]["team"]["name"]
                
                pitcher_away = g["teams"]["away"].get("probablePitcher", {}).get("fullName", "Por Anunciar")
                pitcher_home = g["teams"]["home"].get("probablePitcher", {}).get("fullName", "Por Anunciar")
                
                # Contexto automático por equipo
                info_away = contexto_tabla.get(away_team, {"tag": "⚾ Normal", "mult": 1.0})
                info_home = contexto_tabla.get(home_team, {"tag": "⚾ Normal", "mult": 1.0})
                
                with st.expander(f"🏟️ {away_team} vs {home_team}"):
                    c_a, c_h = st.columns(2)
                    
                    with c_a:
                        st.markdown(f"**Abridor {away_team}:**")
                        st.write(f"👤 {pitcher_away}")
                        k_proj_a = round(5.8 * info_away["mult"], 1)
                        st.metric("Proyección Ponches (Ks)", f"~{k_proj_a} Ks")
                        st.caption(f"Contexto: {info_away['tag']}")
                    
                    with c_h:
                        st.markdown(f"**Abridor {home_team}:**")
                        st.write(f"👤 {pitcher_home}")
                        k_proj_h = round(5.5 * info_home["mult"], 1)
                        st.metric("Proyección Ponches (Ks)", f"~{k_proj_h} Ks")
                        st.caption(f"Contexto: {info_home['tag']}")
        else:
            st.info("No hay partidos de MLB programados para la fecha de hoy.")
    except Exception as e:
        st.error("Error al cargar la cartelera de MLB. Intenta refrescar.")

# ---------------------------------------------------------
# TAB 2: LIGA MX CALCULATOR
# ---------------------------------------------------------
with tab2:
    st.header("⚽ Calculadora de Valor - Liga MX")
    col_a, col_b = st.columns(2)
    with col_a:
        equipo_l = st.text_input("Equipo Local", "Tigres")
        goles_l = st.number_input("Promedio Goles Local", value=1.6, step=0.1)
        corners_l = st.number_input("Promedio Córners Local", value=5.2, step=0.1)
    with col_b:
        equipo_v = st.text_input("Equipo Visitante", "Pachuca")
        goles_v = st.number_input("Promedio Goles Visitante", value=1.2, step=0.1)
        corners_v = st.number_input("Promedio Córners Visitante", value=4.1, step=0.1)

    st.markdown("---")
    m1, m2 = st.columns(2)
    m1.metric("Goles Esperados Totales", round(goles_l + goles_v, 2))
    m2.metric("Córners Esperados Totales", round(corners_l + corners_v, 1))

# ---------------------------------------------------------
# TAB 3: TRACKER DE ACIERTOS
# ---------------------------------------------------------
with tab3:
    st.header("📈 Tracker de Aciertos")
    
    with st.form("form_tracker"):
        f1, f2, f3 = st.columns(3)
        dep = f1.selectbox("Deporte", ["MLB", "Liga MX"])
        pick_txt = f2.text_input("Apuesta (Ej: Skubal OVER 5.5 Ks)")
        est = f3.selectbox("Estado", ["Pendiente ⏳", "Ganada 🟢", "Perdida 🔴"])
        
        if st.form_submit_button("Guardar"):
            if pick_txt:
                st.session_state.tracker_apuestas.append({
                    "Fecha": datetime.date.today().strftime("%Y-%m-%d"),
                    "Deporte": dep,
                    "Pick": pick_txt,
                    "Estado": est
                })
                st.success("¡Guardado!")

    if st.session_state.tracker_apuestas:
        df_log = pd.DataFrame(st.session_state.tracker_apuestas)
        st.dataframe(df_log, use_container_width=True)
        
        g = len(df_log[df_log["Estado"] == "Ganada 🟢"])
        p = len(df_log[df_log["Estado"] == "Perdida 🔴"])
        tot = g + p
        wr = round((g / tot) * 100, 1) if tot > 0 else 0.0
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Ganadas 🟢", g)
        k2.metric("Perdidas 🔴", p)
        k3.metric("% Win Rate", f"{wr}%")
