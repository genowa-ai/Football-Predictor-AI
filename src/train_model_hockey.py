import pandas as pd
import joblib
import numpy as np
import sys
import os
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report, log_loss

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src import config
except ImportError:
    import config

# Try SHAP for Explainability
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

def train_model_hockey():
    print(f"🚀 Loading Hockey data from {config.HOCKEY_PROCESSED_PATH}...")
    
    if not config.HOCKEY_PROCESSED_PATH.exists():
        print(f"❌ Error: Data file not found. Run preprocess_hockey.py first.")
        return

    df = pd.read_csv(config.HOCKEY_PROCESSED_PATH)

    # 1. VERIFY TARGET
    # If the CSV was saved correctly, 'target' should exist.
    if 'target' not in df.columns:
        print("⚠️ 'target' column missing. Recalculating...")
        conditions = [
            (df['reg_goals_home'] < df['reg_goals_away']), # 0: Away Win
            (df['reg_goals_home'] == df['reg_goals_away']), # 1: Draw
            (df['reg_goals_home'] > df['reg_goals_away'])  # 2: Home Win
        ]
        df['target'] = np.select(conditions, [0, 1, 2])

    # 2. TIME DECAY WEIGHTING (Recent games matter more)
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.sort_values('date')
    
    print("⏳ Applying Time Decay...")
    min_date = df['date'].min()
    max_date = df['date'].max()
    days_diff = (df['date'] - min_date).dt.days
    total_days = (max_date - min_date).days
    
    if total_days == 0:
        df['sample_weight'] = 1.0
    else:
        # Weight range: 1.0 (oldest) to 3.0 (newest)
        df['sample_weight'] = 1 + (2 * (days_diff / total_days))
    
    # 3. DEFINE FEATURES
    # These must match exactly what preprocess_hockey.py created
    features = config.MODEL_FEATURES 
    print(f"✅ Training with {len(features)} Features.")
    
    X = df[features].fillna(0)
    y = df['target'].astype(int)
    weights = df['sample_weight']

    # Identify Categorical Columns (e.g. League ID)
    categorical_indices = [i for i, col in enumerate(features) if col == 'league_id']

    # 4. SPLIT TRAIN/TEST
    # We use a time-based split (Train on past, Test on future)
    split_idx = int(len(X) * 0.85)
    
    if split_idx >= len(X):
        print("❌ Error: Not enough data to create a test set.")
        return

    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    w_train = weights.iloc[:split_idx]

    # 5. TRAIN MODEL (HistGradientBoosting)
    print("🧠 Training Hockey Model (Regulation Result)...")
    model = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=300,
        max_depth=10,
        l2_regularization=1.0,
        categorical_features=categorical_indices,
        class_weight='balanced', # Important for Draws
        random_state=42,
        scoring='neg_log_loss'
    )
    model.fit(X_train, y_train, sample_weight=w_train)

    # 6. EVALUATE
    print("📊 Generating Predictions...")
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)
    
    print("\n📊 HOCKEY CLASSIFICATION REPORT:")
    
    # --- CRITICAL FIX: explicit labels prevent crash on missing classes ---
    try:
        print(classification_report(
            y_test, 
            y_pred, 
            labels=[0, 1, 2], 
            target_names=['Away', 'Draw', 'Home'], 
            zero_division=0
        ))
    except Exception as e:
        print(f"⚠️ Report Generation Error: {e}")

    try:
        loss = log_loss(y_test, y_prob, labels=[0, 1, 2])
        print(f"📉 Log Loss: {loss:.4f}")
    except Exception as e:
        print(f"⚠️ Log Loss Calculation Failed: {e}")

    # 7. SAVE MODEL
    print(f"💾 Saving Model to {config.HOCKEY_MODEL_PATH}...")
    joblib.dump(model, config.HOCKEY_MODEL_PATH)
    
    # 8. SAVE SHAP EXPLAINER (Optional)
    if SHAP_AVAILABLE:
        print("🔍 Generating SHAP Explainer...")
        try:
            # Use a small background sample for speed
            background_data = X_train.tail(200) 
            explainer = shap.Explainer(model.predict, background_data)
            
            shap_path = config.MODELS_DIR / "shap_explainer_hockey.pkl"
            print(f"💾 Saving SHAP Explainer to {shap_path}...")
            joblib.dump(explainer, shap_path)
        except Exception as e:
            print(f"⚠️ SHAP Failed: {e}")

    print("✅ Hockey Training Complete.")

if __name__ == "__main__":
    train_model_hockey()