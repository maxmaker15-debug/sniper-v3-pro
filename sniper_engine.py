import requests
import config
from datetime import datetime, timedelta
import time

# --- UTILITIES ---
def calculate_kelly(true_prob, decimal_odd, bankroll):
    if decimal_odd <= 1.01: return 0
    net_odd = 1 + ((decimal_odd - 1) * (1 - config.COMMISSIONE_BETFAIR))
    b = net_odd - 1
    q = 1 - true_prob
    f = (b * true_prob - q) / b
    raw_stake = bankroll * f * config.KELLY_FRACTION
    if raw_stake < config.STAKE_MIN: return 0
    if raw_stake > config.STAKE_MAX: return int(config.STAKE_MAX)
    return int(raw_stake)

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": config.TELEGRAM_CHAT_ID, "text": message})
    except: pass

# --- FUNZIONE SPECIALE: PRELIEVO DATI ON-DEMAND ---
def get_player_predictive_stats(player_id, surface_filter):
    """
    Scarica le statistiche REALI 2025 del giocatore solo quando serve.
    Restituisce il 'Dominance Ratio' (Service% + Return%).
    """
    if not player_id: return None
    
    current_year = datetime.now().year
    # Se siamo a inizio anno, potremmo voler guardare anche l'anno scorso
    season = current_year 
    
    try:
        headers = {'x-apisports-key': config.TENNIS_API_KEY}
        url = f"https://api.tennis.api-sports.io/players/statistics"
        params = {"season": season, "id": player_id}
        
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200: return None
        
        data = resp.json().get('response', [])
        
        total_points_won = 0
        matches_count = 0
        service_points_won_pct = 0
        return_points_won_pct = 0
        
        # Cerchiamo le stats generali o filtrate per superficie
        found_surface = False
        
        for stat_block in data:
            # Se riusciamo a filtrare per superficie è meglio (es. Hard)
            raw_surf = stat_block.get('surface', '').lower()
            if surface_filter.lower() in raw_surf:
                matches_count = stat_block.get('games', {}).get('appearences', 0)
                if matches_count > 0:
                    # Estrazione Dati Predittivi
                    # Nota: L'API Free a volte ha dati parziali, usiamo Points Won
                    # Calcoliamo una media pesata se possibile
                    # Qui semplifichiamo usando i dati generici forniti
                    # API-Sports free fornisce dati aggregati complessi, usiamo win% generico come proxy
                    # se mancano i punti precisi
                    
                    # Logica Semplificata per API-Sports Structure:
                    # Service Games Won %
                    srv_games_won = stat_block.get('games', {}).get('service_games_won', 0)
                    srv_games_total = stat_block.get('games', {}).get('service_games_played', 0)
                    
                    if srv_games_total > 0:
                        service_points_won_pct = (srv_games_won / srv_games_total) * 100
                    
                    # Per la risposta è più difficile averlo diretto, usiamo break points converted
                    # come proxy di aggressività
                    bp_conv = stat_block.get('break_points', {}).get('converted', 0)
                    bp_total = stat_block.get('break_points', {}).get('attempted', 0)
                    if bp_total > 0:
                        return_points_won_pct = (bp_conv / bp_total) * 100 # Questo è BP Conversion, non Return Points, ma è predittivo
                    
                    found_surface = True
                    break
        
        # Se non troviamo la superficie specifica, prendiamo il dato "All" (totale)
        if not found_surface and len(data) > 0:
            stat_block = data[0]
            srv_games_won = stat_block.get('games', {}).get('service_games_won', 0)
            srv_games_total = stat_block.get('games', {}).get('service_games_played', 0)
            if srv_games_total > 0:
                service_points_won_pct = (srv_games_won / srv_games_total) * 100
        
        # CREAZIONE DEL DOMINANCE INDEX
        # Service Hold % (Media ATP ~80%) + Break % (Media ATP ~20%) = 100
        # Se un giocatore ha Hold 90% e Break 30% = 120 (MOSTRO)
        dominance_index = service_points_won_pct + (return_points_won_pct / 2) # Pesiamo diversamente i BP
        
        return {
            "Hold%": round(service_points_won_pct, 1),
            "Break_Conv%": round(return_points_won_pct, 1),
            "Dominance": round(dominance_index, 1),
            "Matches": matches_count
        }

    except Exception as e:
        print(f"Err Stats: {e}")
        return None

