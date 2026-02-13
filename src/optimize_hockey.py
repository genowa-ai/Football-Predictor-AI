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
try:
    from src import config
except ImportError:
    import config

def objective(trial):
    # 1. Load HOCKEY Data
    try:
        df = pd.read_csv(config.HOCKEY_PROCESSED_PATH)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return -9999

    # 2. Ensure Target (Regulation Result)
    if 'target' not in df.columns:
        conditions = [
            (df['reg_goals_home'] < df['reg_goals_away']),
            (df['reg_goals_home'] == df['reg_goals_away']),
            (df['reg_goals_home'] > df['reg_goals_away'])
        ]
        df['target'] = np.select(conditions, [0, 1, 2])
    
    # 3. Handle Date
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], format='mixed')
        df = df.sort_values('date')

    features = config.MODEL_FEATURES
    X = df[features].fillna(0)
    y = df['target'].astype(int)

    categorical_indices = [i for i, col in enumerate(features) if col == 'league_id']

    # 4. Suggest Hyperparameters (Tuned for Hockey's Higher Variance)
    param = {
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'max_iter': trial.suggest_int('max_iter', 100, 1000),
        'max_depth': trial.suggest_int('max_depth', 3, 25), # Hockey might need deeper trees
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 20, 200),
        'l2_regularization': trial.suggest_float('l2_regularization', 0.0, 10.0),
        'max_bins': 255,
        'categorical_features': categorical_indices,
        'class_weight': 'balanced', 
        'random_state': 42,
        'scoring': 'neg_log_loss'
    }

    # 5. Cross Validation
    tscv = TimeSeriesSplit(n_splits=3)
    model = HistGradientBoostingClassifier(**param)
    
    try:
        scores = cross_val_score(model, X, y, cv=tscv, scoring='neg_log_loss', n_jobs=-1)
        return scores.mean()
    except Exception as e:
        return -9999

if __name__ == "__main__":
    print("🧠 Starting HOCKEY Hyperparameter Optimization...")
    print(f"📂 Data: {config.HOCKEY_PROCESSED_PATH}")
    
    study = optuna.create_study(direction="maximize") 
    study.optimize(objective, n_trials=50) # 50 trials is usually enough for a quick tune

    print("\n🏆 Best Hockey Trial:")
    trial = study.best_trial
    print(f"   Value: {trial.value}")
    print("   Params: ")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")

    # Save Best Params specifically for Hockey
    best_params_path = config.MODELS_DIR / "best_params_hockey.json"
    with open(best_params_path, "w") as f:
        json.dump(trial.params, f, indent=4)
    
    print(f"\n✅ Optimization Complete. Saved to {best_params_path}")