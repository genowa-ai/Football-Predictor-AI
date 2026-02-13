import pandas as pd
import numpy as np
import os
import sys
from sqlalchemy import create_engine

# Import Config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src import config
except ImportError:
    import config

def get_db_engine():
    db_url = f"postgresql://{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    return create_engine(db_url)

def calculate_elo_series(df):
    """
    Iterates through the dataframe to calculate Elo ratings for every game.
    """
    elo_dict = {} # Stores current Elo for each team
    
    home_elos = []
    away_elos = []
    
    # Default Elo
    START_ELO = 1500
    K_FACTOR = 30 # Standard for Hockey
    
    print("⚡ Calculating Elo History for Hockey...")
    
    for index, row in df.iterrows():
        home = row['home_team_name']
        away = row['away_team_name']
        
        # Get current Elo (or default)
        h_elo = elo_dict.get(home, START_ELO)
        a_elo = elo_dict.get(away, START_ELO)
        
        # Store PRE-MATCH Elo (Features)
        home_elos.append(h_elo)
        away_elos.append(a_elo)
        
        # Calculate Outcome (Regulation Goals)
        h_goals = row['reg_goals_home']
        a_goals = row['reg_goals_away']
        
        if h_goals > a_goals:
            result = 1.0
        elif h_goals == a_goals:
            result = 0.5
        else:
            result = 0.0
            
        # Expected Result
        expected = 1 / (1 + 10 ** ((a_elo - h_elo) / 400))
        
        # Update Elo
        # Margin of Victory Multiplier (Optional, keeping simple K for now)
        change = K_FACTOR * (result - expected)
        
        elo_dict[home] = h_elo + change
        elo_dict[away] = a_elo - change
        
    return home_elos, away_elos

def calculate_hockey_features(df):
    print("🧹 Cleaning & Calculating Features...")
    
    df['date'] = pd.to_datetime(df['date'])
    
    # 1. Regulation Goals (Critical for Target)
    df['reg_goals_home'] = df['score_p1_home'] + df['score_p2_home'] + df['score_p3_home']
    df['reg_goals_away'] = df['score_p1_away'] + df['score_p2_away'] + df['score_p3_away']
    
    # 2. Target (0=Away, 1=Draw, 2=Home)
    conditions = [
        (df['reg_goals_home'] < df['reg_goals_away']),
        (df['reg_goals_home'] == df['reg_goals_away']),
        (df['reg_goals_home'] > df['reg_goals_away'])
    ]
    df['target'] = np.select(conditions, [0, 1, 2])

    # 3. Elo Calculations
    df['home_elo'], df['away_elo'] = calculate_elo_series(df)
    df['elo_diff'] = df['home_elo'] - df['away_elo']

    # --- ROLLING STATS ENGINE ---
    # Convert to Long Format (One row per team per game) to calculate history
    home_df = df[['date', 'home_team_name', 'reg_goals_home', 'reg_goals_away']].rename(
        columns={'home_team_name': 'team', 'reg_goals_home': 'gf', 'reg_goals_away': 'ga'}
    )
    away_df = df[['date', 'away_team_name', 'reg_goals_away', 'reg_goals_home']].rename(
        columns={'away_team_name': 'team', 'reg_goals_away': 'gf', 'reg_goals_home': 'ga'}
    )
    
    team_stats = pd.concat([home_df, away_df]).sort_values(['team', 'date'])
    
    # A. BTTS (Both Teams To Score)
    team_stats['btts'] = ((team_stats['gf'] > 0) & (team_stats['ga'] > 0)).astype(int)
    
    # B. Fatigue (Rest Days)
    team_stats['last_date'] = team_stats.groupby('team')['date'].shift(1)
    # Fix for the "0 incompatible with datetime" warning:
    team_stats['rest_days'] = (team_stats['date'] - team_stats['last_date']).dt.days.fillna(7) # Default 7 days rest for first game
    
    # C. Rolling Averages (Last 5 Games)
    window = 5
    grouped = team_stats.groupby('team')
    
    team_stats['avg_gf'] = grouped['gf'].transform(lambda x: x.shift(1).rolling(window).mean())
    team_stats['avg_ga'] = grouped['ga'].transform(lambda x: x.shift(1).rolling(window).mean())
    team_stats['avg_btts'] = grouped['btts'].transform(lambda x: x.shift(1).rolling(window).mean())
    
    # Fill NAs for first 5 games
    team_stats.fillna(0, inplace=True)
    
    # Merge Features back to Main DataFrame
    cols = ['date', 'team', 'avg_gf', 'avg_ga', 'avg_btts', 'rest_days']
    
    # Merge Home Stats
    df = df.merge(team_stats[cols], left_on=['date', 'home_team_name'], right_on=['date', 'team'], how='left')
    df.rename(columns={
        'avg_gf': 'home_rolling_goals', 
        'avg_ga': 'home_rolling_conceded', 
        'avg_btts': 'home_btts_rate',
        'rest_days': 'home_rest_days'
    }, inplace=True)
    df.drop(columns=['team'], inplace=True)
    
    # Merge Away Stats
    df = df.merge(team_stats[cols], left_on=['date', 'away_team_name'], right_on=['date', 'team'], how='left')
    df.rename(columns={
        'avg_gf': 'away_rolling_goals', 
        'avg_ga': 'away_rolling_conceded', 
        'avg_btts': 'away_btts_rate',
        'rest_days': 'away_rest_days'
    }, inplace=True)
    df.drop(columns=['team'], inplace=True)

    # 4. Final Interaction Features
    df['form_diff'] = df['home_rolling_goals'] - df['away_rolling_goals'] # Simple form proxy
    df['defensive_diff'] = df['home_rolling_conceded'] - df['away_rolling_conceded']
    df['btts_interaction'] = df['home_btts_rate'] * df['away_btts_rate']
    df['rest_diff'] = df['home_rest_days'] - df['away_rest_days']
    
    return df

def feature_engineering_hockey():
    print("⏳ Loading HOCKEY Data from DB...")
    engine = get_db_engine()
    # Only Finished games
    query = f"SELECT * FROM {config.HOCKEY_TABLE} WHERE status_short IN ('FT', 'AOT', 'AP') ORDER BY date ASC"
    df = pd.read_sql(query, engine)

    if df.empty:
        print("⚠️ No Hockey data found.")
        return

    df = calculate_hockey_features(df)
    
    print(f"💾 Saving processed data ({len(df)} rows) to {config.HOCKEY_PROCESSED_PATH}...")
    df.to_csv(config.HOCKEY_PROCESSED_PATH, index=False)
    print("✅ Hockey Preprocessing Complete.")

if __name__ == "__main__":
    feature_engineering_hockey()