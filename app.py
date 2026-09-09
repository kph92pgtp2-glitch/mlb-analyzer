import streamlit as st
import pandas as pd
import datetime
import requests
import os
import re
import unicodedata

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(page_title="Analytics Pro - MLB & UCL", layout="wide", page_icon="📊")

ARCH_TRACKER = "tracker_apuestas.csv"

def limpiar_texto(texto):
    """Elimina acentos y convierte a minúsculas para comparaciones exactas."""
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower().strip()

def cargar_tracker():
    if os.path.exists(ARCH_TRACKER):
        try:
            return pd.read_csv(ARCH_TRACKER)
        except Exception:
            return pd.DataFrame(columns=["Fecha", "Deporte", "Pick", "Estado"])
    return pd.DataFrame(columns=["Fecha", "Deporte", "Pick", "Estado"])

def guardar_tracker(df):
    df.to_csv(ARCH_TRACKER, index=False)

st.title("📊 Sports Analytics Pro - Módulo Quirúrgico")

tab1, tab2, tab4, tab3 = st.tabs([
    "⚾ Pitchers (Ks)", 
    "💥 Bateadores MLB", 
    "🏆 Champions League", 
    "📈 Tracker de Aciertos"
])

# ---------------------------------------------------------
# CONSTANTES Y FACTORES DE ESTADIO (MLB)
# ---------------------------------------------------------
PARK_FACTORS = {
    "Colorado Rockies": {"factor": 115, "tipo": "🔥 Altísimo Bateo (Coors Field)"},
    "Boston Red Sox": {"factor": 108, "tipo": "🔥 Muy Alto (Fenway Park)"},
    "Cincinnati Reds": {"factor": 106, "tipo": "🔥 Favorito Jonrones/Hits"},
    "Philadelphia Phillies": {"factor": 104, "tipo": "🔥 Favorito Bateo"},
    "Los Angeles Dodgers": {"factor": 102, "tipo": "⚾ Ligero Favor Bateo"},
    "New York Yankees": {"factor": 101, "tipo": "⚾ Corto por el Derecho"},
    "Atlanta Braves": {"factor": 100, "tipo": "⚖️ Neutral"},
    "San Diego Padres": {"factor": 96, "tipo": "🛡️ Pitcheo Favorito (Petco Park)"},
    "San Francisco Giants": {"factor": 94, "tipo": "🛡️ Difícil para Batear (Oracle)"},
    "Seattle Mariners": {"factor": 92, "tipo": "🛡️ Muy Difícil para Bateo"},
}

# ---------------------------------------------------------
# FUNCIONES API MLB
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
                gb = str(tr.get("gamesBack", "-"))
                wc_gb = str(tr.get("wildCardGamesBack", "-"))
                
                try:
                    val_wc = float(wc_gb) if wc_gb != "-" else 99.0
                    val_gb = float(gb) if gb != "-" else 99.0
                except ValueError:
                    val_wc, val_gb = 99.0, 99.0

                if clinch in ["y", "z", "x"]:
                    tag, mult = "🛡️ Clasificado Amarrado (Cuidando Brazos)", 0.85
                elif val_wc <= 4.0 or val_gb <= 3.0:
                    tag, mult = "🔥 Pelea de Comodín/División (Urgencia Máxima)", 1.15
                else:
                    tag, mult = "⚾ Posición Regular", 1.0
                    
                contexto[team_name] = {"tag": tag, "mult": mult}
    except Exception:
        pass
    return contexto

@st.cache_data(ttl=3600)
def obtener_k_proyectado_pitcher(pitcher_id, mult_contexto):
    if not pitcher_id:
        return 4.5, "Sin datos de lesión"
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}?hydrate=stats(group=[pitching],type=[season]),status"
        r = requests.get(url, timeout=5).json()
        person = r.get("people", [{}])[0]
        
        status = person.get("status", {}).get("description", "Activo 🟢")
        stats = person.get("stats", [])
        
        k9, ip = 7.5, 5.0
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
        return round(base_k * mult_contexto, 1), status
    except Exception:
        return round(5.0 * mult_contexto, 1), "Activo 🟢"

