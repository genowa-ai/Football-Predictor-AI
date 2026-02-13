import time
from datetime import datetime
import sys
import os

# Import Hockey Modules
import importer_hockey
import preprocess_hockey
import train_model_hockey
import predict_smart_hockey

def run_hockey_job():
    start_time = time.time()
    print(f"\n🏒 STARTING HOCKEY PIPELINE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # STEP 1: Import (Results & Fixtures)
    print("\n>>> [STEP 1] Importing Data...")
    try:
        importer_hockey.run_importer()
    except Exception as e:
        print(f"❌ Importer Failed: {e}")
        return

    # STEP 2: Preprocess (Feature Engineering)
    print("\n>>> [STEP 2] Processing Features...")
    try:
        preprocess_hockey.feature_engineering_hockey()
    except Exception as e:
        print(f"❌ Preprocess Failed: {e}")
        return

    # STEP 3: Train (Retrain Model on new results)
    print("\n>>> [STEP 3] Retraining Model...")
    try:
        train_model_hockey.train_model_hockey()
    except Exception as e:
        print(f"❌ Training Failed: {e}")
        return

    # STEP 4: Predict (Sniper Mode)
    print("\n>>> [STEP 4] Generating Predictions...")
    try:
        predict_smart_hockey.smart_daily_predict_hockey()
    except Exception as e:
        print(f"❌ Prediction Failed: {e}")
        return

    elapsed = round(time.time() - start_time, 2)
    print("=" * 60)
    print(f"✅ HOCKEY PIPELINE FINISHED in {elapsed} seconds.")
    print("============================================================")

if __name__ == "__main__":
    run_hockey_job()
