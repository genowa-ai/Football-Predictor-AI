import streamlit as st
import requests
import pandas as pd
import sys
import os
from sqlalchemy import create_engine

# Ensure we can find the config file
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src import config
except ImportError:
    import config

API_URL = "http://127.0.0.1:8000/predict"

st.set_page_config(page_title="Football Match Predictor", page_icon="⚽", layout="wide")
st.title("⚽ Football Match Predictor")

# --- Database Connection ---
@st.cache_resource
def get_db_engine():
    db_url = f"postgresql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    return create_engine(db_url)

# --- Load Teams (STRICTLY FROM PROCESSED DATA) ---
@st.cache_data
def load_teams():
    """
    Loads teams directly from the processed data file.
    This guarantees that every team in the dropdown has stats available.
    """
    teams = []
    if os.path.exists(config.PROCESSED_DATA_PATH):
        try:
            df = pd.read_csv(config.PROCESSED_DATA_PATH)
            # Combine home and away to get full list
            teams = pd.concat([df['home_team'], df['away_team']]).unique()
        except Exception as e:
            st.error(f"Error loading processed data: {e}")
    
    # Fallback to DB if file missing (slower but accurate)
    if len(teams) == 0:
        try:
            engine = get_db_engine()
            teams = pd.read_sql("SELECT DISTINCT name FROM teams ORDER BY name", engine)['name'].tolist()
        except Exception as e:
            st.error(f"Error loading from DB: {e}")

    return sorted(teams)

def get_todays_matches():
    try:
        engine = get_db_engine()
        # Fetch today's matches
        query = """
            SELECT 
                m.match_date, 
                t1.name as home_team, 
                t2.name as away_team
            FROM matches m
            JOIN teams t1 ON m.home_team_id = t1.team_id
            JOIN teams t2 ON m.away_team_id = t2.team_id
            WHERE m.match_date::date = CURRENT_DATE
            ORDER BY m.match_date ASC
        """
        return pd.read_sql(query, engine)
    except:
        return pd.DataFrame()

def predict_match(home, away):
    try:
        payload = {"home_team": home, "away_team": away}
        response = requests.post(API_URL, json=payload, timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# --- UI ---
teams_list = load_teams()

tab1, tab2, tab3 = st.tabs(["💎 Best Bets", "📅 Today's Fixtures", "🔮 Custom Prediction"])

# === TAB 3: Custom (Use this to test first) ===
with tab3:
    st.header("Debug / Custom Prediction")
    if not teams_list:
        st.error("No teams found! Check 'training_data_processed.csv'.")
    else:
        c1, c2 = st.columns(2)
        # Select boxes now use the EXACT names from the processed file
        with c1: home = st.selectbox("Home", teams_list, index=0)
        with c2: away = st.selectbox("Away", teams_list, index=1 if len(teams_list)>1 else 0)

        if st.button("Predict Custom"):
            res = predict_match(home, away)
            if res:
                winner = res.get("predicted_winner", "Unknown")
                if winner == "Unknown":
                    st.error(f"Stats missing for {home} or {away}. (Backend couldn't find them)")
                else:
                    st.success(f"Winner: {winner} ({res.get('confidence',0):.1%})")
                    st.bar_chart(res.get("probabilities", {}))
            else:
                st.error("API Error")

# === TAB 2: Today's Matches ===
with tab2:
    st.header("Today's Matches")
    df = get_todays_matches()
    if df.empty:
        st.info("No matches today.")
    else:
        if st.button("Predict All Today"):
            for _, row in df.iterrows():
                h, a = row['home_team'], row['away_team']
                res = predict_match(h, a)
                with st.expander(f"{h} vs {a}"):
                    if res and res.get("predicted_winner") != "Unknown":
                        st.write(f"Winner: {res['predicted_winner']}")
                    else:
                        st.warning(f"Could not predict {h} vs {a} (Name mismatch or no stats)")

# === TAB 1: Best Bets ===
with tab1:
    st.header("Best Bets (High Confidence)")
    st.write("Go to 'Today's Fixtures' first to verify names work.")