import time
from datetime import datetime, timedelta
from importer_hockey import HockeyImporter
try:
    from src import config
except ImportError:
    import config

def smart_backfill():
    importer = HockeyImporter()
    
    # SAFETY SETTING: 7 seconds ensures we never exceed 10 req/min
    COOLDOWN = 7 
    
    print(f"🚀 STARTING SMART BACKFILL (Rate Limit Safe: {COOLDOWN}s delay)")
    print("--------------------------------")
    
    # --- PHASE 1: HISTORICAL SEASONS ---
    historical_seasons = [2022, 2023, 2024]
    leagues = config.HOCKEY_LEAGUES
    
    print(f"\n📚 PHASE 1: Fetching Historical Seasons {historical_seasons}")
    
    for league_id in leagues:
        for season in historical_seasons:
            games = importer.fetch_season_games(league_id, season)
            if games:
                importer.save_to_db(games)
            
            # WAIT to respect rate limit
            time.sleep(COOLDOWN)
            
    # --- PHASE 2: CURRENT SEASON (Daily Fetch) ---
    days_back = 10 # Adjusted to 10 to ensure we finish in one run within limit
    print(f"\n📅 PHASE 2: Fetching Recent Games (Last {days_back} days)")
    
    start_date = datetime.now() - timedelta(days=1)
    
    for i in range(days_back):
        target_date = (start_date - timedelta(days=i)).strftime('%Y-%m-%d')
        
        print(f"📅 Processing {target_date}...", end=" ")
        
        # Fetch
        games = importer.fetch_fixtures(target_date)
        
        # Save
        if games:
            importer.save_to_db(games)
        else:
            print("") # New line if no games found
            
        # WAIT
        time.sleep(COOLDOWN)
        
    print(f"\n\n✅ SMART BACKFILL COMPLETE.")

if __name__ == "__main__":
    smart_backfill()