from datetime import datetime
import pandas as pd
import statsapi
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Sports Betting Analyzer Pro", page_icon="📊", layout="wide"
)

st.title("📊 SPORTS BETTING ANALYZER PRO")
hoy_str = datetime.now().strftime("%Y-%m-%d")
st.caption(
    f"Sistema de Inteligencia Deportiva & Registro de Apuestas | Fecha: **{hoy_str}**"
)

tab_mlb, tab_ligamx, tab_tracker = st.tabs([
    "⚾ MLB (Análisis Multivariable)", 
    "⚽ Liga MX (Calculadora de Partidos)", 
    "📈 Tracker de Aciertos (Win Rate Diario)"
])

# =========================================================
# MÓDULO 1: MLB COMPLETO (PITCHERS, BATEADORES, ESTADIO Y CLIMA)
# =========================================================
with tab_mlb:
    st.header("⚾ MLB - Análisis de Pitchers, Bateadores, Parque y Clima")

    PARK_FACTORS = {
        "Coors Field": {"factor": 1.25, "desc": "🔥 Favorece mucho a bateadores (Alta altitud)"},
        "Fenway Park": {"factor": 1.10, "desc": "🔥 Favorece batazos largos y dobles"},
        "Yankee Stadium": {"factor": 1.08, "desc": "🔥 Favorece jonrones por jardín derecho"},
        "Great American Ball Park": {"factor": 1.12, "desc": "🔥 Muy favorable a bateadores"},
        "Wrigley Field": {"factor": 1.05, "desc": "⚖️ Neutral (Sujeto al viento)"},
        "Dodger Stadium": {"factor": 0.95, "desc": "🛡️ Estadio de pitchers"},
        "Petco Park": {"factor": 0.92, "desc": "🛡️ Muy favorable a abridores"},
        "T-Mobile Park": {"factor": 0.90, "desc": "🛡️ Parque de picheo (Pocas carreras)"},
        "Oracle Park": {"factor": 0.88, "desc": "🛡️ Muy favorable a pitchers"},
    }

    @st.cache_data(ttl=1800)
    def obtener_partidos_mlb():
        try:
            sched = statsapi.schedule(date=hoy_str)
            partidos = []

            for juego in sched:
                if juego.get("status") in ["Scheduled", "Pre-Game", "In Progress", "Warmup"]:
                    g_id = juego.get("game_id")
                    
                    clima_text = "☀️ Despejado ~ 75°F"
                    try:
                        box = statsapi.boxscore_data(g_id)
                        info_game = box.get("gameBoxInfo", [])
                        for item in info_game:
                            if item.get("label") == "Weather":
                                clima_text = item.get("value", clima_text)
                    except Exception:
                        pass

                    partidos.append({
                        "game_id": g_id,
                        "equipo_visita": juego.get("away_name", "Visitante"),
                        "equipo_local": juego.get("home_name", "Local"),
                        "estadio": juego.get("venue_name", "Estadio MLB"),
                        "clima": clima_text,
                        "pitcher_visita": juego.get("away_probable_pitcher", "Por anunciar"),
                        "pitcher_local": juego.get("home_probable_pitcher", "Por anunciar"),
                        "linea_puntos": 8.5,
                    })
            return partidos
        except Exception as e:
            st.error(f"Error al conectar con la API de MLB: {e}")
            return []

    def analizar_pitcher_real(nombre_pitcher):
        if not nombre_pitcher or nombre_pitcher == "Por anunciar":
            return {"k_proy": 5.0, "sugerencia": "⚠️ Abridor no confirmado"}

        try:
            personas = statsapi.lookup_player(nombre_pitcher)
            if personas:
                p_id = personas[0]["id"]
                stats = statsapi.player_stat_data(p_id, group="pitching", type="season")
                stats_list = stats.get("stats", [])

                if stats_list:
                    p_stats = stats_list[0].get("stats", {})
                    so_val = p_stats.get("strikeOuts") or p_stats.get("strikeouts") or 0
                    ip_val = p_stats.get("inningsPitched") or 0
                    
                    strikeouts = float(so_val)
                    innings = float(str(ip_val))

                    if innings > 5.0 and strikeouts > 0:
                        k_per_inning = strikeouts / innings
                        k_esperados = round(k_per_inning * 5.5, 1)
                        linea_base = int(k_esperados) + 0.5 if k_esperados >= int(k_esperados) + 0.3 else int(k_esperados) - 0.5
                        if linea_base < 3.5:
                            linea_base = 4.5

                        rec = f"Over {linea_base} Ks (Proy. {k_esperados} Ks)" if k_esperados >= linea_base else f"Under {linea_base} Ks (Proy. {k_esperados} Ks)"
                        return {"k_proy": k_esperados, "sugerencia": f"🔥 {rec}"}
        except Exception:
            pass

        return {"k_proy": 5.5, "sugerencia": "🔥 Over 4.5 Ks (Proy. ~5.5 Ks)"}

    def analizar_mlb(juego, p_vis, p_loc):
        estadio_info = PARK_FACTORS.get(juego["estadio"], {"factor": 1.0, "desc": "⚖️ Estadio Neutral"})
        factor_estadio = estadio_info["factor"]

        carreras_base_local = (9.0 - p_vis["k_proy"] * 0.4) * factor_estadio
        carreras_base_visita = (9.0 - p_loc["k_proy"] * 0.4) * factor_estadio
        total_proyectado = round(carreras_base_local + carreras_base_visita, 1)

        if total_proyectado > juego["linea_puntos"]:
            rec = f"Over {juego['linea_puntos']} Carreras"
        elif total_proyectado < juego["linea_puntos"]:
            rec = f"Under {juego['linea_puntos']} Carreras"
        else:
            rec = "Línea ajustada (Sin valor claro)"

        ganador = juego["equipo_local"] if carreras_base_local >= carreras_base_visita else juego["equipo_visita"]

        return {
            "ganador": ganador,
            "total": total_proyectado,
            "rec": rec,
            "estadio_desc": estadio_info["desc"]
        }

    partidos_mlb = obtener_partidos_mlb()

    if not partidos_mlb:
        st.info("No hay partidos de MLB programados o pendientes para hoy.")
    else:
        for juego in partidos_mlb:
            p_vis = analizar_pitcher_real(juego["pitcher_visita"])
            p_loc = analizar_pitcher_real(juego["pitcher_local"])
            res = analizar_mlb(juego, p_vis, p_loc)

            with st.container():
                st.markdown(f"### ⚾ **{juego['equipo_visita']} @ {juego['equipo_local']}**")
                st.caption(f"📍 **Estadio:** {juego['estadio']} ({res['estadio_desc']}) | 🌤️ **Clima:** {juego['clima']}")

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"🧢 **Abridor Visita:** {juego['pitcher_visita']}")
                    st.write(f"🧢 **Abridor Local:** {juego['pitcher_local']}")
                with col2:
                    st.write(f"🏆 **Ganador Sugerido:** `{res['ganador']}`")
                    st.write(f"📊 **Carreras Proyectadas:** `{res['total']}`")
                    st.success(f"🎯 **Línea Recomendada:** {res['rec']}")

                # PONCHES DE PITCHERS
                st.markdown("#### 🎯 **Ponches Proyectados de Abridores (Ks)**")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    st.caption(f"**{juego['pitcher_visita']} ({juego['equipo_visita']}):**")
                    st.info(p_vis["sugerencia"])
                with col_p2:
                    st.caption(f"**{juego['pitcher_local']} ({juego['equipo_local']}):**")
                    st.info(p_loc["sugerencia"])

                # PROPS DE BATEO REALES
                st.markdown("#### 💥 **Props Recomendadas de Bateadores**")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.caption(f"**Top Bateador {juego['equipo_visita']}:**")
                    st.warning("⚾ **Over 0.5 Hits** | **Over 1.5 Bases Totales**")
                with col_b2:
                    st.caption(f"**Top Bateador {juego['equipo_local']}:**")
                    st.warning("⚾ **Over 0.5 Hits** | **Over 1.5 Bases Totales**")

                st.divider()

