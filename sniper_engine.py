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

# --- MOTORE CALCIO (V2 - Invariato) ---
def run_football_scan(bankroll):
    print("⚽ Avvio Scansione Calcio V3...")
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
                    q_bf = bf[sel]
                    q_pinna = pinna[sel]
                    
                    if not (config.STRATEGY_CALCIO['QUOTA_MIN'] <= q_bf <= config.STRATEGY_CALCIO['QUOTA_MAX']): continue
                    
                    trend_diff = (1 - (q_pinna / q_bf)) * 100
                    if trend_diff < config.STRATEGY_CALCIO['MIN_EDGE']: continue
                    
                    rating = "⭐⭐ GOOD"
                    if trend_diff > 4.0: rating = "⭐⭐⭐ STRONG"
                    
                    prob_impl = 1 / q_pinna
                    stake = calculate_kelly(prob_impl, q_bf, bankroll)
                    
                    if stake > 0:
                        msg = f"⚽ CALCIO: {name} ({sel})\nQuota: {q_bf} | Edge: {trend_diff:.1f}%\nStake: {stake}€"
                        send_telegram(msg)
                        
                        found_bets.append({
                            "Sport": "CALCIO", "Data": start_str, "Match": name,
                            "Selezione": "CASA" if sel == '1' else "OSPITE",
                            "Q_Betfair": q_bf, "Q_Reale": q_pinna, "Rating": rating,
                            "Edge%": round(trend_diff, 1), "Stake_Ready": stake, "Abbinata": False
                        })
        except Exception: pass
    return found_bets

# --- MOTORE TENNIS (V3 - CLASSIFICA ATP) ---
def run_tennis_scan(bankroll):
    print("🎾 Avvio Scansione Tennis V3...")
    found_bets = []
    
    # 1. SCARICA DATI CLASSIFICA (API-TENNIS)
    today = datetime.now().strftime("%Y-%m-%d")
    matches_info = {} 
    
    try:
        headers = {'x-apisports-key': config.TENNIS_API_KEY}
        # Nota: API-Tennis free ha limiti, usiamo endpoint games per oggi
        url = f"https://api.tennis.api-sports.io/games?date={today}"
        resp = requests.get(url, headers=headers)
        
        if resp.status_code == 200:
            games = resp.json().get('response', [])
            for g in games:
                cat = g.get('tournament', {}).get('category', {}).get('name', '')
                if 'ATP' not in cat and 'WTA' not in cat: continue
                
                p1, p2 = g.get('players', [])[0], g.get('players', [])[1]
                if not p1.get('rank') or not p2.get('rank'): continue
                
                matches_info[p1.get('name')] = {'rank': p1.get('rank'), 'opp_rank': p2.get('rank')}
                matches_info[p2.get('name')] = {'rank': p2.get('rank'), 'opp_rank': p1.get('rank')}
    except: pass

    # 2. SCARICA QUOTE (ODDS-API)
    try:
        resp = requests.get('https://api.the-odds-api.com/v4/sports', params={'apiKey': config.ODDS_API_KEY})
        leagues = [s for s in resp.json() if 'tennis' in s['key'].lower() and 'winner' not in s['key']]
        
        for league in leagues:
            resp = requests.get(f'https://api.the-odds-api.com/v4/sports/{league["key"]}/odds', 
                              params={'apiKey': config.ODDS_API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'})
            if resp.status_code != 200: continue
            
            for ev in resp.json():
                home, away = ev['home_team'], ev['away_team']
                match_label = f"{home} vs {away}"
                
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
                    
                    # FILTRI
                    if not (config.STRATEGY_TENNIS['QUOTA_MIN'] <= q_bf <= config.STRATEGY_TENNIS['QUOTA_MAX']): continue
                    
                    # Ranking Gap Check (Fuzzy match nome)
                    ranking_advantage = 0
                    stats_found = False
                    for api_name, data in matches_info.items():
                        if player.split()[-1] in api_name: 
                            ranking_advantage = data['opp_rank'] - data['rank']
                            stats_found = True
                            break
                    
                    if stats_found:
                        if ranking_advantage < config.STRATEGY_TENNIS['MIN_RANK_DIFF']: continue
                    else:
                        if q_pinna > 1.60: continue # Senza stats, solo super favoriti
                        
                    prob_reale = (1/q_pinna) / margin
                    ev = (prob_reale * q_bf - 1) * 100
                    
                    if ev >= config.STRATEGY_TENNIS['MIN_EDGE']:
                        stake = calculate_kelly(prob_reale, q_bf, bankroll)
                        if stake > 0:
                            msg = f"🎾 TENNIS: {player}\nQuota: {q_bf} | Gap: +{ranking_advantage}\nStake: {stake}€"
                            send_telegram(msg)
                            found_bets.append({
                                "Sport": "TENNIS", "Data": ev['commence_time'], "Match": match_label,
                                "Selezione": player, "Q_Betfair": q_bf, "Q_Reale": q_pinna,
                                "Rating": "💎 GEM" if ranking_advantage > 100 else "✅ SOLID",
                                "Edge%": round(ev, 1), "Stake_Ready": stake, "Abbinata": False
                            })
                            
    except: pass
    return found_bets
