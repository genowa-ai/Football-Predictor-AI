import time
from datetime import datetime
import sys
import os

# Import Modules
import importer
import preprocess
import train_model
import predict_smart

def run_daily_job():
    start_time = time.time()
    print(f"\n⚡ STARTING DAILY PIPELINE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # STEP 1: Import Data
    print("\n>>> [STEP 1] Data Import (API)")
    try:
        importer.run_importer()
    except Exception as e:
        print(f"❌ Importer Failed: {e}")
        return # Stop if import fails

    # STEP 2: Preprocess
    print("\n>>> [STEP 2] Feature Engineering")
    try:
        preprocess.feature_engineering_main()
    except Exception as e:
        print(f"❌ Preprocess Failed: {e}")
        return

    # STEP 3: Train Model
    print("\n>>> [STEP 3] Model Retraining")
    try:
        train_model.train_model()
    except Exception as e:
        print(f"❌ Training Failed: {e}")
        return

    # STEP 4: Predict
    print("\n>>> [STEP 4] Generating Predictions")
    try:
        predict_smart.smart_daily_predict()
    except Exception as e:
        print(f"❌ Prediction Failed: {e}")
        return

    elapsed = round(time.time() - start_time, 2)
    print("=" * 60)
    print(f"✅ PIPELINE FINISHED in {elapsed} seconds.")
    print("============================================================")

if __name__ == "__main__":
    run_daily_job()