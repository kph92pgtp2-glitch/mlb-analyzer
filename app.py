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

st.title("⚾ MLB & Liga MX Analizador Quirúrgico")

tab1, tab2, tab3 = st.tabs(["⚾ MLB Cartelera del Día", "⚽ Liga MX Calculator", "📈 Tracker de Aciertos"])

# ---------------------------------------------------------
# FUNCIONES AUXILIARES CON API MLB
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def obtener_contexto_equipos():
    contexto = {}
    try:
        url = "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104"
        r = requests.get(url, timeout=5).json()
        for rec in r.get("records", []):
            for tr in rec.get("teamRecords", []):
                team_name = tr["team"]["name"]
                clinch = tr.get("clinchIndicator", "")
                gb = tr.get("gamesBack", "-")
                wc_gb = tr.get("wildCardGamesBack", "-")
                
                if clinch in ["y", "z", "x"]:
                    tag, mult = "🛡️ Clasificado Amarrado (Cuidando Brazos)", 0.85
                elif (wc_gb != "-" and float(wc_gb if wc_gb != "-" else 99) <= 4.0) or (gb != "-" and float(gb if gb != "-" else 99) <= 3.0):
                    tag, mult = "🔥 Pelea de Comodín/División (Urgencia Máxima)", 1.15
                else:
                    tag, mult = "⚾ Posición Regular / Sin Presión Directa", 1.0
                    
                contexto[team_name] = {"tag": tag, "mult": mult}
    except Exception:
        pass
    return contexto

@st.cache_data(ttl=7200)
def obtener_k_proyectado_pitcher(pitcher_id, mult_contexto):
    """Obtiene las métricas reales del pitcher (K/9 e IP) de la API oficial."""
    if not pitcher_id:
        return 4.5
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}?hydrate=stats(group=[pitching],type=[season])"
        r = requests.get(url, timeout=5).json()
        stats = r.get("people", [{}])[0].get("stats", [])
        
        k9 = 7.5  # Base por defecto si no hay stats
        ip = 5.0
        
        for s in stats:
            if s.get("type", {}).get("displayName") == "season":
                splits = s.get("splits", [])
                if splits:
                    stat_dict = splits[0].get("stat", {})
                    k9 = float(stat_dict.get("strikeoutsPer9Inn", 7.5))
                    games = float(stat_dict.get("gamesPitched", 1))
                    innings = float(stat_dict.get("inningsPitched", 5.0))
                    if games > 0:
                        ip = innings / games

        base_k = (k9 / 9.0) * ip
        return round(base_k * mult_contexto, 1)
    except Exception:
        return round(5.0 * mult_contexto, 1)

# ---------------------------------------------------------
# TAB 1: CARTELERA MLB REAL
# ---------------------------------------------------------
with tab1:
    st.header("⚾ Cartelera y Lanzadores Probables de Hoy")
    fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")
    st.caption(f"Partidos programados para hoy ({fecha_hoy}) | Métricas Reales de Pitcher en Vivo 📊")

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
                
                p_away_data = g["teams"]["away"].get("probablePitcher", {})
                p_home_data = g["teams"]["home"].get("probablePitcher", {})
                
                pitcher_away = p_away_data.get("fullName", "Por Anunciar")
                pitcher_home = p_home_data.get("fullName", "Por Anunciar")
                
                id_away = p_away_data.get("id", None)
                id_home = p_home_data.get("id", None)
                
                info_away = contexto_tabla.get(away_team, {"tag": "⚾ Normal", "mult": 1.0})
                info_home = contexto_tabla.get(home_team, {"tag": "⚾ Normal", "mult": 1.0})
                
                # Proyección basada en stats reales
                k_proj_a = obtener_k_proyectado_pitcher(id_away, info_away["mult"])
                k_proj_h = obtener_k_proyectado_pitcher(id_home, info_home["mult"])
                
                with st.expander(f"🏟️ {away_team} vs {home_team}"):
                    c_a, c_h = st.columns(2)
                    
                    with c_a:
                        st.markdown(f"**Abridor {away_team}:**")
                        st.write(f"👤 {pitcher_away}")
                        st.metric("Proyección Real Ponches (Ks)", f"~{k_proj_a} Ks")
                        st.caption(f"Contexto: {info_away['tag']}")
                    
                    with c_h:
                        st.markdown(f"**Abridor {home_team}:**")
                        st.write(f"👤 {pitcher_home}")
                        st.metric("Proyección Real Ponches (Ks)", f"~{k_proj_h} Ks")
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