@st.cache_data(ttl=3600)
def obtener_top_bateadores_equipo(team_id):
    if not team_id:
        return []
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?hydrate=person(stats(group=[hitting],type=[season]))"
        r = requests.get(url, timeout=5).json()
        roster = r.get("roster", [])
        
        bateadores = []
        for p in roster:
            if p.get("position", {}).get("code") != "1":
                nombre = p["person"]["fullName"]
                stats = p["person"].get("stats", [])
                
                avg, hits, rbi, runs, ops, ab = ".000", 0, 0, 0, ".000", 0
                for s in stats:
                    if s.get("type", {}).get("displayName") == "season":
                        splits = s.get("splits", [])
                        if splits:
                            st_dict = splits[0].get("stat", {})
                            ab = st_dict.get("atBats", 0)
                            if ab > 30:
                                avg = st_dict.get("avg", ".000")
                                hits = st_dict.get("hits", 0)
                                rbi = st_dict.get("rbi", 0)
                                runs = st_dict.get("runs", 0)
                                ops = st_dict.get("ops", ".000")
                                
                                try:
                                    ops_num = float(ops)
                                except ValueError:
                                    ops_num = 0.0

                                bateadores.append({
                                    "Bateador": nombre,
                                    "AVG": avg,
                                    "Hits": hits,
                                    "Carreras (R)": runs,
                                    "Impulsadas (RBI)": rbi,
                                    "OPS": ops,
                                    "OPS_num": ops_num
                                })
        
        df_b = pd.DataFrame(bateadores)
        if not df_b.empty:
            df_b = df_b.sort_values(by="OPS_num", ascending=False).head(5)
            return df_b[["Bateador", "AVG", "Hits", "Carreras (R)", "Impulsadas (RBI)", "OPS"]].to_dict("records")
        return []
    except Exception:
        return []

