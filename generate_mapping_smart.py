import pandas as pd
import os
from src.utils import get_db_engine
from thefuzz import process

# --- COPY YOUR LEAGUE MAP HERE ---
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

def get_db_teams_by_league(league_id, engine):
    """
    Finds all team names in the DB that have played in a specific league.
    """
    query = f"""
        SELECT DISTINCT t.name 
        FROM teams t
        JOIN matches m ON t.team_id = m.home_team_id OR t.team_id = m.away_team_id
        WHERE m.league_id = {league_id}
    """
    try:
        df = pd.read_sql(query, engine)
        return df['name'].tolist()
    except Exception as e:
        return []

def generate_smart_map():
    engine = get_db_engine()
    root_dir = os.getcwd()
    mapping_data = []

    print(f"📂 Scanning {root_dir} and matching by League...")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip hidden
        if any(x in dirpath for x in ['.venv', '.git', '.idea']): continue

        for filename in filenames:
            if not filename.lower().endswith(".csv") or "mapping" in filename:
                continue

            # 1. Identify League
            # Filename might be 'E0.csv' or 'E0 (1).csv'
            name_key = filename.split(' ')[0].split('.')[0] # Get 'E0'
            
            # Find the league code (case insensitive)
            league_code = next((k for k in LEAGUE_MAP if k.lower() == name_key.lower()), None)
            
            if not league_code:
                continue # Skip files not in our map
            
            league_id = LEAGUE_MAP[league_code]
            print(f"   Processing {filename} -> League {league_id} ({league_code})...")

            # 2. Get CSV Names
            try:
                df_csv = pd.read_csv(os.path.join(dirpath, filename), encoding='latin-1')
                if 'HomeTeam' not in df_csv.columns: continue
                
                csv_names = set(df_csv['HomeTeam'].dropna().unique()) | set(df_csv['AwayTeam'].dropna().unique())
            except:
                continue

            # 3. Get DB Names (ONLY for this League)
            db_names = get_db_teams_by_league(league_id, engine)
            
            if not db_names:
                print(f"      ⚠️ No teams found in DB for League {league_id}. Skipping match.")
                # Fallback: You might want to match against ALL DB teams here if specific league fails
                continue

            # 4. Smart Match
            for csv_name in csv_names:
                # We match the CSV name (e.g. "Man United") to the best DB name in THAT league
                best_match, score = process.extractOne(csv_name, db_names)
                
                if score > 80:
                    mapping_data.append({
                        "api_name": best_match,
                        "csv_name": csv_name,
                        "league": league_code,
                        "confidence": score
                    })

    # Save
    if mapping_data:
        output_df = pd.DataFrame(mapping_data).drop_duplicates(subset=['csv_name'])
        output_df.to_csv("team_mapping.csv", index=False)
        print(f"✅ Generated smart mapping for {len(output_df)} teams.")
    else:
        print("❌ No matches found. Does your DB have data in the 'matches' table?")

if __name__ == "__main__":
    generate_smart_map()