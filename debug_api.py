import requests
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src import config
except ImportError:
    import config

def inspect_api_structure():
    # URL for games
    url = f"{config.HOCKEY_API_URL}/games"
    
    # Get games for a specific date (e.g., yesterday or today)
    # We want to see a FINISHED game to check scores
    params = {'date': '2026-01-01'} 
    headers = {'x-apisports-key': config.API_KEY}

    print(f"🕵️ Fetching raw data from: {url}")
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if not data.get('response'):
            print("❌ No games found in response. Try changing the date in the script.")
            print(f"Raw Response: {data}")
            return

        # Get the first game
        game = data['response'][0]
        
        print("\n🔎 === API RESPONSE STRUCTURE (First Game) ===")
        print(f"Match: {game['teams']['home']['name']} vs {game['teams']['away']['name']}")
        print(f"Status: {game['status']['long']}")
        
        print("\n🔢 [SCORES OBJECT]:")
        print(json.dumps(game.get('scores'), indent=4))
        
        print("\n🕒 [PERIODS OBJECT]:")
        print(json.dumps(game.get('periods'), indent=4))
        
        print("\n============================================")
        print("Copy and paste the output above so I can fix the importer!")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_api_structure()