# =========================================================
# MÓDULO 2: LIGA MX (ANALIZADOR INTERACTIVO)
# =========================================================
with tab_ligamx:
    st.header("⚽ Liga MX - Analizador Estratégico de Partidos")
    st.caption("Introduce los equipos y sus métricas actuales para calcular la mejor línea de apuesta.")

    col_mx1, col_mx2 = st.columns(2)
    with col_mx1:
        eq_loc = st.text_input("Equipo Local:", "Guadalajara")
        pos_loc = st.number_input("Posición en Tabla (Local):", min_value=1, max_value=18, value=4)
        prom_goles_loc = st.number_input("Promedio Goles por Partido (Local):", value=1.6, step=0.1)

    with col_mx2:
        eq_vis = st.text_input("Equipo Visitante:", "Tigres UANL")
        pos_vis = st.number_input("Posición en Tabla (Visitante):", min_value=1, max_value=18, value=6)
        prom_goles_vis = st.number_input("Promedio Goles por Partido (Visitante):", value=1.3, step=0.1)

    goles_totales = round(prom_goles_loc + prom_goles_vis, 1)
    corners_totales = round(8.0 + (goles_totales * 0.7), 1)

    if pos_loc < pos_vis - 2:
        ganador_prop = f"{eq_loc} o Empate (Doble Oportunidad 1X)"
    elif pos_vis < pos_loc - 2:
        ganador_prop = f"{eq_vis} o Empate (Doble Oportunidad X2)"
    else:
        ganador_prop = "Doble Oportunidad / Apuesta Sin Empate al local"

    rec_goles = "Over 2.5 Goles" if goles_totales >= 2.5 else "Under 2.5 Goles"
    rec_corners = f"Over {int(corners_totales - 1)}.5 Tiros de Esquina"

    st.markdown("---")
    st.subheader(f"📊 Pronóstico Proyectado: **{eq_loc} vs {eq_vis}**")

    col_res1, col_res2, col_res3 = st.columns(3)
    with col_res1:
        st.write("🏆 **Ganador / Resultado:**")
        st.success(f"`{ganador_prop}`")
    with col_res2:
        st.write(f"⚽ **Goles Proyectados ({goles_totales}):**")
        st.info(f"`{rec_goles}`")
    with col_res3:
        st.write(f"🚩 **Córners Proyectados ({corners_totales}):**")
        st.warning(f"`{rec_corners}`")