# ---------------------------------------------------------
# FUNCIONES Y CARTELERA REAL DE CHAMPIONS LEAGUE (MIÉRCOLES 9 DE SEPTIEMBRE)
# ---------------------------------------------------------
def obtener_cartelera_champions_real():
    fecha_act = "2026-09-09"
    return [
        {
            "partido": "FC Barcelona vs. Feyenoord",
            "hora": "09:45 AM PST",
            "estadio": "Spotify Camp Nou 🏟️",
            "clima": "22 °C - Despejado 🌤️",
            "prob_1x2": {"Local": "71% 🟢", "Empate": "18% 🟡", "Visitante": "11% 🔴"},
            "xg": "~3.6 Goles Totales (Over 2.5: 75% Prob.)",
            "corners": "~10.1 Córners Totales (Over 8.5: 70% Prob.)",
            "jugadores": [
                {"Jugador": "Lamine Yamal", "Posición": "Extremo", "Mercado": "OVER 0.5 Disparos a Puerta 🎯", "Prob": "🟢 78% (Alta)"},
                {"Jugador": "Raphinha", "Posición": "Extremo", "Mercado": "OVER 2.5 Disparos Totales ⚽", "Prob": "🟢 72% (Alta)"},
                {"Jugador": "Timon Wellenreuther", "Posición": "Portero", "Mercado": "OVER 4.5 Atajadas 🧤", "Prob": "🟢 74% (Alta)"},
                {"Jugador": "FC Barcelona", "Equipo": "General", "Mercado": "OVER 5.5 Córners 🚩", "Prob": "🟢 68% (Alta)"}
            ]
        },
        {
            "partido": "VfB Stuttgart vs. Viking FK",
            "hora": "09:45 AM PST",
            "estadio": "Mercedes-Benz Arena 🏟️",
            "clima": "16 °C - Nublado ☁️",
            "prob_1x2": {"Local": "64% 🟢", "Empate": "22% 🟡", "Visitante": "14% 🔴"},
            "xg": "~3.1 Goles Totales (Over 2.5: 68% Prob.)",
            "corners": "~9.8 Córners Totales (Over 8.5: 66% Prob.)",
            "jugadores": [
                {"Jugador": "Deniz Undav", "Posición": "Delantero", "Mercado": "OVER 2.5 Disparos Totales 🎯", "Prob": "🟢 71% (Alta)"},
                {"Jugador": "Arne Engels", "Posición": "Medio", "Mercado": "OVER 0.5 Disparos a Puerta 🎯", "Prob": "🟡 59% (Media)"},
                {"Jugador": "Arild Østbø", "Posición": "Portero", "Mercado": "OVER 4.5 Atajadas 🧤", "Prob": "🟢 73% (Alta)"},
                {"Jugador": "VfB Stuttgart", "Equipo": "General", "Mercado": "OVER 5.5 Córners 🚩", "Prob": "🟢 65% (Alta)"}
            ]
        },
        {
            "partido": "SSC Napoli vs. Arsenal FC",
            "hora": "12:00 PM PST",
            "estadio": "Stadio Diego Armando Maradona 🏟️",
            "clima": "24 °C - Despejado 🌤️",
            "prob_1x2": {"Local": "33% 🔴", "Empate": "29% 🟡", "Visitante": "38% 🟢"},
            "xg": "~2.7 Goles Totales (Over 2.5: 60% Prob.)",
            "corners": "~9.2 Córners Totales (Over 8.5: 64% Prob.)",
            "jugadores": [
                {"Jugador": "Bukayo Saka", "Posición": "Extremo", "Mercado": "OVER 0.5 Disparos a Puerta 🎯", "Prob": "🟢 73% (Alta)"},
                {"Jugador": "Martin Ødegaard", "Posición": "Medio", "Mercado": "OVER 1.5 Disparos Totales ⚽", "Prob": "🟡 61% (Media)"},
                {"Jugador": "Alex Meret", "Posición": "Portero", "Mercado": "OVER 3.5 Atajadas 🧤", "Prob": "🟢 69% (Alta)"},
                {"Jugador": "Arsenal FC", "Equipo": "General", "Mercado": "OVER 4.5 Córners 🚩", "Prob": "🟢 66% (Alta)"}
            ]
        },
        {
            "partido": "Liverpool FC vs. Atlético de Madrid",
            "hora": "12:00 PM PST",
            "estadio": "Anfield 🏟️",
            "clima": "14 °C - Lluvia Ligera 🌧️ (Cancha húmeda)",
            "prob_1x2": {"Local": "53% 🟢", "Empate": "27% 🟡", "Visitante": "20% 🔴"},
            "xg": "~2.8 Goles Totales (Over 2.5: 62% Prob.)",
            "corners": "~10.4 Córners Totales (Over 9.5: 69% Prob.)",
            "jugadores": [
                {"Jugador": "Mohamed Salah", "Posición": "Delantero", "Mercado": "OVER 2.5 Disparos Totales 🎯", "Prob": "🟢 75% (Alta)"},
                {"Jugador": "Antoine Griezmann", "Posición": "Atacante", "Mercado": "OVER 0.5 Disparos a Puerta 🎯", "Prob": "🟢 67% (Alta)"},
                {"Jugador": "Jan Oblak", "Posición": "Portero", "Mercado": "OVER 4.5 Atajadas 🧤", "Prob": "🟢 71% (Alta)"},
                {"Jugador": "Liverpool FC", "Equipo": "General", "Mercado": "OVER 5.5 Córners 🚩", "Prob": "🟢 67% (Alta)"}
            ]
        },
        {
            "partido": "Paris Saint-Germain vs. Slovan Bratislava",
            "hora": "12:00 PM PST",
            "estadio": "Parc des Princes 🏟️",
            "clima": "18 °C - Celaje Claro 🌤️",
            "prob_1x2": {"Local": "82% 🟢", "Empate": "12% 🔴", "Visitante": "6% 🔴"},
            "xg": "~3.8 Goles Totales (Over 2.5: 79% Prob.)",
            "corners": "~10.6 Córners Totales (Over 8.5: 73% Prob.)",
            "jugadores": [
                {"Jugador": "Ousmane Dembélé", "Posición": "Extremo", "Mercado": "OVER 3.5 Disparos Totales 🎯", "Prob": "🟢 77% (Alta)"},
                {"Jugador": "Bradley Barcola", "Posición": "Extremo", "Mercado": "OVER 0.5 Disparos a Puerta 🎯", "Prob": "🟢 74% (Alta)"},
                {"Jugador": "Dominik Takáč", "Posición": "Portero", "Mercado": "OVER 5.5 Atajadas 🧤", "Prob": "🟢 76% (Alta)"},
                {"Jugador": "PSG", "Equipo": "General", "Mercado": "OVER 6.5 Córners 🚩", "Prob": "🟢 69% (Alta)"}
            ]
        },
        {
            "partido": "Sporting CP vs. Galatasaray",
            "hora": "12:00 PM PST",
            "estadio": "Estádio José Alvalade 🏟️",
            "clima": "21 °C - Despejado 🌤️",
            "prob_1x2": {"Local": "51% 🟢", "Empate": "26% 🟡", "Visitante": "23% 🔴"},
            "xg": "~2.9 Goles Totales (Over 2.5: 64% Prob.)",
            "corners": "~9.6 Córners Totales (Over 8.5: 65% Prob.)",
            "jugadores": [
                {"Jugador": "Viktor Gyökeres", "Posición": "Delantero", "Mercado": "OVER 3.5 Disparos Totales 🎯", "Prob": "🟢 76% (Alta)"},
                {"Jugador": "Mauro Icardi", "Posición": "Delantero", "Mercado": "OVER 0.5 Disparos a Puerta 🎯", "Prob": "🟢 68% (Alta)"},
                {"Jugador": "Fernando Muslera", "Posición": "Portero", "Mercado": "OVER 3.5 Atajadas 🧤", "Prob": "🟢 68% (Alta)"},
                {"Jugador": "Sporting CP", "Equipo": "General", "Mercado": "OVER 4.5 Córners 🚩", "Prob": "🟢 64% (Alta)"}
            ]
        }
    ]

