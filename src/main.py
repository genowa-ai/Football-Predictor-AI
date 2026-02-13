from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor
from src import config
from src.predict_utils import stats_cache # Import our new helper

app = FastAPI()

# --- Load Artifacts ---
model = joblib.load(config.MODEL_PATH)
shap_explainer = joblib.load(config.SHAP_EXPLAINER_PATH)

# --- Database Connection ---
def get_db_connection():
    return psycopg2.connect(
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        host=config.DB_HOST,
        port=config.DB_PORT
    )

# --- Request Models ---
class MatchRequest(BaseModel):
    home_team: str
    away_team: str

# --- Endpoints ---

@app.get("/")
def home():
    return {"message": "No-Draw Sniper API is Live 🎯"}

@app.post("/predict")
def predict_match(match: MatchRequest):
    """Manual Single Match Prediction"""
    features = stats_cache.get_features_for_fixture(match.home_team, match.away_team)
    
    # Create DataFrame
    X = pd.DataFrame([features])
    
    # Predict
    probs = model.predict_proba(X)[0] # [Away, Draw, Home]
    
    return {
        "home_team": match.home_team,
        "away_team": match.away_team,
        "probabilities": {
            "home": float(probs[2]),
            "draw": float(probs[1]),
            "away": float(probs[0])
        },
        "features": features
    }

@app.get("/fixtures/today")
def get_today_fixtures():
    """
    Fetches today's matches from DB, filters played games, and predicts outcomes.
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    today = date.today()
    # Query: Matches for today
    query = """
        SELECT match_date, home_team, away_team, status 
        FROM matches 
        WHERE DATE(match_date) = %s 
        ORDER BY match_date ASC
    """
    cursor.execute(query, (today,))
    fixtures = cursor.fetchall()
    conn.close()

    results = []
    current_time = datetime.now()

    for f in fixtures:
        match_time = f['match_date'] # This is a datetime object
        
        # FILTER: Skip matches that have already started
        if match_time < current_time and f['status'] not in ['NS', 'TBD']:
            continue 

        # Generate Features
        features = stats_cache.get_features_for_fixture(f['home_team'], f['away_team'])
        X = pd.DataFrame([features])
        
        # Predict
        probs = model.predict_proba(X)[0]
        
        results.append({
            "time": match_time.strftime("%H:%M"),
            "home_team": f['home_team'],
            "away_team": f['away_team'],
            "prob_home": round(float(probs[2]), 2),
            "prob_draw": round(float(probs[1]), 2),
            "prob_away": round(float(probs[0]), 2),
            "elo_diff": int(features['elo_diff'])
        })

    return {"date": str(today), "matches": results}