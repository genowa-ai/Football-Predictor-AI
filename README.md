Football-Predictor-AI/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── src/
│   ├── run_pipeline.py
│   ├── run_hockey_pipeline.py
│   │
│   ├── importer.py
│   ├── importer_hockey.py
│   │
│   ├── preprocess.py
│   ├── preprocess_hockey.py
│   │
│   ├── train_model.py
│   ├── train_hockey_model.py
│   │
│   ├── predict_smart.py
│   ├── predict_hockey_smart.py
│   │
│   ├── optimize.py
│   ├── optimize_hockey.py
│   │
│   ├── generate_mapping_smart.py
│   ├── predicts_utils.py
│   ├── utils.py
│   ├── config.py
│   └── stats_engine.py   (NOT PROVIDED—ADD YOUR FILE HERE)
│
├── models/
│   ├── no_draw_model.pkl
│   ├── hockey_regulation_model.pkl
│   ├── shap_explainer.pkl
│   ├── feature_columns.json
│   ├── best_params.json
│   └── best_params_hockey.json
│
├── data/
│   ├── training_data.csv
│   ├── training_data_processed.csv
│   ├── training_data_hockey.csv
│   └── team_mapping.csv
│
└── predictions/
    ├── predictions_YYYY-MM-DD.csv
    └── hockey_predictions_YYYY-MM-DD.csv

 # 🧠 Football Predictor AI & 🏒 Hockey Predictor AI

An end‑to‑end **machine learning prediction system** for football and hockey, built with:

- Automated daily ETL pipelines  
- API ingestion (API‑Sports Football + Hockey)  
- PostgreSQL storage  
- Feature engineering  
- Elo ratings  
- Rolling statistics  
- Smart no‑draw prediction logic  
- HistGradientBoostingClassifier (scikit‑learn)  
- Optuna hyperparameter optimization  
- SHAP explainability  
- Sniper‑mode daily predictions  

This project generates **daily predictions** for:
- Football (No‑Draw Model → Double Chance style)
- Hockey (Regulation Time Model → 1X2)

Everything is fully automated, except the manual daily run.

---

## 📁 Project Overview

This repository contains two complete ML systems:

### ⚽ **Football Predictor AI**
Predicts **Home or Away only** (No‑Draw model), using:
- Elo ratings  
- Rolling goals  
- Rolling conceded  
- BTTS interaction  
- Rest‑day fatigue  
- League ID categorical feature  
- Daily importer for results, fixtures, odds, injuries  
- Daily predictions with value calculations & injury checks  

### 🏒 **Hockey Predictor AI**
Predicts **Regulation‑time 1X2**, using:
- Regulation goals only (3‑period scores)
- Custom hockey Elo system  
- Rolling averages for scoring & conceding  
- BTTS rates  
- Rest days  
- Sniper prediction mode  
- API‑Sports Hockey data importer  

---

## 🔥 Features

- Automated daily data ingestion (matches, fixtures, odds, injuries)
- Full PostgreSQL storage
- Smart league/team mapping
- Feature engineering (rolling stats, Elo, fatigue, BTTS)
- No‑draw football logic (filters out draws before prediction)
- Regulation‑time hockey logic
- Optuna tuning for both sports
- SHAP explainability support
- Full training pipeline for both sports
- Prediction output saved to CSV daily

---

## 📂 Repository Structure


src/
│── run_pipeline.py                 # Football daily job
│── run_hockey_pipeline.py          # Hockey daily job
│── importer.py                     # Football API importer
│── importer_hockey.py              # Hockey API importer
│── preprocess.py                   # Football preprocessing
│── preprocess_hockey.py            # Hockey preprocessing
│── train_model.py                  # Football model trainer
│── train_hockey_model.py           # Hockey model trainer
│── predict_smart.py                # Football predictions
│── predict_hockey_smart.py         # Hockey predictions
│── optimize.py                     # Optuna tuning (football)
│── optimize_hockey.py              # Optuna tuning (hockey)
│── generate_mapping_smart.py       # Smart CSV-to-API team name mapping
│── predicts_utils.py
│── utils.py
│── config.py                       # API keys, DB config, feature list
│── stats_engine.py                 # Your elo + statistical helpers

---

## 🧠 ML Approach

### Football Model
- 3‑class classification (Away, Draw, Home)
- Converted into a **No‑Draw double‑chance prediction**
- Model: HistGradientBoostingClassifier
- Balanced class weights  
- Custom recency weighting  
- 15 engineered features  
- Sniper logic for:
  - Low draw probability filters
  - Odds implied probability checks
  - Edge (Value) calculation
  - Injury penalties
  - Poisson draw risk scoring

### Hockey Model
- 3‑class regulation result model
- 5‑game rolling averages
- Hockey‑specific Elo (K‑factor 30)
- Balanced class weights
- Sniper recommendation engine

---

## 🛠 Installation

```bash
git clone https://github.com/yourusername/Football-Predictor-AI
cd Football-Predictor-AI
pip install -r requirements.txt


🗄 PostgreSQL Setup
Create the database:
CREATE DATABASE football_db;
Tables are auto‑created when the importer runs.

🚀 Running the Daily Pipelines
Football
src/run_pipeline.py
Hockey
src/run_hockey_pipeline.py

📈 Hyperparameter Optimization (Optional)
Football:
src/optimize.py
Hockey:
src/optimize_hockey.py
This writes:

* best_params.json
* best_params_hockey.json

Models automatically reload tuned parameters during training.

📊 Prediction Outputs
Football predictions saved as:
predictions_YYYY-MM-DD.csv

Hockey predictions saved as:
hockey_predictions_YYYY-MM-DD.csv

Each includes:

* Match
* Tip
* Confidence
* Probabilities
* Odds
* Value edge
* Status
* Injuries (football)


🧩 API Mapping (CSV → API names)
Run this to map your CSV historical datasets to the real API‑Sports team names:
bashDownloadCopy codepython src/generate_mapping_smart.py
Outputs:
team_mapping.csv


📜 Environment Variables
Create a `.env` file in the project root using `env.example`:
API_KEY = "your_api_key_here"


🤝 Contributions
Pull requests welcome.

📄 License
MIT License.   