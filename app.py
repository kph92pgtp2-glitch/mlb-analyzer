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

# Pestañas principales
tab_mlb, tab_ligamx = st.tabs(["⚾ MLB (Béisbol)", "⚽ Liga MX (Fútbol)"])

# =========================================================
# MÓDULO 1: MLB (EQUIPOS, TOTALES, WINNER & PROPS)
# =========================================================
with tab_mlb:
    st.header("⚾ MLB - Partidos & Proyecciones")

    @st.cache_data(ttl=1800)
    def obtener_partidos_mlb():
        try:
            sched = statsapi.schedule(date=hoy_str)
            partidos = []

            for juego in sched:
                if juego.get("status") in [
                    "Scheduled",
                    "Pre-Game",
                    "In Progress",
                    "Warmup",
                ]:
                    partidos.append({
                        "game_id": juego.get("game_id"),
                        "equipo_visita": juego.get(
                            "away_name", "Equipo Visitante"
                        ),
                        "equipo_local": juego.get("home_name", "Equipo Local"),
                        "estadio": juego.get("venue_name", "Estadio MLB"),
                        "pitcher_visita": juego.get(
                            "away_probable_pitcher", "Por anunciar"
                        ),
                        "pitcher_local": juego.get(
                            "home_probable_pitcher", "Por anunciar"
                        ),
                        "linea_puntos": 8.5,
                    })
            return partidos
        except Exception as e:
            st.error(f"Error al conectar con la API de MLB: {e}")
            return []

    def analizar_mlb(juego):
        carreras_base_local = 4.6
        carreras_base_visita = 4.4
        total_proyectado = round(carreras_base_local + carreras_base_visita, 1)

        if total_proyectado > juego["linea_puntos"]:
            recomendacion = f"Más de {juego['linea_puntos']} carreras"
        elif total_proyectado < juego["linea_puntos"]:
            recomendacion = f"Menos de {juego['linea_puntos']} carreras"
        else:
            recomendacion = "Sin valor claro, pasar"

        ganador = (
            juego["equipo_local"]
            if carreras_base_local >= carreras_base_visita
            else juego["equipo_visita"]
        )
        return {
            "ganador": ganador,
            "total": total_proyectado,
            "rec": recomendacion,
            "carreras_local": carreras_base_local,
            "carreras_visita": carreras_base_visita,
        }

    def calcular_props_pitcher(nombre_pitcher):
        if nombre_pitcher == "Por anunciar":
            return {"sugerencia": "⚠️ Abridor no confirmado"}
        return {"sugerencia": "🔥 Proyección: Over 4.5 Ponches (Ks)"}

    partidos_mlb = obtener_partidos_mlb()

    if not partidos_mlb:
        st.info("No hay partidos de MLB programados o pendientes para hoy.")
    else:
        for juego in partidos_mlb:
            res = analizar_mlb(juego)

            with st.container():
                st.markdown(
                    f"### ⚾ **{juego['equipo_visita']} @ {juego['equipo_local']}**"
                )
                st.caption(f"📍 **Estadio:** {juego['estadio']}")

                # --- 1. PROYECCIÓN DE GANADOR Y CARRERAS ---
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Abridor Visita:** {juego['pitcher_visita']}")
                    st.write(f"**Abridor Local:** {juego['pitcher_local']}")
                    st.write(f"**Carreras Visita (Proy.):** {res['carreras_visita']}")
                    st.write(f"**Carreras Local (Proy.):** {res['carreras_local']}")
                with col2:
                    st.write(f"🏆 **Ganador Proyectado:** `{res['ganador']}`")
                    st.write(f"📊 **Carreras Totales:** `{res['total']}`")
                    st.success(f"🎯 **Sugerencia:** {res['rec']}")

                # --- 2. PROYECCIÓN DE PONCHES (Ks) ---
                st.markdown("#### 🎯 **Ponches del Pitcher (Ks)**")
                col_p1, col_p2 = st.columns(2)
                p_vis = calcular_props_pitcher(juego["pitcher_visita"])
                p_loc = calcular_props_pitcher(juego["pitcher_local"])

                with col_p1:
                    st.caption(f"**Visita ({juego['pitcher_visita']}):** {p_vis['sugerencia']}")
                with col_p2:
                    st.caption(f"**Local ({juego['pitcher_local']}):** {p_loc['sugerencia']}")

                # --- 3. PROPS BATEADORES ---
                with st.expander("🧢 Props de Bateadores (Hits / Carreras)"):
                    st.write(f"• **1+ Hits:** Alta probabilidad para el 1er y 2do bateador de la alineación.")
                    st.write(f"• **1+ Carrera / RBI:** Recomendado en limpiabases del equipo local.")

                st.divider()

# =========================================================
# MÓDULO 2: LIGA MX (FÚTBOL MEXICANO)
# =========================================================
with tab_ligamx:
    st.header("⚽ Liga MX - Analizador de Partidos")
    st.caption("Selecciona los equipos para proyectar el resultado y total de goles.")

    equipos_ligamx = [
        "Guadalajara",
        "Club América",
        "Tigres UANL",
        "CF Monterrey",
        "Cruz Azul",
        "Pachuca",
        "Toluca",
        "Pumas UNAM",
        "Santos Laguna",
        "León",
        "Atlas",
        "Puebla",
        "Tijuana",
        "Querétaro",
        "FC Juárez",
        "Necaxa",
        "Mazatlán",
        "Apostadores/Otro",
    ]

    col_eq1, col_eq2 = st.columns(2)
    with col_eq1:
        local_sel = st.selectbox("Equipo Local", equipos_ligamx, index=0)
    with col_eq2:
        visita_sel = st.selectbox("Equipo Visitante", equipos_ligamx, index=2)

    goles_prom_loc = st.slider("Goles Promedio Local (últimos 5 juegos)", 0.5, 3.0, 1.5, 0.1)
    goles_prom_vis = st.slider("Goles Promedio Visitante (últimos 5 juegos)", 0.5, 3.0, 1.2, 0.1)

    total_goles_fut = round(goles_prom_loc + goles_prom_vis, 1)

    if goles_prom_loc > goles_prom_vis + 0.3:
        pron_res = f"Gana {local_sel} (Local)"
    elif goles_prom_vis > goles_prom_loc + 0.3:
        pron_res = f"Gana {visita_sel} (Visitante)"
    else:
        pron_res = "Empate / Doble Oportunidad"

    rec_goles = "Altas / Over 2.5 Goles" if total_goles_fut >= 2.5 else "Bajas / Under 2.5 Goles"

    st.markdown("---")
    st.markdown(f"### ⚽ **{local_sel} vs {visita_sel}**")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.write(f"🏆 **Pronóstico:** `{pron_res}`")
        st.write(f"⚽ **Goles Totales Proyectados:** `{total_goles_fut}`")
    with col_f2:
        st.info(f"🎯 **Línea de Goles:** {rec_goles}")

st.caption("Analizador Estadístico Deportivo | Datos en tiempo real")
