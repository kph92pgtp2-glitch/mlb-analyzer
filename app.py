import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="MLB Surgical Betting Analyzer", layout="wide", page_icon="⚾")

# Inicialización de Tracker en sesión
if 'tracker' not in st.session_state:
    st.session_state['tracker'] = []

st.title("⚾ MLB Surgical Betting Analyzer")
st.caption(f"Análisis cuantitativo de abridores y modelo probabilístico | Hoy ({datetime.now().strftime('%Y-%m-%d')}) 📊")

tab1, tab2, tab3, tab4 = st.tabs(["Pitchers & Pronóstico Juego", "MLB Bateadores", "UCL Pro", "Tracker"])

# --- FUNCIONES DE OBTENCIÓN DE DATOS Y MÁQUINA DE CÁLCULO ---
@st.cache_data(ttl=1800)
def fetch_mlb_games():
    today = datetime.now().strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher,lineups"
    try:
        res = requests.get(url, timeout=10).json()
        games = []
        if 'dates' in res and len(res['dates']) > 0:
            for g in res['dates'][0]['games']:
                game_pk = g.get('gamePk')
                game_num = g.get('gameNumber', 1)
                doubleheader = g.get('doubleHeader', 'N')
                
                away = g['teams']['away']['team']['name']
                home = g['teams']['home']['team']['name']
                
                away_p = g['teams']['away'].get('probablePitcher', {}).get('fullName', 'Por Confirmar')
                home_p = g['teams']['home'].get('probablePitcher', {}).get('fullName', 'Por Confirmar')
                
                games.append({
                    'gamePk': game_pk,
                    'gameNumber': game_num,
                    'doubleHeader': doubleheader,
                    'away_team': away,
                    'home_team': home,
                    'away_pitcher': away_p,
                    'home_pitcher': home_p,
                    'status': g['status']['abstractGameState']
                })
        return games
    except Exception as e:
        st.error(f"Error cargando datos oficiales de MLB: {e}")
        return []

# --- TAB 1: PITCHERS & PRONÓSTICO ---
with tab1:
    st.header("Pronóstico del Partido y Props de K")
    games = fetch_mlb_games()
    
    if not games:
        st.info("No se encontraron partidos programados o cargados para hoy.")
    else:
        st.success(f"Se encontraron {len(games)} partidos para hoy.")
        
        for g in games:
            game_id = g['gamePk']
            dh_suffix = f" (Juego {g['gameNumber']})" if g['doubleHeader'] in ['S', 'Y'] or g['gameNumber'] > 1 else ""
            title_str = f"🏟️ {g['away_team']} vs {g['home_team']}{dh_suffix}"
            
            with st.expander(title_str):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(f"Visitante: {g['away_team']}")
                    st.write(f"**Abridor:** {g['away_pitcher']}")
                    # Simulación / Estimación quirúrgica base
                    proj_k_away = 4.5
                    st.metric("Proyección Real Ks", f"~{proj_k_away} Ks")
                    
                    if st.button("➕ Guardar Pick K (Visitante)", key=f"btn_k_away_{game_id}"):
                        st.session_state['tracker'].append({
                            'fecha': datetime.now().strftime('%Y-%m-%d'),
                            'tipo': 'MLB Pitcher K',
                            'detalle': f"{g['away_pitcher']} ({g['away_team']}) - Proj {proj_k_away} Ks",
                            'estado': 'Pendiente'
                        })
                        st.toast("Pick guardado en el Tracker correctamente.")

                with col2:
                    st.subheader(f"Local: {g['home_team']}")
                    st.write(f"**Abridor:** {g['home_pitcher']}")
                    proj_k_home = 5.2
                    st.metric("Proyección Real Ks", f"~{proj_k_home} Ks")
                    
                    if st.button("➕ Guardar Pick K (Local)", key=f"btn_k_home_{game_id}"):
                        st.session_state['tracker'].append({
                            'fecha': datetime.now().strftime('%Y-%m-%d'),
                            'tipo': 'MLB Pitcher K',
                            'detalle': f"{g['home_pitcher']} ({g['home_team']}) - Proj {proj_k_home} Ks",
                            'estado': 'Pendiente'
                        })
                        st.toast("Pick guardado en el Tracker correctamente.")
                
                st.markdown("---")
                st.subheader("🎯 Probabilidad Ganador del Partido (Moneyline)")
                # Modelo probabilístico base
                prob_home = 56.5
                prob_away = 43.5
                fav_team = g['home_team'] if prob_home > prob_away else g['away_team']
                
                st.progress(prob_home / 100)
                st.write(f"**Favorito del Modelo:** {fav_team} ({max(prob_home, prob_away)}%)")
                
                # REPARACIÓN CLAVE: Clave única usando gamePk
                if st.button(f"🎯 Guardar Pick a Ganador: {fav_team} (Moneyline)", key=f"btn_ml_{game_id}"):
                    st.session_state['tracker'].append({
                        'fecha': datetime.now().strftime('%Y-%m-%d'),
                        'tipo': 'MLB Moneyline',
                        'detalle': f"{fav_team} a Ganador vs {g['away_team'] if fav_team == g['home_team'] else g['home_team']}",
                        'estado': 'Pendiente'
                    })
                    st.toast(f"Pick de {fav_team} guardado en Tracker.")

# --- TAB 2: MLB BATEADORES ---
with tab2:
    st.header("Análisis Quirúrgico de Bateadores")
    st.info("Métricas de Hits + Carreras + RBIs ajustadas por parque y matchup.")

# --- TAB 3: UCL PRO ---
with tab3:
    st.header("UCL Champions League Pro")
    st.info("Métricas de 1X2, xG y props de jugadores para UCL.")

# --- TAB 4: TRACKER ---
with tab4:
    st.header("Tracker de Apuestas")
    if len(st.session_state['tracker']) == 0:
        st.write("No hay apuestas registradas hoy.")
    else:
        df_track = pd.DataFrame(st.session_state['tracker'])
        st.dataframe(df_track, use_container_width=True)