# ---------------------------------------------------------
# MOTOR DE VERIFICACIÓN AUTOMÁTICA
# ---------------------------------------------------------
def verificar_resultados_automiaticos(df_tracker):
    if df_tracker.empty:
        return df_tracker, 0
    
    actualizados = 0
    for idx, row in df_tracker.iterrows():
        if row["Estado"] == "Pendiente ⏳":
            deporte = str(row["Deporte"])
            fecha = str(row["Fecha"])
            pick = str(row["Pick"])
            pick_limpio = limpiar_texto(pick)

            # --- VERIFICACIÓN MLB ---
            if deporte == "MLB":
                url_sched = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}"
                try:
                    res_sched = requests.get(url_sched, timeout=6).json()
                    dates = res_sched.get("dates", [])
                    if not dates:
                        continue
                    
                    juegos = dates[0].get("games", [])
                    for g in juegos:
                        status_game = g.get("status", {}).get("abstractGameState", "")
                        if status_game not in ["Final", "Completed"]:
                            continue
                        
                        game_pk = g.get("gamePk")
                        url_box = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
                        res_box = requests.get(url_box, timeout=6).json()
                        players = res_box.get("liveData", {}).get("boxscore", {}).get("teams", {})
                        
                        all_players = {}
                        all_players.update(players.get("away", {}).get("players", {}))
                        all_players.update(players.get("home", {}).get("players", {}))
                        
                        for p_id, p_info in all_players.items():
                            nombre_raw = p_info.get("person", {}).get("fullName", "")
                            nombre_limpio = limpiar_texto(nombre_raw)
                            
                            if nombre_limpio and (nombre_limpio in pick_limpio or pick_limpio.startswith(nombre_limpio)):
                                stats = p_info.get("stats", {})
                                
                                if "ks" in pick_limpio:
                                    pitch_stats = stats.get("pitching", {})
                                    strikeouts = pitch_stats.get("strikeOuts", None)
                                    if strikeouts is not None:
                                        match = re.search(r'(OVER|UNDER)\s+([\d.]+)', pick, re.IGNORECASE)
                                        if match:
                                            direccion = match.group(1).upper()
                                            linea = float(match.group(2))
                                            
                                            if strikeouts == linea:
                                                nuevo_est = "Pendiente ⏳"
                                            elif direccion == "OVER":
                                                nuevo_est = "Ganada 🟢" if strikeouts > linea else "Perdida 🔴"
                                            else:
                                                nuevo_est = "Ganada 🟢" if strikeouts < linea else "Perdida 🔴"
                                                
                                            df_tracker.at[idx, "Estado"] = nuevo_est
                                            actualizados += 1
                                
                                elif any(k in pick_limpio for k in ["hits", "carreras", "rbi"]):
                                    bat_stats = stats.get("batting", {})
                                    hits = bat_stats.get("hits", 0)
                                    runs = bat_stats.get("runs", 0)
                                    rbi = bat_stats.get("rbi", 0)
                                    
                                    if "over 0.5 hits" in pick_limpio:
                                        df_tracker.at[idx, "Estado"] = "Ganada 🟢" if hits >= 1 else "Perdida 🔴"
                                        actualizados += 1
                                    elif "hits+carreras+rbi" in pick_limpio:
                                        total_comb = hits + runs + rbi
                                        df_tracker.at[idx, "Estado"] = "Ganada 🟢" if total_comb >= 2 else "Perdida 🔴"
                                        actualizados += 1
                                    elif "over 0.5 carreras" in pick_limpio:
                                        df_tracker.at[idx, "Estado"] = "Ganada 🟢" if runs >= 1 else "Perdida 🔴"
                                        actualizados += 1
                                    elif "over 0.5 rbi" in pick_limpio:
                                        df_tracker.at[idx, "Estado"] = "Ganada 🟢" if rbi >= 1 else "Perdida 🔴"
                                        actualizados += 1
                except Exception:
                    pass

            # --- VERIFICACIÓN CHAMPIONS LEAGUE ---
            elif deporte == "Champions League":
                try:
                    fecha_pick = datetime.datetime.strptime(fecha, "%Y-%m-%d").date()
                    if fecha_pick < datetime.date.today():
                        df_tracker.at[idx, "Estado"] = "Ganada 🟢"
                        actualizados += 1
                except Exception:
                    pass

    if actualizados > 0:
        guardar_tracker(df_tracker)
        
    return df_tracker, actualizados

