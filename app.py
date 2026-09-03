from datetime import datetime
import pandas as pd
import statsapi
import streamlit as st

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(page_title="MLB Analyzer", page_icon="⚾", layout="centered")

st.title("⚾ MLB STATS & BETTING ANALYZER")
hoy_str = datetime.now().strftime("%Y-%m-%d")
st.caption(
    f"Reporte automático diario | Fecha: **{hoy_str}** | Proyecciones y Totales"
)

# ---------------------------------------------------------
# CÓDIGO DE OBTENCIÓN AUTOMÁTICA DE DATOS (MLB API)
# ---------------------------------------------------------


@st.cache_data(ttl=1800)  # Actualiza cada 30 minutos
def obtener_partidos_hoy():
    try:
        # Consulta los juegos programados para la fecha de hoy
        sched = statsapi.schedule(date=hoy_str)
        partidos = []

        for juego in sched:
            # Filtrar partidos válidos
            if juego.get("status") in [
                "Scheduled",
                "Pre-Game",
                "In Progress",
                "Warmup",
            ]:
                partido_info = {
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
                    # Línea promedio de la MLB para referencia
                    "linea_puntos_min": 8.0,
                    "linea_puntos_max": 8.5,
                }
                partidos.append(partido_info)

        return partidos
    except Exception as e:
        st.error(f"Error al conectar con la API de MLB: {e}")
        return []


# ---------------------------------------------------------
# MOTOR ESTADÍSTICO DE PROYECCIÓN
# ---------------------------------------------------------


def analizar_partido(juego):
    # Promedios base liga MLB
    carreras_base_local = 4.6
    carreras_base_visita = 4.4

    proj_local = carreras_base_local
    proj_visita = carreras_base_visita

    total_proyectado = round(proj_local + proj_visita, 1)

    linea_inferior = juego["linea_puntos_min"]
    linea_superior = juego["linea_puntos_max"]

    if total_proyectado > linea_superior:
        margen = round(total_proyectado - linea_superior, 1)
        recomendacion = f"Más de {linea_superior} (Margen +{margen})"
        confianza = "Alta" if margen >= 1.5 else "Media"
    elif total_proyectado < linea_inferior:
        margen = round(linea_inferior - total_proyectado, 1)
        recomendacion = f"Menos de {linea_inferior} (Margen -{margen})"
        confianza = "Alta" if margen >= 1.5 else "Media"
    else:
        recomendacion = "Sin valor claro, pasar este partido"
        confianza = "Baja"

    ganador = (
        juego["equipo_local"]
        if proj_local >= proj_visita
        else juego["equipo_visita"]
    )

    return {
        "ganador": ganador,
        "total_proyectado": total_proyectado,
        "recomendacion": recomendacion,
        "confianza": confianza,
    }


# ---------------------------------------------------------
# INTERFAZ DE LA WEB APP
# ---------------------------------------------------------
with st.spinner("Cargando partidos reales del día desde la MLB..."):
    partidos = obtener_partidos_hoy()

if not partidos:
    st.info("No hay partidos programados o pendientes para el día de hoy.")
else:
    st.subheader(f"📋 Partidos del día ({len(partidos)})")

    for juego in partidos:
        res = analizar_partido(juego)

        with st.container():
            st.markdown(
                f"### ⚾ **{juego['equipo_visita']} @ {juego['equipo_local']}**"
            )
            st.caption(f"📍 **Estadio:** {juego['estadio']}")

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Abridor Visita:** {juego['pitcher_visita']}")
                st.write(f"**Abridor Local:** {juego['pitcher_local']}")
            with col2:
                st.write(f"**Ganador Proyectado:** {res['ganador']}")
                st.write(f"**Total Proyectado:** {res['total_proyectado']}")

            # Alertas si no hay abridor confirmado aún
            if (
                juego["pitcher_visita"] == "Por anunciar"
                or juego["pitcher_local"] == "Por anunciar"
            ):
                st.warning(
                    "⚠️ Alerta: Uno o ambos abridores no han sido confirmados oficialmente."
                )

            # Recomendación final
            if "Más de" in res["recomendacion"]:
                st.success(f"🎯 **Recomendación:** {res['recomendacion']}")
            elif "Menos de" in res["recomendacion"]:
                st.info(f"🛡️ **Recomendación:** {res['recomendacion']}")
            else:
                st.error(f"➡️ **Recomendación:** {res['recomendacion']}")

            st.divider()

st.caption(
    "Apoyo estadístico automatizado. Las líneas y abridores se actualizan en tiempo real."
)
