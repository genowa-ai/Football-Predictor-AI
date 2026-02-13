import pandas as pd
import joblib
import json
import numpy as np
import sys
import os
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix, log_loss

# Try importing SHAP
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("⚠️ SHAP library not installed. Explainer will not be generated.")

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src import config
except ImportError:
    import config

def train_model():
    print(f"🚀 Loading processed data from {config.PROCESSED_DATA_PATH}...")
    if not config.PROCESSED_DATA_PATH.exists():
        print(f"❌ Error: Data file not found at {config.PROCESSED_DATA_PATH}")
        return

    df = pd.read_csv(config.PROCESSED_DATA_PATH)

    # 1. DEFINE TARGET
    if 'target' not in df.columns:
        conditions = [
            (df['home_goals'] < df['away_goals']),
            (df['home_goals'] == df['away_goals']),
            (df['home_goals'] > df['away_goals'])
        ]
        df['target'] = np.select(conditions, [0, 1, 2])

    # 2. DATE SORT & TIME DECAY
    if 'match_date' in df.columns:
        df['date'] = pd.to_datetime(df['match_date'], format='mixed')
        df = df.sort_values('date')
        
        print("⏳ Applying Time Decay (Recency Weighting)...")
        min_date = df['date'].min()
        max_date = df['date'].max()
        days_diff = (df['date'] - min_date).dt.days
        total_days = (max_date - min_date).days
        # Standard weighting curve
        df['sample_weight'] = 1 + (2 * (days_diff / total_days))
    else:
        df['sample_weight'] = 1.0 
    
    # 3. FEATURES
    features = config.MODEL_FEATURES
    print(f"✅ Training with {len(features)} Features.")
    
    X = df[features].fillna(0)
    y = df['target'].astype(int)
    weights = df['sample_weight']

    categorical_indices = [i for i, col in enumerate(features) if col == 'league_id']
    if categorical_indices:
        print(f"ℹ️ Categorical Feature Indices: {categorical_indices}")

    # 4. SPLIT
    split_idx = int(len(X) * 0.85)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    w_train = weights.iloc[:split_idx]

    # 5. INITIALIZE MODEL (RESTORED BALANCED MODE)
    model_params = {
        'learning_rate': 0.05,
        'max_iter': 300,
        'max_depth': 12,
        'l2_regularization': 1.0,
        'categorical_features': categorical_indices,
        
        # RESTORED: 'balanced' ensures the model learns to identify Draws again.
        'class_weight': 'balanced', 
        
        'random_state': 42,
        'scoring': 'neg_log_loss'
    }

    # Load optimized params
    params_path = config.MODELS_DIR / "best_params.json"
    if os.path.exists(params_path):
        print(f"⚡ Loading optimized params from {params_path}...")
        with open(params_path, "r") as f:
            best_params = json.load(f)
        model_params.update(best_params)
        model_params['categorical_features'] = categorical_indices 
        # Force balanced
        model_params['class_weight'] = 'balanced'

    print("🧠 Training HistGradientBoostingClassifier (Balanced Mode)...")
    model = HistGradientBoostingClassifier(**model_params)
    model.fit(X_train, y_train, sample_weight=w_train)

    # 6. EVALUATE
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)
    
    print("\n📊 CLASSIFICATION REPORT:")
    print(classification_report(y_test, y_pred, target_names=['Away', 'Draw', 'Home']))
    print(f"📉 Log Loss: {log_loss(y_test, y_prob):.4f}")

    # 7. SAVE EVERYTHING
    print(f"💾 Saving Model to {config.MODEL_PATH}...")
    joblib.dump(model, config.MODEL_PATH)
    
    with open(config.FEATURE_COLUMNS_PATH, 'w') as f:
        json.dump(features, f)

    if SHAP_AVAILABLE:
        print("🔍 Generating SHAP Explainer...")
        try:
            background_data = X_train.tail(500)
            explainer = shap.Explainer(model.predict, background_data)
            
            # --- UPDATE: Added Print Statement Here ---
            print(f"💾 Saving SHAP Explainer to {config.SHAP_EXPLAINER_PATH}...")
            joblib.dump(explainer, config.SHAP_EXPLAINER_PATH)
            
        except Exception as e:
            print(f"⚠️ SHAP Generation Failed: {e}")

    print("✅ Training Pipeline Complete.")

if __name__ == "__main__":
    train_model()