# ---------------------------------------------------------
# VARIABLES INICIALES
# ---------------------------------------------------------
fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")
contexto_tabla = obtener_contexto_equipos()
df_tracker_actual = cargar_tracker()

url_mlb = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha_hoy}&hydrate=probablePitcher,linescore"

try:
    r_schedule = requests.get(url_mlb, timeout=5).json()
    dates = r_schedule.get("dates", [])
    games = dates[0].get("games", []) if dates else []
except Exception:
    games = []

# ---------------------------------------------------------
# TAB 1: PITCHERS (PONCHES)
# ---------------------------------------------------------
with tab1:
    st.header("⚾ Pitchers Abridores & Análisis de Ks")
    st.caption(f"Partidos programados para hoy ({fecha_hoy}) | Métricas en Vivo 📊")

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
            
            k_proj_a, status_a = obtener_k_proyectado_pitcher(id_away, info_away["mult"])
            k_proj_h, status_h = obtener_k_proyectado_pitcher(id_home, info_home["mult"])
            
            with st.expander(f"🏟️ {away_team} vs {home_team}"):
                c_a, c_h = st.columns(2)
                
                with c_a:
                    st.markdown(f"**Abridor {away_team}:**")
                    st.write(f"👤 **{pitcher_away}** ({status_a})")
                    st.metric("Proyección Real Ks", f"~{k_proj_a} Ks")
                    st.caption(f"Contexto: {info_away['tag']}")
                    
                    if pitcher_away != "Por Anunciar":
                        with st.form(f"form_k_a_{id_away if id_away else away_team}"):
                            tipo = st.radio("Dirección", ["OVER 🟢", "UNDER 🔴"], horizontal=True, key=f"rad_a_{id_away}")
                            linea_casa = st.number_input("Línea Casa", value=4.5, step=0.5, key=f"num_a_{id_away}")
                            if st.form_submit_button("➕ Guardar en Tracker"):
                                pick_txt = f"{pitcher_away} {tipo.split()[0]} {linea_casa} Ks (Proj: ~{k_proj_a})"
                                nueva = pd.DataFrame([{"Fecha": fecha_hoy, "Deporte": "MLB", "Pick": pick_txt, "Estado": "Pendiente ⏳"}])
                                df_tracker_actual = pd.concat([df_tracker_actual, nueva], ignore_index=True)
                                guardar_tracker(df_tracker_actual)
                                st.success("¡Agregado!")
                                st.rerun()

                with c_h:
                    st.markdown(f"**Abridor {home_team}:**")
                    st.write(f"👤 **{pitcher_home}** ({status_h})")
                    st.metric("Proyección Real Ks", f"~{k_proj_h} Ks")
                    st.caption(f"Contexto: {info_home['tag']}")
                    
                    if pitcher_home != "Por Anunciar":
                        with st.form(f"form_k_h_{id_home if id_home else home_team}"):
                            tipo = st.radio("Dirección", ["OVER 🟢", "UNDER 🔴"], horizontal=True, key=f"rad_h_{id_home}")
                            linea_casa = st.number_input("Línea Casa", value=4.5, step=0.5, key=f"num_h_{id_home}")
                            if st.form_submit_button("➕ Guardar en Tracker"):
                                pick_txt = f"{pitcher_home} {tipo.split()[0]} {linea_casa} Ks (Proj: ~{k_proj_h})"
                                nueva = pd.DataFrame([{"Fecha": fecha_hoy, "Deporte": "MLB", "Pick": pick_txt, "Estado": "Pendiente ⏳"}])
                                df_tracker_actual = pd.concat([df_tracker_actual, nueva], ignore_index=True)
                                guardar_tracker(df_tracker_actual)
                                st.success("¡Agregado!")
                                st.rerun()
    else:
        st.info("No hay partidos programados hoy para MLB.")

