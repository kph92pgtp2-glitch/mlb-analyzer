import pandas as pd
import streamlit as st

st.set_page_config(page_title="MLB Analyzer", page_icon="⚾", layout="centered")

st.title("⚾ MLB STATS & BETTING ANALYZER")
st.caption("Reporte de proyecciones, totales de carreras y valor de líneas")


def analizar_partido(juego):
    carreras_base_local = juego["equipo_local_carreras_prom"]
    carreras_base_visita = juego["equipo_visita_carreras_prom"]

    impacto_pitcher_visita = juego["pitcher_visita_era"] * 0.45
    impacto_pitcher_local = juego["pitcher_local_era"] * 0.45

    proj_local = (carreras_base_local * 0.55) + impacto_pitcher_visita
    proj_visita = (carreras_base_visita * 0.55) + impacto_pitcher_local

    total_proyectado = round(proj_local + proj_visita, 1)

    linea_inferior = juego["linea_puntos_min"]
    linea_superior = juego["linea_puntos_max"]

    margen = 0
    recomendacion = ""
    confianza = "Media"

    if total_proyectado > linea_superior:
        margen = round(total_proyectado - linea_superior, 1)
        if margen >= 2.0:
            confianza = "Alta"
            recomendacion = f"Más de {linea_superior} (Margen +{margen})"
        else:
            recomendacion = f"Posible Más de {linea_superior}"
    elif total_proyectado < linea_inferior:
        margen = round(linea_inferior - total_proyectado, 1)
        if margen >= 2.0:
            confianza = "Alta"
            recomendacion = f"Menos de {linea_inferior} (Margen -{margen})"
        else:
            recomendacion = f"Posible Menos de {linea_inferior}"
    else:
        recomendacion = "Sin valor claro, pasar este partido"
        confianza = "Baja"

    ganador = (
        juego["equipo_local"]
        if proj_local > proj_visita
        else juego["equipo_visita"]
    )

    return {
        "ganador": ganador,
        "total_proyectado": total_proyectado,
        "recomendacion": recomendacion,
        "confianza": confianza,
    }


partidos_hoy = [
    {
        "equipo_visita": "LA Dodgers",
        "equipo_local": "SF Giants",
        "estadio": "Oracle Park",
        "pitcher_visita": "Tyler Glasnow",
        "pitcher_visita_era": 3.10,
        "pitcher_local": "Logan Webb",
        "pitcher_local_era": 3.45,
        "equipo_visita_carreras_prom": 5.2,
        "equipo_local_carreras_prom": 4.1,
        "linea_puntos_min": 7.0,
        "linea_puntos_max": 7.5,
    },
    {
        "equipo_visita": "NY Mets",
        "equipo_local": "ATL Braves",
        "estadio": "Truist Park",
        "pitcher_visita": "Kodai Senga",
        "pitcher_visita_era": 4.85,
        "pitcher_local": "Spencer Strider",
        "pitcher_local_era": 5.10,
        "equipo_visita_carreras_prom": 4.8,
        "equipo_local_carreras_prom": 5.0,
        "linea_puntos_min": 8.0,
        "linea_puntos_max": 8.5,
    },
]

st.subheader("📋 Reporte y recomendaciones del día")

for juego in partidos_hoy:
    res = analizar_partido(juego)

    with st.container():
        st.markdown(
            f"### **{juego['equipo_visita']} @ {juego['equipo_local']}**"
        )
        st.caption(f"📍 {juego['estadio']}")

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Ganador Proyectado:** {res['ganador']}")
            st.write(f"**Total Proyectado:** {res['total_proyectado']} carreras")
        with col2:
            st.write(f"**Confianza:** {res['confianza']}")
            st.write(
                f"**Línea:** {juego['linea_puntos_min']} - {juego['linea_puntos_max']}"
            )

        if juego["pitcher_visita_era"] > 4.5:
            st.warning(
                f"⚠️ Alerta: {juego['pitcher_visita']} ({juego['equipo_visita']}) tiene ERA elevado: {juego['pitcher_visita_era']}"
            )
        if juego["pitcher_local_era"] > 4.5:
            st.warning(
                f"⚠️ Alerta: {juego['pitcher_local']} ({juego['equipo_local']}) tiene ERA elevado: {juego['pitcher_local_era']}"
            )

        if "Más de" in res["recomendacion"]:
            st.success(f"🎯 **Recomendación:** {res['recomendacion']}")
        elif "Menos de" in res["recomendacion"]:
            st.info(f"🛡️ **Recomendación:** {res['recomendacion']}")
        else:
            st.error(f"➡️ **Recomendación:** {res['recomendacion']}")

        st.divider()

st.caption(
    "Recuerda: esto es apoyo estadístico, no garantía. Apuesta responsablemente."
)
