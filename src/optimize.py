import optuna
import pandas as pd
import numpy as np
import joblib
import json
import sys
import os
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def objective(trial):
    # 1. Load Data
    try:
        df = pd.read_csv(config.PROCESSED_DATA_PATH)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return -9999

    # Ensure Target
    if 'target' not in df.columns:
        conditions = [
            (df['home_goals'] < df['away_goals']),
            (df['home_goals'] == df['away_goals']),
            (df['home_goals'] > df['away_goals'])
        ]
        df['target'] = np.select(conditions, [0, 1, 2])
    
    # 2. FIX: Handle Date Format Safely (The fix is here)
    if 'match_date' in df.columns:
        # Use format='mixed' to handle "2023-05-12" AND "2023-05-12 00:00:00"
        df['date'] = pd.to_datetime(df['match_date'], format='mixed')
        df = df.sort_values('date')

    features = config.MODEL_FEATURES
    X = df[features].fillna(0)
    y = df['target'].astype(int)

    # Identify Categorical Features (League ID)
    categorical_indices = [i for i, col in enumerate(features) if col == 'league_id']

    # 3. Suggest Hyperparameters
    param = {
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'max_iter': trial.suggest_int('max_iter', 100, 1000),
        'max_depth': trial.suggest_int('max_depth', 3, 20),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 20, 200),
        'l2_regularization': trial.suggest_float('l2_regularization', 0.0, 10.0),
        'max_bins': 255,
        'categorical_features': categorical_indices,
        'class_weight': 'balanced', 
        'random_state': 42,
        'scoring': 'neg_log_loss'
    }

    # 4. Cross Validation (TimeSeriesSplit)
    tscv = TimeSeriesSplit(n_splits=3)
    
    model = HistGradientBoostingClassifier(**param)
    
    # Calculate Score
    try:
        scores = cross_val_score(model, X, y, cv=tscv, scoring='neg_log_loss', n_jobs=-1)
        return scores.mean()
    except Exception as e:
        print(f"⚠️ Trial failed: {e}")
        return -9999

if __name__ == "__main__":
    print("🧠 Starting Hyperparameter Optimization (Phase 4)...")
    print(f"📂 Data: {config.PROCESSED_DATA_PATH}")
    
    # Create Study
    study = optuna.create_study(direction="maximize") 
    study.optimize(objective, n_trials=50) 

    print("\n🏆 Best trial:")
    trial = study.best_trial
    print(f"   Value: {trial.value}")
    print("   Params: ")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")

    # Save Best Params
    best_params_path = config.MODELS_DIR / "best_params.json"
    with open(best_params_path, "w") as f:
        json.dump(trial.params, f, indent=4)
    
    print(f"\n✅ Optimization Complete. Saved to {best_params_path}")