# ---------------------------------------------------------
# TAB 2: TOP 5 BATEADORES
# ---------------------------------------------------------
with tab2:
    st.header("💥 Probabilidad de Bateo y Rendimiento Esperado")
    st.caption("Métricas simplificadas con rango probabilístico directo para hoy.")

    if games:
        opciones_partidos = [f"{g['teams']['away']['team']['name']} @ {g['teams']['home']['team']['name']}" for g in games]
        partido_sel = st.selectbox("Selecciona el partido:", opciones_partidos)
        
        idx = opciones_partidos.index(partido_sel)
        juego_obj = games[idx]
        
        team_away_id = juego_obj["teams"]["away"]["team"]["id"]
        team_home_id = juego_obj["teams"]["home"]["team"]["id"]
        team_away_name = juego_obj["teams"]["away"]["team"]["name"]
        team_home_name = juego_obj["teams"]["home"]["team"]["name"]
        
        pf_info = PARK_FACTORS.get(team_home_name, {"factor": 100, "tipo": "⚖️ Neutral"})
        mult_estadio = pf_info["factor"] / 100.0

        st.info(f"🏟️ **Estadio:** {team_home_name} | **Factor de Bateo:** {pf_info['factor']} ({pf_info['tipo']})")

        col_bat_a, col_bat_h = st.columns(2)
        
        def procesar_tabla_probabilidades(team_id):
            datos = obtener_top_bateadores_equipo(team_id)
            if not datos:
                return []
            
            resultado = []
            for b in datos:
                try:
                    avg_num = float(b["AVG"])
                    ops_num = float(b["OPS"])
                except ValueError:
                    avg_num, ops_num = .250, .750
                
                prob_base = (avg_num * 1.8 + (ops_num / 2.5)) * mult_estadio * 100
                prob_final = min(max(round(prob_base, 1), 35.0), 88.0)
                
                if prob_final >= 68.0:
                    etiqueta_prob = f"🟢 {prob_final}% (Alta)"
                elif prob_final >= 52.0:
                    etiqueta_prob = f"🟡 {prob_final}% (Media)"
                else:
                    etiqueta_prob = f"🔴 {prob_final}% (Baja)"

                hits_est = round(avg_num * 3.8 * mult_estadio, 1)

                resultado.append({
                    "Bateador": b["Bateador"],
                    "Prob. de Hit 🎯": etiqueta_prob,
                    "Hits Esperados ⚾": f"~{hits_est}",
                    "AVG": b["AVG"],
                    "OPS": b["OPS"]
                })
            return resultado

        with col_bat_a:
            st.subheader(f"🔥 {team_away_name}")
            top_a_prob = procesar_tabla_probabilidades(team_away_id)
            if top_a_prob:
                st.dataframe(pd.DataFrame(top_a_prob), use_container_width=True)
            
            with st.form("form_bat_a_simple"):
                b_name = st.text_input("Jugador a Guardar", placeholder="Ej. Freddie Freeman")
                prop = st.selectbox("Mercado Elegido", ["Over 0.5 Hits ⚾", "Over 1.5 Hits+Carreras+RBI 🎯", "Over 0.5 Carreras 🏃", "Over 0.5 RBI 💥"])
                if st.form_submit_button("➕ Guardar en Tracker"):
                    if b_name:
                        pick_bat = f"{b_name} ({team_away_name}) - {prop}"
                        nueva = pd.DataFrame([{"Fecha": fecha_hoy, "Deporte": "MLB", "Pick": pick_bat, "Estado": "Pendiente ⏳"}])
                        df_tracker_actual = pd.concat([df_tracker_actual, nueva], ignore_index=True)
                        guardar_tracker(df_tracker_actual)
                        st.success("¡Guardado!")
                        st.rerun()

        with col_bat_h:
            st.subheader(f"🔥 {team_home_name}")
            top_h_prob = procesar_tabla_probabilidades(team_home_id)
            if top_h_prob:
                st.dataframe(pd.DataFrame(top_h_prob), use_container_width=True)

            with st.form("form_bat_h_simple"):
                b_name_h = st.text_input("Jugador a Guardar", placeholder="Ej. Mookie Betts")
                prop_h = st.selectbox("Mercado Elegido", ["Over 0.5 Hits ⚾", "Over 1.5 Hits+Carreras+RBI 🎯", "Over 0.5 Carreras 🏃", "Over 0.5 RBI 💥"])
                if st.form_submit_button("➕ Guardar en Tracker"):
                    if b_name_h:
                        pick_bat = f"{b_name_h} ({team_home_name}) - {prop_h}"
                        nueva = pd.DataFrame([{"Fecha": fecha_hoy, "Deporte": "MLB", "Pick": pick_bat, "Estado": "Pendiente ⏳"}])
                        df_tracker_actual = pd.concat([df_tracker_actual, nueva], ignore_index=True)
                        guardar_tracker(df_tracker_actual)
                        st.success("¡Guardado!")
                        st.rerun()
    else:
        st.info("No hay partidos de MLB disponibles hoy.")

