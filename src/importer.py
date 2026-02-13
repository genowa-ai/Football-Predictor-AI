import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
import sys
import os
import math

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src import config
except ImportError:
    import config

# --- CONFIGURATION ---
if not config.API_KEY:
    raise ValueError("API_KEY not set. Please define it in your .env file.")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {'x-apisports-key': config.API_KEY}

def get_db_connection():
    try:
        return psycopg2.connect(
            host=config.DB_HOST, database=config.DB_NAME,
            user=config.DB_USER, password=config.DB_PASS
        )
    except Exception as e:
        print(f"❌ Database Connection Error: {e}")
        return None

def create_tables_if_not_exist(cursor):
    """Auto-creates extra tables for Phase 5 data (Odds, Injuries, Standings)."""
    queries = [
        """CREATE TABLE IF NOT EXISTS odds (
            id SERIAL PRIMARY KEY, fixture_id INT, bookmaker_id INT, 
            home_odd FLOAT, draw_odd FLOAT, away_odd FLOAT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS injuries (
            id SERIAL PRIMARY KEY, fixture_id INT, player_name VARCHAR(100), 
            team_id INT, type VARCHAR(50), reason VARCHAR(255)
        );""",
        """CREATE TABLE IF NOT EXISTS standings (
            league_id INT, team_id INT, rank INT, form VARCHAR(10), 
            points INT, goals_diff INT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (league_id, team_id)
        );"""
    ]
    for q in queries:
        cursor.execute(q)

def fetch_api(endpoint, params):
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params)
        if r.status_code == 200: return r.json().get('response', [])
        print(f"⚠️ API Error {r.status_code}: {r.text}")
        return []
    except Exception as e:
        print(f"❌ Network Error: {e}")
        return []

# --- CORE IMPORTERS ---

def import_matches_and_fixtures():
    """Fetches Yesterday (Results) and Today/Tomorrow (Fixtures)."""
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    create_tables_if_not_exist(cursor)

    dates = {
        'yesterday': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        'today': datetime.now().strftime('%Y-%m-%d'),
        'tomorrow': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    }

    # 1. PROCESS YESTERDAY (Results)
    print(f"📥 Processing Results for {dates['yesterday']}...")
    data = fetch_api("fixtures", {"date": dates['yesterday']})
    
    history_matches = []
    teams = {}
    
    for m in data:
        if m['fixture']['status']['short'] in ['FT', 'AET', 'PEN']:
            history_matches.append((
                m['fixture']['id'], m['league']['id'], m['fixture']['date'],
                m['teams']['home']['id'], m['teams']['away']['id'],
                m['goals']['home'], m['goals']['away'], 'FT'
            ))
            teams[m['teams']['home']['id']] = m['teams']['home']['name']
            teams[m['teams']['away']['id']] = m['teams']['away']['name']

    if teams:
        execute_values(cursor, "INSERT INTO teams (team_id, name) VALUES %s ON CONFLICT (team_id) DO NOTHING", list(teams.items()))
    if history_matches:
        q = """INSERT INTO matches (match_id, league_id, match_date, home_team_id, away_team_id, home_goals, away_goals, status)
               VALUES %s ON CONFLICT (match_id) DO UPDATE SET status='FT', home_goals=EXCLUDED.home_goals, away_goals=EXCLUDED.away_goals"""
        execute_values(cursor, q, history_matches)
        print(f"✅ Updated {len(history_matches)} finished matches.")

    # 2. PROCESS TODAY & TOMORROW (Fixtures)
    print(f"🔮 Processing Fixtures for {dates['today']} & {dates['tomorrow']}...")
    fixtures_data = []
    fixture_ids = [] # Collect IDs for Odds/Injuries
    
    for day in [dates['today'], dates['tomorrow']]:
        data = fetch_api("fixtures", {"date": day})
        for m in data:
            if m['fixture']['status']['short'] in ['NS', 'TBD']:
                fixtures_data.append((
                    m['fixture']['date'], m['teams']['home']['name'], m['teams']['away']['name'],
                    m['league']['id'], 'SCHEDULED'
                ))
                fixture_ids.append(m['fixture']['id'])

    cursor.execute("TRUNCATE TABLE fixtures")
    if fixtures_data:
        execute_values(cursor, "INSERT INTO fixtures (match_date, home_team, away_team, league_id, status) VALUES %s", fixtures_data)
        print(f"✅ Scheduled {len(fixtures_data)} upcoming matches.")

    conn.commit()
    conn.close()
    return fixture_ids

def import_odds(fixture_ids):
    """Fetches Odds using Date filtering to save requests."""
    if not fixture_ids: return
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("💰 Fetching Market Odds...")
    # Strategy: Call odds by DATE (tomorrow) instead of ID to save requests
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    data = fetch_api("odds", {"date": tomorrow, "bookmaker": 1}) # 1 = Bet365
    
    odds_data = []
    for item in data:
        if item['fixture']['id'] in fixture_ids:
            try:
                # Find Match Winner odds
                markets = [m for m in item['bookmakers'][0]['bets'] if m['id'] == 1]
                if markets:
                    vals = {v['value']: v['odd'] for v in markets[0]['values']}
                    odds_data.append((
                        item['fixture']['id'], 1, 
                        vals.get('Home'), vals.get('Draw'), vals.get('Away')
                    ))
            except: continue

    if odds_data:
        # Clear old odds to keep DB light
        cursor.execute("TRUNCATE TABLE odds")
        execute_values(cursor, "INSERT INTO odds (fixture_id, bookmaker_id, home_odd, draw_odd, away_odd) VALUES %s", odds_data)
        print(f"✅ Updated Odds for {len(odds_data)} matches.")
    
    conn.commit()
    conn.close()

def import_injuries(fixture_ids):
    """Batched Injury Fetching (Max 20 IDs per call)."""
    if not fixture_ids: return
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"🚑 Checking Injuries for {len(fixture_ids)} matches (Batched)...")
    
    # Chunk IDs into groups of 20
    chunk_size = 20
    injury_records = []
    
    for i in range(0, len(fixture_ids), chunk_size):
        chunk = fixture_ids[i:i + chunk_size]
        ids_str = "-".join(map(str, chunk))
        
        data = fetch_api("injuries", {"ids": ids_str})
        for item in data:
            injury_records.append((
                item['fixture']['id'], item['player']['name'], 
                item['team']['id'], item['player']['type'], item['player']['reason']
            ))
            
    if injury_records:
        cursor.execute("TRUNCATE TABLE injuries")
        execute_values(cursor, "INSERT INTO injuries (fixture_id, player_name, team_id, type, reason) VALUES %s", injury_records)
        print(f"✅ Found {len(injury_records)} injury reports.")
    
    conn.commit()
    conn.close()

def run_importer():
    print("🚀 Starting Daily Data Import (Phase 5)...")
    
    # 1. Matches & Fixtures (Cost: ~3 Requests)
    fixture_ids = import_matches_and_fixtures()
    
    # 2. Odds (Cost: ~2-4 Requests)
    if fixture_ids:
        import_odds(fixture_ids)
        
    # 3. Injuries (Cost: ~3-5 Requests depending on volume)
    if fixture_ids:
        import_injuries(fixture_ids)
        
    print("🏁 Data Import Complete.")

if __name__ == "__main__":
    run_importer()