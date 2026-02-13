import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src import config
except ImportError:
    import config

class HockeyImporter:
    def __init__(self):
        self.base_url = config.HOCKEY_API_URL
        self.headers = {'x-apisports-key': config.API_KEY}
        self.leagues = config.HOCKEY_LEAGUES
        self.table = config.HOCKEY_TABLE

    def get_db_connection(self):
        try:
            return psycopg2.connect(
                host=config.DB_HOST, database=config.DB_NAME,
                user=config.DB_USER, password=config.DB_PASS
            )
        except Exception as e:
            print(f"❌ Database Connection Error: {e}")
            return None
    
    def _smart_request(self, url, params):
        retries = 3
        while retries > 0:
            try:
                response = requests.get(url, headers=self.headers, params=params)
                
                # --- NEW: Quota Tracking ---
                remaining = response.headers.get('x-ratelimit-remaining')
                limit = response.headers.get('x-ratelimit-limit')
                if remaining and limit:
                    print(f"   [API Quota: {remaining}/{limit} left]")
                # ---------------------------

                if response.status_code == 429:
                    print("⏳ Rate Limit Hit. Cooling down for 65s...")
                    time.sleep(65)
                    retries -= 1
                    continue
                
                data = response.json()
                errors = data.get('errors', {})
                if isinstance(errors, list) and errors: errors = errors[0]
                
                if errors:
                    error_text = str(errors).lower()
                    if 'rate limit' in error_text or 'requests per minute' in error_text:
                        print("⏳ API Limit Reached. Cooling down for 65s...")
                        time.sleep(65)
                        retries -= 1
                        continue
                    else:
                        print(f"❌ API Error: {errors}")
                        return None
                        
                return data
            except Exception as e:
                print(f"❌ Request Exception: {e}")
                return None
        return None
    
    def fetch_fixtures(self, date_str):
        url = f"{self.base_url}/games"
        params = {'date': date_str}
        data = self._smart_request(url, params)
        if not data: return []
        all_games = data.get('response', [])
        return [g for g in all_games if g['league']['id'] in self.leagues]

    def fetch_season_games(self, league_id, season):
        url = f"{self.base_url}/games"
        params = {'league': league_id, 'season': season}
        print(f"🏒 Fetching Season {season} for League {league_id}...")
        data = self._smart_request(url, params)
        if not data: return []
        return data.get('response', [])

    def parse_game(self, game):
        game_id = game.get('id')
        date = game.get('date')
        status = game.get('status', {}).get('short')
        league = game.get('league', {})
        teams = game.get('teams', {})
        scores = game.get('scores', {})
        periods = game.get('periods', {})

        # --- PARSER FIX: Handle "1-0" Strings ---
        def parse_score_str(val):
            """Splits '1-0' into (1, 0)"""
            if not val or not isinstance(val, str) or '-' not in val:
                return 0, 0
            try:
                parts = val.split('-')
                return int(parts[0]), int(parts[1])
            except:
                return 0, 0

        # Parse Period Scores
        p1_h, p1_a = parse_score_str(periods.get('first'))
        p2_h, p2_a = parse_score_str(periods.get('second'))
        p3_h, p3_a = parse_score_str(periods.get('third'))
        ot_h, ot_a = parse_score_str(periods.get('overtime'))
        pen_h, pen_a = parse_score_str(periods.get('penalties'))

        return (
            game_id, league.get('id'), league.get('season'), date,
            teams.get('home', {}).get('id'), teams.get('away', {}).get('id'),
            teams.get('home', {}).get('name'), teams.get('away', {}).get('name'),
            scores.get('home'), scores.get('away'),
            # Correct Integers now!
            p1_h, p1_a,
            p2_h, p2_a,
            p3_h, p3_a,
            ot_h, ot_a,
            pen_h, pen_a,
            status
        )

    def save_to_db(self, games_data):
        if not games_data: return
        conn = self.get_db_connection()
        if not conn: return
        cursor = conn.cursor()
        
        parsed_data = [self.parse_game(g) for g in games_data]
        
        query = f"""
            INSERT INTO {self.table} (
                fixture_id, league_id, season, date, 
                home_team_id, away_team_id, home_team_name, away_team_name,
                goals_home, goals_away, 
                score_p1_home, score_p1_away, score_p2_home, score_p2_away, 
                score_p3_home, score_p3_away, score_ot_home, score_ot_away, 
                score_pen_home, score_pen_away, status_short
            ) VALUES %s
            ON CONFLICT (fixture_id) DO UPDATE SET
                goals_home = EXCLUDED.goals_home,
                goals_away = EXCLUDED.goals_away,
                score_p1_home = EXCLUDED.score_p1_home,
                score_p1_away = EXCLUDED.score_p1_away,
                score_p2_home = EXCLUDED.score_p2_home,
                score_p2_away = EXCLUDED.score_p2_away,
                score_p3_home = EXCLUDED.score_p3_home,
                score_p3_away = EXCLUDED.score_p3_away,
                score_ot_home = EXCLUDED.score_ot_home,
                score_ot_away = EXCLUDED.score_ot_away,
                score_pen_home = EXCLUDED.score_pen_home,
                score_pen_away = EXCLUDED.score_pen_away,
                status_short = EXCLUDED.status_short;
        """
        try:
            execute_values(cursor, query, parsed_data)
            conn.commit()
            print(f"💾 Saved {len(parsed_data)} games to DB.")
        except Exception as e:
            print(f"Database Error: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

def run_importer():
    importer = HockeyImporter()
    print("🏒 Starting Hockey Daily Import...")
    
    dates_to_fetch = [
        ("Results", (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')),
        ("Live/Today", datetime.now().strftime('%Y-%m-%d')),
        ("Upcoming", (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
    ]

    for label, date_str in dates_to_fetch:
        print(f"   Fetching {label} for {date_str}...", end=" ")
        games = importer.fetch_fixtures(date_str)
        
        if games:
            print(f"✅ Found {len(games)} games.")
            importer.save_to_db(games)
        else:
            print("⚠️ No games found (or API Limit Hit).")
    
    print("✅ Hockey Import Complete.")

if __name__ == "__main__":
    run_importer()