import pandas as pd
import numpy as np
import joblib
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src import config
    from src.stats_engine import StatsEngine
except ImportError:
    import config
    from stats_engine import StatsEngine

def get_db_engine():
    url = f"postgresql://{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    return create_engine(url)

def get_latest_hockey_stats(df_history):
    print("🕵️  Building Hockey Stats Knowledge Base...")
    stats_db = {}
    df_history['date'] = pd.to_datetime(df_history['date'], format='mixed', errors='coerce')
    df_history = df_history.dropna(subset=['date']).sort_values('date')
    
    for _, row in df_history.iterrows():
        # Update Elo based on REGULATION performance (Now using correct reg_goals columns)
        # Using 30 as K-factor
        delta = StatsEngine.calculate_elo_change(
            elo_home=row['home_elo'], elo_away=row['away_elo'],
            home_goals=row['reg_goals_home'], away_goals=row['reg_goals_away']
        )
        
        # Get Rolling Stats (Safely)
        h_goals = row.get('home_rolling_goals', 0)
        h_conceded = row.get('home_rolling_conceded', 0)
        a_goals = row.get('away_rolling_goals', 0)
        a_conceded = row.get('away_rolling_conceded', 0)

        stats_db[row['home_team_name']] = {
            'elo': row['home_elo'] + delta,
            'last_date': row['date'],
            'rolling_goals': h_goals,
            'rolling_conceded': h_conceded,
            'btts_rate': row.get('home_btts_rate', 0)
        }
        stats_db[row['away_team_name']] = {
            'elo': row['away_elo'] - delta,
            'last_date': row['date'],
            'rolling_goals': a_goals,
            'rolling_conceded': a_conceded,
            'btts_rate': row.get('away_btts_rate', 0)
        }
    return stats_db

def load_hockey_fixtures():
    engine = get_db_engine()
    query = f"""
        SELECT f.fixture_id, f.date, f.home_team_name, f.away_team_name, f.league_id,
               o.home_odd, o.draw_odd, o.away_odd
        FROM {config.HOCKEY_TABLE} f
        LEFT JOIN odds o ON f.fixture_id = o.fixture_id
        WHERE f.date >= CURRENT_DATE 
        AND f.status_short = 'NS' 
        ORDER BY f.date ASC
    """
    try:
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print(f"⚠️ Could not load fixtures: {e}")
        return pd.DataFrame()

def smart_daily_predict_hockey():
    print("🔮 Starting Hockey Prediction (Sniper Mode)...")
    
    if not config.HOCKEY_MODEL_PATH.exists():
        print("❌ Model not found. Train first.")
        return

    try:
        model = joblib.load(config.HOCKEY_MODEL_PATH)
        df_history = pd.read_csv(config.HOCKEY_PROCESSED_PATH)
        stats_db = get_latest_hockey_stats(df_history)
        
        df_fixtures = load_hockey_fixtures()
        if df_fixtures.empty:
            print("⚠️ No upcoming matches found.")
            return

        # Build Features
        feature_rows = []
        valid_indices = []

        for index, row in df_fixtures.iterrows():
            home = row['home_team_name']
            away = row['away_team_name']
            
            if home not in stats_db or away not in stats_db: 
                continue
                
            h_stats = stats_db[home]
            a_stats = stats_db[away]
            
            try: date = pd.to_datetime(row['date'])
            except: continue

            h_rest = max(0, min((date - h_stats['last_date']).days, 7))
            a_rest = max(0, min((date - a_stats['last_date']).days, 7))

            features = {
                'league_id': row['league_id'],
                'home_elo': h_stats['elo'],
                'away_elo': a_stats['elo'],
                'elo_diff': h_stats['elo'] - a_stats['elo'],
                'home_rolling_goals': h_stats['rolling_goals'],
                'away_rolling_goals': a_stats['rolling_goals'],
                'home_rolling_conceded': h_stats['rolling_conceded'],
                'away_rolling_conceded': a_stats['rolling_conceded'],
                'form_diff': 0, # Placeholder
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

        if not feature_rows:
            print("❌ No valid team stats found for upcoming games.")
            return

        X_pred = pd.DataFrame(feature_rows, columns=config.MODEL_FEATURES)
        df_valid = df_fixtures.loc[valid_indices]
        
        # Predict
        probs = model.predict_proba(X_pred)
        
        predictions = []
        
        for i, (index, row) in enumerate(df_valid.iterrows()):
            # Unpack Probabilities: [Away, Draw, Home]
            p_away, p_draw, p_home = probs[i]
            
            # --- IMPROVED TIP LOGIC (1X2) ---
            # Determine the highest probability outcome
            if p_home > p_away and p_home > p_draw:
                tip = "HOME"
                conf = p_home
                odd_col = 'home_odd'
            elif p_away > p_home and p_away > p_draw:
                tip = "AWAY"
                conf = p_away
                odd_col = 'away_odd'
            else:
                tip = "DRAW"
                conf = p_draw
                odd_col = 'draw_odd'
            
            # Value Calculation
            value_msg = ""
            if pd.notnull(row[odd_col]):
                try:
                    implied_prob = StatsEngine.calculate_implied_prob(row[odd_col])
                    edge = conf - implied_prob
                    if edge > 0.05: value_msg = f"💎 +{round(edge*100,1)}%"
                except:
                    pass

            predictions.append({
                'Match': f"{row['home_team_name']} vs {row['away_team_name']}",
                'Tip': tip,
                'Conf': round(conf * 100, 1),
                'H_Win%': round(p_home * 100, 0),
                'D_Win%': round(p_draw * 100, 0),
                'A_Win%': round(p_away * 100, 0),
                'Odds': row[odd_col],
                'Value': value_msg,
                'Status': "✅ PREDICTED"
            })

        # Output
        if not predictions:
            print("⚠️ Predictions list is empty.")
            return

        df_pred = pd.DataFrame(predictions).sort_values('Conf', ascending=False)
        cols = [
            'Match', 'Tip', 'Conf', 
            'H_Win%', 'D_Win%', 'A_Win%', 
            'Odds', 'Value', 'Status'
        ]
        
        print("\n🎯 TOP HOCKEY PREDICTIONS (Regulation Time):")
        print(df_pred[cols].to_string(index=False))
        
        save_path = config.BASE_DIR / f"hockey_predictions_{datetime.now().strftime('%Y-%m-%d')}.csv"
        df_pred.to_csv(save_path, index=False)
        print(f"\n💾 Saved to {save_path}")

    except Exception as e:
        print(f"❌ Prediction Failed: {e}")

if __name__ == "__main__":
    smart_daily_predict_hockey()