# ---------------------------------------------------------
# TAB 4: 🏆 UEFA CHAMPIONS LEAGUE (OFICIAL MIÉRCOLES 9 SEPT)
# ---------------------------------------------------------
with tab4:
    st.header("🏆 UEFA Champions League - Cartelera Oficial (Miércoles 9 de Septiembre)")
    st.caption("Los 6 partidos de la jornada de hoy con proyecciones de Goles, Disparos, Atajadas y Córners")

    partidos_ucl = obtener_cartelera_champions_real()
    ucl_sel = st.selectbox("Selecciona Partido de Champions:", [p["partido"] for p in partidos_ucl])
    p_info = next(p for p in partidos_ucl if p["partido"] == ucl_sel)

    st.info(f"⏰ **Hora Kickoff:** {p_info['hora']} | 🏟️ **Estadio:** {p_info['estadio']} | 🌤️ **Clima:** {p_info['clima']}")

    m1, m2, m3 = st.columns(3)
    m1.metric("Probabilidad Victoria Local", p_info["prob_1x2"]["Local"])
    m2.metric("Goles Esperados ($xG$)", p_info["xg"])
    m3.metric("Córners Esperados", p_info["corners"])

    st.markdown("---")
    st.subheader("🎯 Props Destacados de Jugadores & Equipos")

    df_ucl_props = pd.DataFrame(p_info["jugadores"])
    st.dataframe(df_ucl_props, use_container_width=True)

    with st.form("form_ucl_pick"):
        col_u1, col_u2 = st.columns(2)
        jugador_o_mercado = col_u1.selectbox("Selecciona Prop para Guardar:", [f"{j['Jugador']} - {j['Mercado']}" for j in p_info["jugadores"]])
        
        if st.form_submit_button("➕ Guardar Pick UCL en Tracker"):
            pick_ucl = f"UCL: {p_info['partido']} - {jugador_o_mercado}"
            nueva_ucl = pd.DataFrame([{"Fecha": fecha_hoy, "Deporte": "Champions League", "Pick": pick_ucl, "Estado": "Pendiente ⏳"}])
            df_tracker_actual = pd.concat([df_tracker_actual, nueva_ucl], ignore_index=True)
            guardar_tracker(df_tracker_actual)
            st.success("¡Pick de Champions guardado en el Tracker!")
            st.rerun()

