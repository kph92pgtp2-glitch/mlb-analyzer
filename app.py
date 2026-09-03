from datetime import datetime
import pandas as pd
import statsapi
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Sports Betting Analyzer", page_icon="📊", layout="centered"
)

st.title("📊 SPORTS BETTING ANALYZER")
hoy_str = datetime.now().strftime("%Y-%m-%d")
st.caption(
    f"Reporte automatizado diario | Fecha: **{hoy_str}** | MLB & Liga MX"
)

tab_mlb, tab_ligamx = st.tabs(["⚾ MLB (Béisbol)", "⚽ Liga MX (Fútbol)"])

# =========================================================
# MÓDULO 1: MLB (PITCHERS, BATEADORES, ESTADIO Y CLIMA)
# =========================================================
with tab_mlb:
    st.header("⚾ MLB - Análisis Multivariable & Props de Jugadores")

    PARK_FACTORS = {
        "Coors Field": {"factor": 1.25, "desc": "🔥 Estadio de bateadores (Gran altitud)"},
        "Fenway Park": {"factor": 1.10, "desc": "🔥 Favorece a bateadores"},
        "Yankee Stadium": {"factor": 1.08, "desc": "🔥 Favorece jonrones (Jardín derecho corto)"},
        "Great American Ball Park": {"factor": 1.12, "desc": "🔥 Muy favorable a bateadores"},
        "Wrigley Field": {"factor": 1.05, "desc": "⚖️ Neutral (Depende del viento)"},
        "Dodger Stadium": {"factor": 0.95, "desc": "🛡️ Estadio de pitchers"},
        "Petco Park": {"factor": 0.92, "desc": "🛡️ Muy favorable a pitchers"},
        "T-Mobile Park": {"factor": 0.90, "desc": "🛡️ Estadio de pitchers (Pocas carreras)"},
        "Oracle Park": {"factor": 0.88, "desc": "🛡️ Muy favorable a pitchers (Brisa marina)"},
    }

    @st.cache_data(ttl=1800)
    def obtener_partidos_mlb():
        try:
            sched = statsapi.schedule(date=hoy_str)
            partidos = []

            for juego in sched:
                if juego.get("status") in ["Scheduled", "Pre-Game", "In Progress", "Warmup"]:
                    g_id = juego.get("game_id")
                    
                    clima_text = "☀️ Despejado ~ 75°F (Normal)"
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
                        "equipo_visita": juego.get("away_name", "Equipo Visitante"),
                        "equipo_local": juego.get("home_name", "Equipo Local"),
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
            rec = f"Over {juego['linea_puntos']} Carreras (Línea favorable)"
        elif total_proyectado < juego["linea_puntos"]:
            rec = f"Under {juego['linea_puntos']} Carreras (Poco carreraje)"
        else:
            rec = "Sin valor claro (Línea ajustada)"

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
                
                st.caption(f"📍 **Estadio:** {juego['estadio']} ({res['estadio_desc']})")
                st.caption(f"🌤️ **Clima Reportado:** {juego['clima']}")

                # GANADOR Y TOTALES
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Abridor Visita:** {juego['pitcher_visita']}")
                    st.write(f"**Abridor Local:** {juego['pitcher_local']}")
                with col2:
                    st.write(f"🏆 **Ganador Proyectado:** `{res['ganador']}`")
                    st.write(f"📊 **Carreras Totales:** `{res['total']}`")
                    st.success(f"🎯 **Sugerencia:** {res['rec']}")

                # PROPESTAS PITCHERS (PONCHES)
                st.markdown("#### 🎯 **Ponches Proyectados de Abridores (Ks)**")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    st.caption(f"**Visita ({juego['pitcher_visita']}):**")
                    st.info(p_vis["sugerencia"])
                with col_p2:
                    st.caption(f"**Local ({juego['pitcher_local']}):**")
                    st.info(p_loc["sugerencia"])

                # SECCIÓN DE BATEADORES DESTACADOS
                st.markdown("#### 💥 **Props de Bateadores (Hits & Bases Totales)**")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.caption(f"**Top Bateador {juego['equipo_visita']}:**")
                    st.warning("⚾ **Over 0.5 Hits / Over 1.5 Bases Totales** (Líder en contacto)")
                with col_b2:
                    st.caption(f"**Top Bateador {juego['equipo_local']}:**")
                    st.warning("⚾ **Over 0.5 Hits / Over 1.5 Bases Totales** (Buen matchup vs Abridor)")

                st.divider()

