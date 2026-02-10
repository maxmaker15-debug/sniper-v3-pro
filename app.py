import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import config
import sniper_engine
import time
from datetime import datetime

# --- SETUP ---
st.set_page_config(page_title="Sniper V3 Pro", page_icon="🦅", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    div[data-testid="stMetric"] { background-color: #262730; border-radius: 10px; padding: 10px; border: 1px solid #41444C; }
    </style>
""", unsafe_allow_html=True)

# --- MEMORIA CLOUD ---
if 'df_hist' not in st.session_state:
    # Simulazione dati storici per vedere i grafici subito (puoi toglierlo dopo)
    # st.session_state.df_hist = pd.DataFrame([
    #    {"Sport": "CALCIO", "Data": "2024-02-10", "Match": "Test A", "Selezione": "1", "Q_Betfair": 2.10, "Rating": "⭐⭐ GOOD", "Stake_Ready": 50, "Esito": "WIN", "Profitto": 52.5},
    #    {"Sport": "TENNIS", "Data": "2024-02-10", "Match": "Test B", "Selezione": "P1", "Q_Betfair": 1.80, "Rating": "💎 GEM", "Stake_Ready": 100, "Esito": "LOSS", "Profitto": -100}
    # ])
    st.session_state.df_hist = pd.DataFrame(columns=["Sport", "Data", "Match", "Selezione", "Q_Betfair", "Rating", "Stake_Ready", "Esito", "Profitto"])

if 'df_pend' not in st.session_state:
    st.session_state.df_pend = pd.DataFrame()

# --- CALCOLO KPI LIVE ---
df = st.session_state.df_hist
profitto_netto = df['Profitto'].sum() if not df.empty else 0.0
capitale_attuale = config.BANKROLL_INIZIALE + profitto_netto
roi = (profitto_netto / df['Stake_Ready'].sum() * 100) if not df.empty and df['Stake_Ready'].sum() > 0 else 0.0
roe = (profitto_netto / config.BANKROLL_INIZIALE * 100)
win_rate = (len(df[df['Esito']=='WIN']) / len(df) * 100) if not df.empty else 0.0

# --- SIDEBAR ---
with st.sidebar:
    st.title("🦅 SNIPER V3")
    st.caption("Professional Algo-Suite")
    st.markdown("---")
    
    # Menu Navigazione Aggiornato
    menu = st.radio("NAVIGAZIONE", ["DASHBOARD (Stats)", "RADAR (Scanner)", "REGISTRO (Diario)"])
    
    st.markdown("---")
    st.metric("BANKROLL", f"{capitale_attuale:.2f} €", delta=f"{profitto_netto:.2f} €")
    
    st.markdown("### ⚡ Azioni Rapide")
    if st.button("🔄 AVVIA SCANNER V3", type="primary"):
        with st.spinner("⏳ Analisi Calcio & Tennis in corso..."):
            # Reset Radar
            st.session_state.df_pend = pd.DataFrame()
            
            # Scansione
            c = sniper_engine.run_football_scan(capitale_attuale)
            t = sniper_engine.run_tennis_scan(capitale_attuale)
            
            tot = c + t
            
            # Feedback Utente
            if not tot:
                st.warning("Nessuna opportunità trovata adesso.")
            else:
                st.session_state.df_pend = pd.DataFrame(tot)
                st.success(f"Trovate {len(tot)} opportunità!")
            
            time.sleep(1)
            st.rerun()

# --- 1. DASHBOARD ANALITICA ---
if menu == "DASHBOARD (Stats)":
    st.header("📊 Performance Analytics")
    
    # KPI ROW 1
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("PROFITTO NETTO", f"{profitto_netto:.2f} €", delta_color="normal")
    c2.metric("ROI (Yield)", f"{roi:.2f} %", help="Ritorno sull'investito")
    c3.metric("ROE (Bankroll)", f"{roe:.2f} %", help="Crescita del capitale totale")
    c4.metric("WIN RATE", f"{win_rate:.1f} %")

    if not df.empty:
        st.markdown("---")
        
        # GRAFICI ROW 2
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.subheader("📈 Equity Curve (Crescita Capitale)")
            # Crea curva cumulata
            chart_data = df.copy()
            chart_data['Progressivo'] = config.BANKROLL_INIZIALE + chart_data['Profitto'].cumsum()
            chart_data['Numero_Bet'] = range(1, len(chart_data) + 1)
            
            fig = px.line(chart_data, x='Numero_Bet', y='Progressivo', markers=True, 
                          title='Andamento Bankroll nel Tempo')
            fig.update_layout(xaxis_title="Numero Scommesse", yaxis_title="Capitale (€)")
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.subheader("🍰 Asset Allocation")
            if 'Sport' in df.columns:
                fig_pie = px.pie(df, names='Sport', values='Stake_Ready', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Dati insufficienti per il grafico a torta.")

        # GRAFICI ROW 3
        c5, c6 = st.columns(2)
        with c5:
            st.subheader("💰 Profitto per Sport")
            sport_pnl = df.groupby('Sport')['Profitto'].sum().reset_index()
            fig_bar = px.bar(sport_pnl, x='Sport', y='Profitto', color='Profitto', 
                             color_continuous_scale=['red', 'green'])
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with c6:
            st.subheader("🎯 Rating Performance")
            if 'Rating' in df.columns:
                rating_pnl = df.groupby('Rating')['Profitto'].sum().reset_index()
                fig_rate = px.bar(rating_pnl, x='Rating', y='Profitto')
                st.plotly_chart(fig_rate, use_container_width=True)

    else:
        st.info("👋 Benvenuto in Sniper V3! Il database è vuoto.")
        st.info("Vai su 'RADAR', avvia lo scanner e inizia a registrare le tue prime operazioni per vedere i grafici.")

# --- 2. RADAR (SCANNER) ---
elif menu == "RADAR (Scanner)":
    st.header("📡 Radar Mercato")
    st.caption("Motori Attivi: Calcio V3 (Stats) | Tennis V3 (Ranking Gap)")
    
    if not st.session_state.df_pend.empty:
        # Tabella Interattiva
        edited = st.data_editor(st.session_state.df_pend, hide_index=True, use_container_width=True,
            column_config={
                "Abbinata": st.column_config.CheckboxColumn("✅ FATTA?", help="Spunta per spostare nel registro"),
                "Rating": st.column_config.TextColumn("QUALITÀ"),
                "Q_Betfair": st.column_config.NumberColumn("QUOTA", format="%.2f"),
                "Q_Reale": st.column_config.NumberColumn("PINNA", format="%.2f"),
                "Edge%": st.column_config.ProgressColumn("VANTAGGIO", min_value=0, max_value=10, format="%.1f%%"),
                "Stake_Ready": st.column_config.NumberColumn("STAKE", format="%d€"),
            })
        
        col_a, col_b = st.columns(2)
        if col_a.button("REGISTRA SELEZIONATE", type="primary"):
            fatte = edited[edited['Abbinata']==True].copy()
            if not fatte.empty:
                # Inizializza campi per registro
                fatte['Esito'] = "PENDING"
                fatte['Profitto'] = 0.0
                # Aggiungi allo storico
                st.session_state.df_hist = pd.concat([st.session_state.df_hist, fatte], ignore_index=True)
                # Rimuovi dal radar
                st.session_state.df_pend = edited[edited['Abbinata']==False]
                st.balloons()
                st.success("Scommesse registrate nel Diario!")
                time.sleep(1)
                st.rerun()
                
        if col_b.button("🗑️ SVUOTA RADAR"):
            st.session_state.df_pend = pd.DataFrame()
            st.rerun()
            
    else:
        st.info("Il Radar è vuoto. Premi 'AVVIA SCANNER V3' nella barra laterale.")

# --- 3. REGISTRO (DIARIO) ---
elif menu == "REGISTRO (Diario)":
    st.header("📝 Diario delle Operazioni")
    
    if not st.session_state.df_hist.empty:
        # Editor modificabile
        edited_hist = st.data_editor(st.session_state.df_hist, hide_index=True, use_container_width=True,
            column_config={
                "Esito": st.column_config.SelectboxColumn("ESITO", options=["PENDING", "WIN", "LOSS", "VOID"], required=True),
                "Profitto": st.column_config.NumberColumn("P&L (€)", format="%.2f€"),
                "Stake_Ready": st.column_config.NumberColumn("STAKE", format="%d€"),
            })
        
        if st.button("💾 SALVA AGGIORNAMENTI"):
            # Logica calcolo P&L automatico
            for index, row in edited_hist.iterrows():
                if row['Esito'] == 'WIN' and row['Profitto'] == 0:
                    lordo = row['Stake_Ready'] * row['Q_Betfair']
                    netto = (lordo - row['Stake_Ready']) * (1 - config.COMMISSIONE_BETFAIR)
                    edited_hist.at[index, 'Profitto'] = round(netto, 2)
                elif row['Esito'] == 'LOSS':
                    edited_hist.at[index, 'Profitto'] = -row['Stake_Ready']
                elif row['Esito'] == 'VOID':
                    edited_hist.at[index, 'Profitto'] = 0.0
            
            st.session_state.df_hist = edited_hist
            st.success("Registro aggiornato e profitti ricalcolati!")
            time.sleep(0.5)
            st.rerun()
            
    else:
        st.info("Il registro è ancora vuoto. Vai al Radar e conferma qualche giocata.")
