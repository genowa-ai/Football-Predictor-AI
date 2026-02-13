import pandas as pd
import numpy as np
try:
    from src import config
except ImportError:
    import config

class TeamStatsCache:
    def __init__(self):
        self.stats = {}
        self.load_latest_stats()

    def load_latest_stats(self):
        """
        Scans the processed training data to find the MOST RECENT stats 
        (Elo, Rolling Goals, etc.) for every team.
        """
        try:
            df = pd.read_csv(config.PROCESSED_DATA_PATH)
            df['date'] = pd.to_datetime(df['match_date'], format='mixed')
            df = df.sort_values('date')
        except FileNotFoundError:
            print("⚠️ Processed data not found. Predictions will use default values.")
            return

        print("📊 Building Team Stats Cache...")
        
        # Iterate through history to update state day-by-day
        # This is a simplified "Last Known State" lookup
        for _, row in df.iterrows():
            # Update Home Team Stats
            self.stats[row['home_team']] = {
                'elo': row['home_elo'],
                'rolling_goals': row['home_rolling_goals'],
                'rolling_conceded': row['home_rolling_conceded']
            }
            # Update Away Team Stats
            self.stats[row['away_team']] = {
                'elo': row['away_elo'],
                'rolling_goals': row['away_rolling_goals'],
                'rolling_conceded': row['away_rolling_conceded']
            }
        print(f"✅ Cached stats for {len(self.stats)} teams.")

    def get_features_for_fixture(self, home_team, away_team):
        """
        Constructs the feature vector (X) for a new matchup.
        """
        # Default average values if team is new/unknown
        avg_elo = 1500.0
        avg_goals = 1.3
        
        home_stats = self.stats.get(home_team, {'elo': avg_elo, 'rolling_goals': avg_goals, 'rolling_conceded': avg_goals})
        away_stats = self.stats.get(away_team, {'elo': avg_elo, 'rolling_goals': avg_goals, 'rolling_conceded': avg_goals})

        # Calculate Diff
        elo_diff = home_stats['elo'] - away_stats['elo']

        # Build Dictionary matching the model's expected columns
        features = {
            'home_elo': home_stats['elo'],
            'away_elo': away_stats['elo'],
            'elo_diff': elo_diff,
            'home_rolling_goals': home_stats['rolling_goals'],
            'away_rolling_goals': away_stats['rolling_goals'],
            'home_rolling_conceded': home_stats['rolling_conceded'],
            'away_rolling_conceded': away_stats['rolling_conceded']
        }
        
        return features

# Singleton instance
stats_cache = TeamStatsCache()