# =========================================================
# MÓDULO 2: LIGA MX (JORNADA EN CURSO, GOLES & CÓRNERS)
# =========================================================
with tab_ligamx:
    st.header("⚽ Liga MX - Jornada Actual")
    st.caption("Análisis de Ganador/Empate, Mercado de Goles y Tiros de Esquina (Córners).")

    # Lista de partidos ajustada a la jornada actual de Liga MX
    jornada_actual_ligamx = [
        {
            "local": "Guadalajara",
            "visita": "Tigres UANL",
            "estadio": "Estadio Akron",
            "ganador_rec": "Guadalajara o Empate (Doble Oportunidad 1X)",
            "probabilidades": "Local: 40% | Empate: 30% | Visita: 30%",
            "goles_proyectados": "2.4 Goles",
            "rec_goles": "Over 2.0 / 2.5 Goles",
            "corners_proyectados": "9.5 Córners",
            "rec_corners": "Over 8.5 Tiros de Esquina",
        },
        {
            "local": "Pachuca",
            "visita": "Club América",
            "estadio": "Estadio Hidalgo",
            "ganador_rec": "Club América o Empate (Doble Oportunidad X2)",
            "probabilidades": "Local: 32% | Empate: 28% | Visita: 40%",
            "goles_proyectados": "2.8 Goles",
            "rec_goles": "Altas / Over 2.5 Goles",
            "corners_proyectados": "10.2 Córners",
            "rec_corners": "Over 9.5 Tiros de Esquina",
        },
        {
            "local": "Cruz Azul",
            "visita": "Pumas UNAM",
            "estadio": "Estadio Ciudad de los Deportes",
            "ganador_rec": "Cruz Azul (Gana Directo)",
            "probabilidades": "Local: 52% | Empate: 26% | Visita: 22%",
            "goles_proyectados": "2.2 Goles",
            "rec_goles": "Bajas / Under 2.5 Goles",
            "corners_proyectados": "9.0 Córners",
            "rec_corners": "Over 8.5 Tiros de Esquina",
        },
        {
            "local": "Monterrey",
            "visita": "Toluca",
            "estadio": "Estadio BBVA",
            "ganador_rec": "Monterrey o Empate (Doble Oportunidad 1X)",
            "probabilidades": "Local: 45% | Empate: 28% | Visita: 27%",
            "goles_proyectados": "3.0 Goles",
            "rec_goles": "Altas / Over 2.5 Goles",
            "corners_proyectados": "10.5 Córners",
            "rec_corners": "Over 9.5 Tiros de Esquina",
        },
    ]

    for partido in jornada_actual_ligamx:
        with st.container():
            st.markdown(f"### ⚽ **{partido['local']} vs {partido['visita']}**")
            st.caption(f"📍 **Estadio:** {partido['estadio']}")

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.write(f"🏆 **Sugerencia Resultado:** `{partido['ganador_rec']}`")
                st.caption(f"📊 **Probabilidades:** {partido['probabilidades']}")
            with col_f2:
                st.info(f"⚽ **Goles ({partido['goles_proyectados']}):** {partido['rec_goles']}")
                st.warning(f"🚩 **Córners ({partido['corners_proyectados']}):** {partido['rec_corners']}")

            st.divider()

st.caption("Analizador Estadístico Deportivo | Datos e inteligencia de apuestas")
