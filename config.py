# --- CONFIGURAZIONE SNIPER V3 FINAL ---

# 1. API KEYS
SPORTMONKS_TOKEN = "EUVQIE2eHy4T2wsYSr3D1RuPQCFuMZLa6n0ey3Q3AtBO8GxOJFzBX1w9hlF8"
ODDS_API_KEY = "78f03ed8354c09f7ac591fe7e105deda"
# API-TENNIS KEY (Nuova)
TENNIS_API_KEY = "56840e9cce33d506b0dddc0cec2cb5e17c83dc825ccb853d176d218d78f2befa"

# 2. MONEY MANAGEMENT
BANKROLL_INIZIALE = 5000.0
KELLY_FRACTION = 0.25      
STAKE_MAX = 100.0          
STAKE_MIN = 10.0           
COMMISSIONE_BETFAIR = 0.05 

# 3. STRATEGIA CALCIO (STATS + VALUE)
STRATEGY_CALCIO = {
    "QUOTA_MIN": 1.60,       
    "QUOTA_MAX": 2.80,       
    "MIN_EDGE": 1.0,         
    "CHECK_PINNACLE": True   
}

# 4. STRATEGIA TENNIS (RANKING GAP + VALUE)
STRATEGY_TENNIS = {
    "QUOTA_MIN": 1.35,       
    "QUOTA_MAX": 2.20,       
    "MIN_RANK_DIFF": 50,     # Il favorito deve avere 50 posti di vantaggio
    "MIN_EDGE": 2.0,         # Vantaggio > 2%
    "SURFACE_FILTER": False  
}

# 5. FILE DI SISTEMA
FILE_STORICO = "registro_operazioni.csv"
FILE_PENDING = "radar_pending.csv"

# 6. TELEGRAM
TELEGRAM_TOKEN = "8145327630:AAHJC6vDjvGUyPT0pKw63fyW53hTl_F873U"
TELEGRAM_CHAT_ID = "5562163433"

# 7. CAMPIONATI TARGET
LEAGUES_CALCIO = [
    "Serie A", "Serie B", "Premier League", "Championship",
    "Bundesliga", "2. Bundesliga", "La Liga", "Segunda División",
    "Ligue 1", "Ligue 2", "Champions League", "Europa League"
]
