import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()# This loads the variables from your .env file

# Now read the key

API_KEY = os.getenv("API_KEY")

# Base Directory
BASE_DIR = Path(__file__).parent.parent

# --- FILE PATHS ---
RAW_DATA_PATH = BASE_DIR / "training_data.csv" 
PROCESSED_DATA_PATH = BASE_DIR / "training_data_processed.csv"
MAPPING_DATA_PATH = BASE_DIR / "team_mapping.csv"

# --- MODEL PATHS ---
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODELS_DIR / "no_draw_model.pkl"
SHAP_EXPLAINER_PATH = MODELS_DIR / "shap_explainer.pkl"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.json"

# --- DATABASE CONFIG ---
DB_NAME = "football_db"
DB_USER = "postgres"
DB_PASS = "1004"
DB_HOST = "localhost"
DB_PORT = "5432"

# --- SNIPER CONFIG (PHASE 5 UPGRADE) ---
# These control how the 'predict_smart.py' uses the new data.
SNIPER_THRESHOLDS = {
    'MAX_DRAW_ODDS_IMPLIED': 0.34,  # If Market says Draw > 34%, we skip (Too risky)
    'MIN_VALUE_EDGE': 0.05,         # We want Model Prob to be 5% higher than Implied Prob
    'INJURY_PENALTY': 0.03          # Reduce confidence by 3% for every key injury
}

# --- FEATURES (CORE SYSTEM - DO NOT CHANGE) ---
# We keep these purely "Fact-Based" for training stability.
MODEL_FEATURES = [
    'league_id', 
    'home_elo', 'away_elo', 'elo_diff',
    'home_rolling_goals', 'away_rolling_goals',
    'home_rolling_conceded', 'away_rolling_conceded',
    'form_diff', 'defensive_diff',
    'home_btts_rate', 'away_btts_rate', 'btts_interaction',
    'home_rest_days', 'away_rest_days', 'rest_diff'
]

# ... (Your existing code) ...

# --- HOCKEY CONFIGURATION (NEW) ---
HOCKEY_API_URL = "https://v1.hockey.api-sports.io"
HOCKEY_TABLE = "hockey_fixtures"
HOCKEY_PROCESSED_PATH = BASE_DIR / "training_data_hockey.csv"
HOCKEY_MODEL_PATH = MODELS_DIR / "hockey_regulation_model.pkl"

# OPTION B: Curated List of Major Leagues (To avoid "junk" data)
HOCKEY_LEAGUES = [
    57,   # NHL (USA/Canada)
    58,   # AHL (USA)
    193,  # KHL (Russia)
    133,  # SHL (Sweden)
    135,  # Liiga (Finland)
    146,  # DEL (Germany)
    173,  # National League (Switzerland)
    142,  # Extraliga (Czech)
    128,  # ICE Hockey League (Austria)
    6,    # Champions Hockey League
    1,    # World Championships
    2     # Olympics
]