# --- MOTORE CALCIO (Invariato) ---
def run_football_scan(bankroll):
    print("⚽ Scansione Calcio...")
    found_bets = []
    dates = [datetime.now().strftime("%Y-%m-%d"), (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")]
    for d in dates:
        try:
            url = f"https://api.sportmonks.com/v3/football/fixtures/date/{d}"
            resp = requests.get(url, params={"api_token": config.SPORTMONKS_TOKEN, "include": "league;participants;odds"})
            if resp.status_code != 200: continue
            fixtures = resp.json().get('data', [])
            for fix in fixtures:
                lname = fix.get('league', {}).get('name', 'Unknown')
                if not any(x in lname for x in config.LEAGUES_CALCIO): continue
                name = fix.get('name')
                start_str = fix.get('starting_at', d)
                odds = fix.get('odds', [])
                pinna, bf = {}, {}
                for o in odds:
                    if str(o['market_id']) == '1':
                        try:
                            val = float(o['value'])
                            label = o['label'].lower()
                            bid = str(o['bookmaker_id'])
                            key = None
                            if label in ['1', 'home']: key = '1'
                            if label in ['2', 'away']: key = '2'
                            if key:
                                if bid == '2': pinna[key] = val
                                if bid in ['1', '6', '16']: bf[key] = val
                        except: pass
                if not bf: continue
                for sel in ['1', '2']:
                    if sel not in bf or sel not in pinna: continue
                    q_bf, q_pinna = bf[sel], pinna[sel]
                    if not (config.STRATEGY_CALCIO['QUOTA_MIN'] <= q_bf <= config.STRATEGY_CALCIO['QUOTA_MAX']): continue
                    trend_diff = (1 - (q_pinna / q_bf)) * 100
                    if trend_diff < config.STRATEGY_CALCIO['MIN_EDGE']: continue
                    rating = "⭐⭐ GOOD"
                    if trend_diff > 4.0: rating = "⭐⭐⭐ STRONG"
                    stake = calculate_kelly(1/q_pinna, q_bf, bankroll)
                    if stake > 0:
                        msg = f"⚽ CALCIO: {name} ({sel})\nQ: {q_bf} | Edge: {trend_diff:.1f}%\nStake: {stake}€"
                        send_telegram(msg)
                        found_bets.append({
                            "Sport": "CALCIO", "Data": start_str, "Match": name, "Selezione": "CASA" if sel=='1' else "OSPITE",
                            "Q_Betfair": q_bf, "Q_Reale": q_pinna, "Rating": rating, "Edge%": round(trend_diff, 1), "Stake_Ready": stake, "Abbinata": False
                        })
        except Exception: pass
    return found_bets

# --- MOTORE TENNIS PREDITTIVO (V7 - LIVE DATA MINING) ---
def run_tennis_scan(bankroll):
    print("🎾 Scansione Tennis Predittivo (V7)...")
    found_bets = []
    
    # 1. MAPPING ID GIOCATORI
    # Scarichiamo il programma e salviamo ID e Superficie
    today = datetime.now().strftime("%Y-%m-%d")
    players_map = {} # Nome -> {ID, Superficie}
    
    try:
        headers = {'x-apisports-key': config.TENNIS_API_KEY}
        url = f"https://api.tennis.api-sports.io/games?date={today}"
        resp = requests.get(url, headers=headers)
        
        if resp.status_code == 200:
            games = resp.json().get('response', [])
            for g in games:
                cat = g.get('tournament', {}).get('category', {}).get('name', '')
                if 'ATP' not in cat and 'WTA' not in cat: continue
                
                raw_surface = g.get('tournament', {}).get('surface', 'Unknown')
                surface = "Hard" # Default
                if "Clay" in raw_surface: surface = "Clay"
                elif "Grass" in raw_surface: surface = "Grass"
                elif "Indoor" in raw_surface: surface = "Indoor"
                
                p1 = g.get('players', [])[0]
                p2 = g.get('players', [])[1]
                
                if p1.get('id') and p1.get('name'):
                    players_map[p1.get('name')] = {'id': p1.get('id'), 'surface': surface, 'rank': p1.get('rank')}
                if p2.get('id') and p2.get('name'):
                    players_map[p2.get('name')] = {'id': p2.get('id'), 'surface': surface, 'rank': p2.get('rank')}
                    
    except Exception as e: 
        print(f"Err Mapping: {e}")
        return []

    # 2. SCANSIONE QUOTE (Il Trigger)
    try:
        resp = requests.get('https://api.the-odds-api.com/v4/sports', params={'apiKey': config.ODDS_API_KEY})
        leagues = [s for s in resp.json() if 'tennis' in s['key'].lower() and 'winner' not in s['key']]
        
        # Limitiamo le leghe per non finire le chiamate
        for league in leagues[:3]: 
            resp = requests.get(f'https://api.the-odds-api.com/v4/sports/{league["key"]}/odds', 
                              params={'apiKey': config.ODDS_API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'})
            if resp.status_code != 200: continue
            
            for ev in resp.json():
                home, away = ev['home_team'], ev['away_team']
                match_label = f"{home} vs {away}"
                
                # Cerchiamo le quote
                pinna, bf = {}, {}
                for b in ev['bookmakers']:
                    if b['key'] == 'pinnacle': 
                        for o in b['markets'][0]['outcomes']: pinna[o['name']] = o['price']
                    if b['key'] in ['betfair_ex_eu', 'betfair', 'bet365']:
                         for o in b['markets'][0]['outcomes']: bf[o['name']] = o['price']
                
                if not pinna or not bf: continue
                margin = sum([1/x for x in pinna.values()])

                for player in pinna:
                    if player not in bf: continue
                    q_bf, q_pinna = bf[player], pinna[player]
                    
                    # 1. FILTRO QUOTA INIZIALE (Non chiamare API se la quota fa schifo)
                    trend_diff = (1 - (q_pinna / q_bf)) * 100
                    if trend_diff < 0.5: continue # Se non c'è minimo valore, passa oltre
                    
                    # 2. IDENTIFICAZIONE GIOCATORE (Fuzzy Match)
                    player_data = None
                    opponent_name = away if player == home else home
                    opponent_data = None
                    
                    for api_name, data in players_map.items():
                        if player.split()[-1] in api_name: player_data = data
                        if opponent_name.split()[-1] in api_name: opponent_data = data
                    
                    if not player_data: continue # Non abbiamo l'ID, non possiamo analizzare
                    
                    # 3. ON-DEMAND DATA MINING (Qui spendiamo la chiamata API)
                    # Scarichiamo le stats solo se potenzialmente interessante
                    print(f"   🔎 Analisi profonda per {player}...")
                    
                    p_stats = get_player_predictive_stats(player_data['id'], player_data['surface'])
                    # Facoltativo: scaricare anche avversario, ma costa doppio.
                    # Per ora ci basiamo sulla forza intrinseca del nostro cavallo.
                    
                    if not p_stats: continue # Dati non disponibili
                    
                    # 4. IL CALCOLO PREDITTIVO
                    # Un giocatore solido deve tenere il servizio > 75%
                    is_solid_server = p_stats['Hold%'] > 75.0
                    dominance = p_stats['Dominance']
                    
                    # Rating Basato sui Dati
                    rating = "⚪ NEUTRAL"
                    predictive_boost = False
                    
                    if dominance > 100.0: # Giocatore Dominante
                        rating = f"🚀 DOMINANT (Score {dominance})"
                        predictive_boost = True
                    elif p_stats['Hold%'] > 85.0 and player_data['surface'] in ['Grass', 'Indoor']:
                        rating = f"🛡️ UNBREAKABLE ({p_stats['Hold%']}%)"
                        predictive_boost = True
                    elif dominance < 85.0:
                        # Giocatore scarso, evitiamo anche se la quota è buona
                        print(f"   ❌ Scartato {player}: Stats troppo basse ({dominance})")
                        continue

                    # 5. CALCOLO FINALE
                    prob_reale = (1/q_pinna) / margin
                    ev = (prob_reale * q_bf - 1) * 100
                    
                    # Se i dati confermano la bontà, abbassiamo la soglia di EV richiesta
                    min_edge_required = config.STRATEGY_TENNIS['MIN_EDGE']
                    if predictive_boost: min_edge_required = 1.0 # Ci accontentiamo di meno margine se è forte
                    
                    if ev >= min_edge_required:
                        stake = calculate_kelly(prob_reale, q_bf, bankroll)
                        if predictive_boost: stake = int(stake * 1.2) # Boost Stake
                        
                        if stake > 0:
                            msg = f"🎾 PREDICTION: {player}\nStats: {rating}\nHold: {p_stats['Hold%']}% | Q: {q_bf}\nStake: {stake}€"
                            send_telegram(msg)
                            found_bets.append({
                                "Sport": "TENNIS", "Data": ev['commence_time'], "Match": match_label,
                                "Selezione": player, "Q_Betfair": q_bf, "Q_Reale": q_pinna,
                                "Rating": rating, "Edge%": round(ev, 1), "Stake_Ready": stake, "Abbinata": False
                            })

    except Exception as e: print(f"Err Tennis V7: {e}")
    return found_bets
