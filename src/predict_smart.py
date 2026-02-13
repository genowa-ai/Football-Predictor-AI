import pandas as pd
import numpy as np
import joblib
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text

# Import Config & Stats Engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src import config
    from src.stats_engine import StatsEngine
except ImportError:
    import config
    from stats_engine import StatsEngine

# --- CONSTANTS ---
DRAW_THRESHOLD = 0.25       
CONFIDENCE_THRESHOLD = 0.60 
ELO_DIFF_MIN = 25           

def get_db_engine():
    url = f"postgresql://{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    return create_engine(url)

def get_latest_team_stats(df_history):
    print("🕵️  Building Team Stats Knowledge Base...")
    stats_db = {}
    df_history['match_date'] = pd.to_datetime(df_history['match_date'], format='mixed', errors='coerce')
    df_history = df_history.dropna(subset=['match_date']).sort_values('match_date')
    
    for _, row in df_history.iterrows():
        delta = StatsEngine.calculate_elo_change(
            elo_home=row['home_elo'], elo_away=row['away_elo'],
            home_goals=row['home_goals'], away_goals=row['away_goals']
        )
        stats_db[row['home_team']] = {
            'elo': row['home_elo'] + delta, 
            'last_date': row['match_date'],
            'rolling_goals': row['home_rolling_goals'],
            'rolling_conceded': row['home_rolling_conceded'],
            'btts_rate': row['home_btts_rate'],
            'form': row['home_form']
        }
        stats_db[row['away_team']] = {
            'elo': row['away_elo'] - delta,
            'last_date': row['match_date'],
            'rolling_goals': row['away_rolling_goals'],
            'rolling_conceded': row['away_rolling_conceded'],
            'btts_rate': row['away_btts_rate'],
            'form': row['away_form']
        }
    return stats_db

def load_upcoming_fixtures():
    engine = get_db_engine()
    query = """
        SELECT f.id as fixture_id, f.match_date, f.home_team, f.away_team, f.league_id,
               o.home_odd, o.draw_odd, o.away_odd
        FROM fixtures f
        LEFT JOIN odds o ON f.id = o.fixture_id
        WHERE f.match_date >= CURRENT_DATE 
        ORDER BY f.match_date ASC
    """
    try:
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print(f"⚠️ Could not load fixtures: {e}")
        return pd.DataFrame()

def check_injuries(fixture_id, engine):
    query = text("SELECT count(*) FROM injuries WHERE fixture_id = :fid")
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"fid": fixture_id}).fetchone()
        return result[0] if result else 0
    except:
        return 0

def prepare_features(df_fixtures, stats_db):
    feature_rows = []
    valid_indices = []

    for index, row in df_fixtures.iterrows():
        home = row['home_team']
        away = row['away_team']
        try: date = pd.to_datetime(row['match_date'])
        except: continue
        
        if home not in stats_db or away not in stats_db: continue 
            
        h_stats = stats_db[home]
        a_stats = stats_db[away]
        
        h_rest = max(0, min((date - h_stats['last_date']).days, 30))
        a_rest = max(0, min((date - a_stats['last_date']).days, 30))
        
        features = {
            'league_id': row['league_id'],
            'home_elo': h_stats['elo'],
            'away_elo': a_stats['elo'],
            'elo_diff': h_stats['elo'] - a_stats['elo'],
            'home_rolling_goals': h_stats['rolling_goals'],
            'away_rolling_goals': a_stats['rolling_goals'],
            'home_rolling_conceded': h_stats['rolling_conceded'],
            'away_rolling_conceded': a_stats['rolling_conceded'],
            'form_diff': h_stats['form'] - a_stats['form'],
            'defensive_diff': h_stats['rolling_conceded'] - a_stats['rolling_conceded'],
            'home_btts_rate': h_stats['btts_rate'],
            'away_btts_rate': a_stats['btts_rate'],
            'btts_interaction': h_stats['btts_rate'] * a_stats['btts_rate'],
            'home_rest_days': h_rest,
            'away_rest_days': a_rest,
            'rest_diff': h_rest - a_rest
        }
        row_data = [features.get(col, 0) for col in config.MODEL_FEATURES]
        feature_rows.append(row_data)
        valid_indices.append(index)

    if not feature_rows: return pd.DataFrame(), pd.DataFrame()
    return pd.DataFrame(feature_rows, columns=config.MODEL_FEATURES), df_fixtures.loc[valid_indices]

