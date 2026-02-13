import pandas as pd
import numpy as np
import os
import sys
from sqlalchemy import create_engine

# Ensure we can import src modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src import config
    from src.stats_engine import StatsEngine 
except ImportError:
    import config
    # Fallback to keep script running even if stats_engine has path issues
    try:
        from stats_engine import StatsEngine
    except ImportError:
        print("❌ Critical Error: StatsEngine not found. Check paths.")
        sys.exit(1)

def get_db_engine():
    db_url = f"postgresql://{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    return create_engine(db_url)

def load_data_from_db():
    print("⏳ Loading Data from PostgreSQL...")
    engine = get_db_engine()
    
    # Load Matches
    query_matches = "SELECT * FROM matches ORDER BY match_date ASC"
    df_matches = pd.read_sql(query_matches, engine)
    
    # Load Teams for mapping
    query_teams = "SELECT team_id, name FROM teams"
    df_teams = pd.read_sql(query_teams, engine)
    
    print(f"✅ Loaded {len(df_matches)} matches and {len(df_teams)} teams.")
    return df_matches, df_teams

def clean_and_map_data(df_matches, df_teams):
    print("🧹 Cleaning & Mapping Data...")
    
    # 1. Map IDs to Names
    id_to_name = dict(zip(df_teams['team_id'], df_teams['name']))
    df_matches['home_team'] = df_matches['home_team_id'].map(id_to_name)
    df_matches['away_team'] = df_matches['away_team_id'].map(id_to_name)
    
    # 2. Drop unknown teams
    df_matches = df_matches.dropna(subset=['home_team', 'away_team'])
    
    # 3. Ensure Date Format
    df_matches['match_date'] = pd.to_datetime(df_matches['match_date'])
    
    # 4. Handle League IDs (Fill NA with 0)
    if 'league_id' in df_matches.columns:
        df_matches['league_id'] = pd.to_numeric(df_matches['league_id'], errors='coerce').fillna(0).astype(int)
    else:
        df_matches['league_id'] = 0
        
    return df_matches

def calculate_rolling_stats(df, window=5):
    print(f"📊 Calculating Rolling Stats (Window={window})...")
    df = df.sort_values('match_date')
    
    # Expand to Team-Match level
    home = df[['match_date', 'home_team', 'home_goals', 'away_goals']].rename(
        columns={'home_team': 'team', 'home_goals': 'gf', 'away_goals': 'ga'}
    )
    away = df[['match_date', 'away_team', 'away_goals', 'home_goals']].rename(
        columns={'away_team': 'team', 'away_goals': 'gf', 'home_goals': 'ga'}
    )
    
    team_stats = pd.concat([home, away]).sort_values(['team', 'match_date'])
    
    # Calc Points & BTTS
    team_stats['pts'] = np.where(team_stats['gf'] > team_stats['ga'], 3, np.where(team_stats['gf'] == team_stats['ga'], 1, 0))
    team_stats['btts'] = np.where((team_stats['gf'] > 0) & (team_stats['ga'] > 0), 1, 0)
    
    # Calc Rest Days
    team_stats['last_date'] = team_stats.groupby('team')['match_date'].shift(1)
    team_stats['rest'] = (team_stats['match_date'] - team_stats['last_date']).dt.days.fillna(7).clip(upper=30)
    
    # Rolling Calculations
    grouped = team_stats.groupby('team')
    team_stats['roll_gf'] = grouped['gf'].transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
    team_stats['roll_ga'] = grouped['ga'].transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
    team_stats['form'] = grouped['pts'].transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
    team_stats['roll_btts'] = grouped['btts'].transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
    
    team_stats.fillna(0, inplace=True)
    
    # Merge Back to Match level
    cols = ['match_date', 'team', 'roll_gf', 'roll_ga', 'form', 'roll_btts', 'rest']
    
    df = df.merge(team_stats[cols], left_on=['match_date', 'home_team'], right_on=['match_date', 'team'], how='left')
    df = df.rename(columns={'roll_gf': 'home_rolling_goals', 'roll_ga': 'home_rolling_conceded', 'form': 'home_form', 'roll_btts': 'home_btts_rate', 'rest': 'home_rest_days'}).drop(columns=['team'])
    
    df = df.merge(team_stats[cols], left_on=['match_date', 'away_team'], right_on=['match_date', 'team'], how='left')
    df = df.rename(columns={'roll_gf': 'away_rolling_goals', 'roll_ga': 'away_rolling_conceded', 'form': 'away_form', 'roll_btts': 'away_btts_rate', 'rest': 'away_rest_days'}).drop(columns=['team'])
    
    return df

def calculate_elo(df):
    print("📈 Calculating True Elo Ratings...")
    # Initialize dictionary to store current ratings
    elo_ratings = {}
    
    df['home_elo'] = 1500.0
    df['away_elo'] = 1500.0
    df = df.sort_values('match_date').reset_index(drop=True)
    
    for idx, row in df.iterrows():
        h_team, a_team = row['home_team'], row['away_team']
        
        h_rating = elo_ratings.get(h_team, 1500.0)
        a_rating = elo_ratings.get(a_team, 1500.0)
        
        # Store PRE-MATCH rating for the model feature
        df.at[idx, 'home_elo'] = h_rating
        df.at[idx, 'away_elo'] = a_rating
        
        delta = StatsEngine.calculate_elo_change(
            elo_home=h_rating, elo_away=a_rating,
            home_goals=row['home_goals'], away_goals=row['away_goals']
        )
        
        elo_ratings[h_team] = h_rating + delta
        elo_ratings[a_team] = a_rating - delta
        
    df['elo_diff'] = df['home_elo'] - df['away_elo']
    return df

def feature_engineering_main():
    df_matches, df_teams = load_data_from_db()
    
    df = clean_and_map_data(df_matches, df_teams)
    df = calculate_rolling_stats(df)
    df = calculate_elo(df)
    
    # Interaction Features
    print("🧮 Generating Interaction Features...")
    df['form_diff'] = df['home_form'] - df['away_form']
    df['defensive_diff'] = df['home_rolling_conceded'] - df['away_rolling_conceded']
    df['rest_diff'] = df['home_rest_days'] - df['away_rest_days']
    df['btts_interaction'] = df['home_btts_rate'] * df['away_btts_rate']
    
    # Target (0=Away, 1=Draw, 2=Home)
    conditions = [
        (df['home_goals'] < df['away_goals']),
        (df['home_goals'] == df['away_goals']),
        (df['home_goals'] > df['away_goals'])
    ]
    df['target'] = np.select(conditions, [0, 1, 2])
    
    print(f"💾 Saving processed data to {config.PROCESSED_DATA_PATH}...")
    df.to_csv(config.PROCESSED_DATA_PATH, index=False)
    print("✅ Preprocessing Complete.")

if __name__ == "__main__":
    feature_engineering_main()