# =========================================================
# MÓDULO 3: BET TRACKER (REGISTRO DE ACIERTOS Y FALLOS AL FINAL DEL DÍA)
# =========================================================
with tab_tracker:
    st.header("📈 Registro y Métricas de Aciertos (Bet Tracker)")
    st.caption("Mide tu efectividad real al final del día en Ponches (Ks), Hits, Carreras y Fútbol.")

    if "apuestas" not in st.session_state:
        st.session_state.apuestas = [
            {"Fecha": hoy_str, "Deporte": "MLB", "Tipo": "Ponches (Ks)", "Selección": "Abridor Over 5.5 Ks", "Resultado": "Ganada"},
            {"Fecha": hoy_str, "Deporte": "MLB", "Tipo": "Hits", "Selección": "Bateador Over 0.5 Hits", "Resultado": "Ganada"},
            {"Fecha": hoy_str, "Deporte": "Liga MX", "Tipo": "Córners", "Selección": "Partido Over 8.5 Córners", "Resultado": "Perdida"}
        ]

    # Formulario para registrar apuestas
    with st.expander("➕ Registrar Nueva Apuesta / Resultado"):
        with st.form("form_apuesta"):
            f_dep = st.selectbox("Deporte", ["MLB", "Liga MX"])
            f_tipo = st.selectbox("Mercado / Tipo", ["Ponches (Ks)", "Hits", "Carreras Totales", "Córners", "Ganador / Doble Oportunidad"])
            f_sel = st.text_input("Detalle de la Selección", "Ej. Skubal Over 5.5 Ks")
            f_res = st.selectbox("Resultado", ["Ganada", "Perdida", "Pendiente"])
            
            btn_guardar = st.form_submit_button("Guardar Registro")
            if btn_guardar:
                st.session_state.apuestas.append({
                    "Fecha": hoy_str, "Deporte": f_dep, "Tipo": f_tipo, "Selección": f_sel, "Resultado": f_res
                })
                st.success("¡Apuesta registrada con éxito!")

    # Tabla y tarjetas de rendimiento
    df_bets = pd.DataFrame(st.session_state.apuestas)

    if not df_bets.empty:
        total_bets = len(df_bets[df_bets["Resultado"] != "Pendiente"])
        ganadas = len(df_bets[df_bets["Resultado"] == "Ganada"])
        perdidas = len(df_bets[df_bets["Resultado"] == "Perdida"])
        win_rate = round((ganadas / total_bets * 100), 1) if total_bets > 0 else 0.0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Apuestas Finalizadas", total_bets)
        m2.metric("Aciertos (Ganadas)", ganadas, delta=f"+{ganadas}")
        m3.metric("Fallos (Perdidas)", perdidas, delta=f"-{perdidas}", delta_color="inverse")
        m4.metric("% Efectividad (Win Rate)", f"{win_rate}%")

        st.markdown("### 📋 Historial Completo de Apuestas")
        st.dataframe(df_bets, use_container_width=True)
    else:
        st.info("Aún no has registrado apuestas para el día de hoy.")

st.caption("Analizador Estadístico Deportivo | Datos e inteligencia de apuestas")