def smart_daily_predict():
    print("🔮 Starting Professional Daily Prediction (Sniper Mode)...")
    model = joblib.load(config.MODEL_PATH)
    df_history = pd.read_csv(config.PROCESSED_DATA_PATH)
    stats_db = get_latest_team_stats(df_history)
    
    df_fixtures = load_upcoming_fixtures()
    if df_fixtures.empty:
        print("⚠️ No upcoming fixtures found.")
        return

    X_pred, df_valid = prepare_features(df_fixtures, stats_db)
    if X_pred.empty: return

    probs = model.predict_proba(X_pred)
    engine = get_db_engine()
    predictions = []
    
    for i, (index, row) in enumerate(df_valid.iterrows()):
        p_away, p_draw, p_home = probs[i]
        
        # --- FILTERS ---
        if p_draw > DRAW_THRESHOLD: continue
        if p_draw > p_home and p_draw > p_away: continue
        if p_home < CONFIDENCE_THRESHOLD and p_away < CONFIDENCE_THRESHOLD: continue
        
        # --- SNIPER LOGIC ---
        market_draw_prob = 0.0
        value_msg = ""
        if pd.notnull(row['draw_odd']):
            market_draw_prob = StatsEngine.calculate_implied_prob(row['draw_odd'])
            if market_draw_prob > config.SNIPER_THRESHOLDS['MAX_DRAW_ODDS_IMPLIED']: continue
            
            my_prob = p_home if p_home > p_away else p_away
            implied_win = StatsEngine.calculate_implied_prob(row['home_odd'] if p_home > p_away else row['away_odd'])
            edge = my_prob - implied_win
            if edge > 0.05: value_msg = f"💎 +{round(edge*100,1)}%"

        # --- EXTRACT STATS ---
        h_avg_goals = X_pred.iloc[i]['home_rolling_goals']
        a_avg_goals = X_pred.iloc[i]['away_rolling_goals']
        h_conceded = X_pred.iloc[i]['home_rolling_conceded']
        a_conceded = X_pred.iloc[i]['away_rolling_conceded']
        
        injuries = check_injuries(row['fixture_id'], engine)
        injury_msg = f"🚑 {injuries}" if injuries > 0 else ""
        
        # Poisson Check
        pois_draw = StatsEngine.calculate_poisson_draw_chance((h_avg_goals + a_conceded)/2, (a_avg_goals + h_conceded)/2)
        status = "✅ BET"
        if pois_draw > 0.25: status = "⚠️ RISK (Poisson)"

        predictions.append({
            'Match': f"{row['home_team']} vs {row['away_team']}",
            'Tip': "HOME" if p_home > p_away else "AWAY",
            'Conf': round(max(p_home, p_away) * 100, 1),
            # NEW COLUMNS START HERE
            'H_Win%': round(p_home * 100, 0),
            'D_Win%': round(p_draw * 100, 0),
            'A_Win%': round(p_away * 100, 0),
            'H_GF': round(h_avg_goals, 2), # Home Goals For
            'A_GF': round(a_avg_goals, 2), # Away Goals For
            'H_GA': round(h_conceded, 2),  # Home Goals Against
            'A_GA': round(a_conceded, 2),  # Away Goals Against
            # END NEW COLUMNS
            'Odds': row['home_odd'] if p_home > p_away else row['away_odd'],
            'Value': value_msg,
            'Injuries': injury_msg,
            'Status': status
        })

    if not predictions:
        print("No matches passed the filters today.")
    else:
        df_pred = pd.DataFrame(predictions).sort_values('Conf', ascending=False)
        
        # Define readable column order
        cols = [
            'Match', 'Tip', 'Conf', 
            'H_Win%', 'D_Win%', 'A_Win%', 
            'H_GF', 'A_GF', 'H_GA', 'A_GA', 
            'Odds', 'Value', 'Injuries', 'Status'
        ]
        
        print("\n🎯 TOP SNIPER TARGETS:")
        # to_string renders nicely in terminal without index
        print(df_pred[cols].to_string(index=False))
        
        filename = f"predictions_{datetime.now().strftime('%Y-%m-%d')}.csv"
        df_pred.to_csv(config.BASE_DIR / filename, index=False)
        print(f"\n💾 Saved to {filename}")

if __name__ == "__main__":
    smart_daily_predict()