import streamlit as st
import pandas as pd
import config
import sniper_engine
import time

# --- SETUP ---
st.set_page_config(page_title="Sniper V3 Pro", page_icon="🦅", layout="wide")
st.markdown("""<style>.stApp { background-color: #0E1117; color: #FAFAFA; }</style>""", unsafe_allow_html=True)

# --- MEMORIA (Usa Session State per il Cloud) ---
if 'df_hist' not in st.session_state:
    st.session_state.df_hist = pd.DataFrame(columns=["Sport", "Data", "Match", "Selezione", "Q_Betfair", "Rating", "Stake_Ready", "Esito", "Profitto"])
if 'df_pend' not in st.session_state:
    st.session_state.df_pend = pd.DataFrame()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🦅 SNIPER V3 CLOUD")
    st.caption("Football Stats + Tennis Ranking")
    st.markdown("---")
    menu = st.radio("MENU", ["RADAR", "REGISTRO"])
    st.markdown("---")
    
    if st.button("🔄 SCANNER V3 (LIVE)", type="primary"):
        with st.spinner("Scaricamento Ranking ATP & Quote Calcio..."):
            c = sniper_engine.run_football_scan(config.BANKROLL_INIZIALE)
            t = sniper_engine.run_tennis_scan(config.BANKROLL_INIZIALE)
            tot = c + t
            st.session_state.df_pend = pd.DataFrame(tot)
            st.success(f"Scansione Completa! Trovate {len(tot)} occasioni.")
            time.sleep(1)
            st.rerun()

# --- RADAR ---
if menu == "RADAR":
    st.header("📡 RADAR V3: Mercato in Tempo Reale")
    if not st.session_state.df_pend.empty:
        edited = st.data_editor(st.session_state.df_pend, hide_index=True, use_container_width=True,
            column_config={
                "Abbinata": st.column_config.CheckboxColumn("✅ FATTA?"),
                "Rating": st.column_config.TextColumn("QUALITÀ"),
                "Q_Betfair": st.column_config.NumberColumn("QUOTA", format="%.2f"),
                "Q_Reale": st.column_config.NumberColumn("PINNA", format="%.2f"),
                "Edge%": st.column_config.ProgressColumn("VANTAGGIO", min_value=0, max_value=10, format="%.1f%%"),
                "Stake_Ready": st.column_config.NumberColumn("STAKE", format="%d€"),
            })
        
        if st.button("CONFERMA GIOCATE"):
            fatte = edited[edited['Abbinata']==True].copy()
            if not fatte.empty:
                fatte['Esito'] = "PENDING"
                fatte['Profitto'] = 0.0
                st.session_state.df_hist = pd.concat([st.session_state.df_hist, fatte], ignore_index=True)
                # Pulisce Radar
                st.session_state.df_pend = edited[edited['Abbinata']==False]
                st.balloons()
                st.rerun()
    else:
        st.info("Radar vuoto. Premi il tasto SCANNER V3 nella barra laterale.")

# --- REGISTRO ---
elif menu == "REGISTRO":
    st.header("📝 Diario Operativo")
    if not st.session_state.df_hist.empty:
        st.dataframe(st.session_state.df_hist, use_container_width=True)
    else: st.info("Nessuna scommessa registrata.")
