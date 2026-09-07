# ---------------------------------------------------------
# TAB 2: TOP 5 BATEADORES (RANGOS DE PROBABILIDAD SIMPLIFICADOS)
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
        
        # Función interna para calcular probabilidad simplificada
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
                
                # Algoritmo de probabilidad ajustada por estadio y OPS
                prob_base = (avg_num * 1.8 + (ops_num / 2.5)) * mult_estadio * 100
                prob_final = min(max(round(prob_base, 1), 35.0), 88.0) # Acotado entre 35% y 88%
                
                if prob_final >= 68.0:
                    etiqueta_prob = f"🟢 {prob_final}% (Alta)"
                elif prob_final >= 52.0:
                    etiqueta_prob = f"🟡 {prob_final}% (Media)"
                else:
                    etiqueta_prob = f"🔴 {prob_final}% (Baja)"

                # Estimado aproximado de producción
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