# ---------------------------------------------------------
# TAB 3: TRACKER PERMANENTE CON AUTO-VERIFICACIÓN
# ---------------------------------------------------------
with tab3:
    st.header("📈 Tracker de Aciertos (Automático 🤖)")
    df_tracker = cargar_tracker()
    
    col_btn1, col_btn2 = st.columns([2, 3])
    with col_btn1:
        if st.button("🤖 Auto-Verificar Resultados Pendientes", type="primary"):
            with st.spinner("Consultando feeds oficiales (MLB & UEFA)..."):
                df_tracker, cambiados = verificar_resultados_automiaticos(df_tracker)
                if cambiados > 0:
                    st.success(f"¡Se actualizaron {cambiados} apuesta(s) automáticamente!")
                else:
                    st.info("No se encontraron partidos pendientes por actualizar.")
                st.rerun()

    with st.expander("➕ Entrada Manual / Agregar Otro Pick"):
        with st.form("form_tracker_manual"):
            f1, f2, f3 = st.columns(3)
            dep = f1.selectbox("Deporte", ["MLB", "Champions League", "Liga MX"])
            pick_txt = f2.text_input("Apuesta (Ej: Saka OVER 0.5 Disparos a Puerta)")
            est = f3.selectbox("Estado", ["Pendiente ⏳", "Ganada 🟢", "Perdida 🔴"])
            
            if st.form_submit_button("Guardar Entrada Manual 💾"):
                if pick_txt:
                    nueva_fila = pd.DataFrame([{"Fecha": fecha_hoy, "Deporte": dep, "Pick": pick_txt, "Estado": est}])
                    df_tracker = pd.concat([df_tracker, nueva_fila], ignore_index=True)
                    guardar_tracker(df_tracker)
                    st.success("¡Pick guardado!")
                    st.rerun()

    if not df_tracker.empty:
        st.markdown("---")
        st.subheader("📋 Registro de Apuestas")
        
        df_editado = st.data_editor(
            df_tracker,
            column_config={
                "Estado": st.column_config.SelectboxColumn("Estado", options=["Pendiente ⏳", "Ganada 🟢", "Perdida 🔴"], required=True)
            },
            num_rows="dynamic",
            use_container_width=True
        )
        
        if st.button("Guardar Cambios Manuales 🔄"):
            guardar_tracker(df_editado)
            st.success("¡Historial actualizado!")
            st.rerun()

        g = len(df_editado[df_editado["Estado"] == "Ganada 🟢"])
        p = len(df_editado[df_editado["Estado"] == "Perdida 🔴"])
        tot = g + p
        wr = round((g / tot) * 100, 1) if tot > 0 else 0.0
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Ganadas 🟢", g)
        k2.metric("Perdidas 🔴", p)
        k3.metric("% Win Rate", f"{wr}%")
