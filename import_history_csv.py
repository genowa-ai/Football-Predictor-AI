import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import hashlib
import os

# --- CONFIG ---
DB_HOST = "localhost"
DB_NAME = "football_db"
DB_USER = "postgres"
DB_PASS = "1004"

# --- LEAGUE MAPPING ---
LEAGUE_MAP = {
    "E0": 39, "E1": 40, "E2": 41, "E3": 42, "EC": 43,
    "SC0": 179, "SC1": 180, "SC2": 181, "SC3": 182,
    "D1": 78, "D2": 79, "I1": 135, "I2": 136,
    "SP1": 140, "SP2": 141, "F1": 61, "F2": 62,
    "N1": 88, "B1": 144, "P1": 94, "T1": 203,
    "G1": 197, "ARG": 128, "AUT": 218, "BRA": 71,
    "CHN": 169, "DNK": 119, "FIN": 244, "IRL": 357,
    "JPN": 98, "MEX": 262, "NOR": 103, "POL": 106,
    "ROU": 283, "RUS": 235, "SWE": 113, "SWZ": 207,
    "USA": 253
}

def get_db_connection():
    try:
        return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

def generate_id(date_str, home, away):
    unique_str = f"{date_str}-{home}-{away}"
    return int(hashlib.sha256(unique_str.encode('utf-8')).hexdigest(), 16) % (10**8)

def import_csv_to_db():
    conn = get_db_connection()
    if not conn:
        print("Could not connect to DB.")
        return
    cursor = conn.cursor()

    print(f"Scanning entire project for league files...")
    root_dir = os.getcwd() 
    total_imported = 0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        if any(x in dirpath for x in ['.venv', '.git', '.idea']): continue
            
        for filename in filenames:
            if not filename.lower().endswith(".csv"): continue

            name_no_ext = os.path.splitext(filename)[0].split(' ')[0] 
            league_code = None
            for key in LEAGUE_MAP:
                if key.lower() == name_no_ext.lower():
                    league_code = key
                    break
            
            if league_code:
                full_path = os.path.join(dirpath, filename)
                league_id = LEAGUE_MAP[league_code]
                
                print(f"Processing {filename} (League {league_id})...")

                try:
                    df = pd.read_csv(full_path, encoding='latin-1')
                    if 'FTHG' not in df.columns: continue

                    matches_to_insert = []
                    teams_to_insert = set()

                    for index, row in df.iterrows():
                        try:
                            # 1. Date
                            try:
                                date_str = pd.to_datetime(row['Date'], dayfirst=True).strftime('%Y-%m-%d')
                            except: continue

                            # 2. Teams
                            home = str(row['HomeTeam']).strip()
                            away = str(row['AwayTeam']).strip()
                            if not home or not away or home == 'nan': continue

                            hg = int(row['FTHG'])
                            ag = int(row['FTAG'])
                            
                            # 3. IDs
                            m_id = generate_id(date_str, home, away)
                            h_id = int(hashlib.sha256(home.encode('utf-8')).hexdigest(), 16) % (10**6)
                            a_id = int(hashlib.sha256(away.encode('utf-8')).hexdigest(), 16) % (10**6)

                            teams_to_insert.add((h_id, home))
                            teams_to_insert.add((a_id, away))
                            
                            # Matches Schema (Original 8 columns)
                            matches_to_insert.append((m_id, league_id, date_str, h_id, a_id, hg, ag, 'FT'))
                        except: continue

                    if teams_to_insert:
                        query_teams = "INSERT INTO teams (team_id, name) VALUES %s ON CONFLICT (team_id) DO NOTHING"
                        execute_values(cursor, query_teams, list(teams_to_insert))
                    
                    if matches_to_insert:
                        query_matches = """
                            INSERT INTO matches 
                            (match_id, league_id, match_date, home_team_id, away_team_id, home_goals, away_goals, status) 
                            VALUES %s 
                            ON CONFLICT (match_id) DO UPDATE SET
                                home_goals = EXCLUDED.home_goals,
                                away_goals = EXCLUDED.away_goals,
                                status = EXCLUDED.status;
                        """
                        execute_values(cursor, query_matches, matches_to_insert)
                    
                    total_imported += len(matches_to_insert)

                except Exception as e:
                    print(f"    Error reading file: {e}")

    conn.commit()
    conn.close()
    print(f"\n✅ SUCCESS! Total matches imported: {total_imported}")

if __name__ == "__main__":
    import_csv_to_db()