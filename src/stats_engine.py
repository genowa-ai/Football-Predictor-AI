import math
import numpy as np

class StatsEngine:
    """
    Central Logic for Statistical Tools.
    Phase 5 Update: Added Implied Probability & Value Engine.
    """

    # --- 1. ODDS & MARKET ANALYSIS (NEW) ---
    @staticmethod
    def calculate_implied_prob(odd):
        """Converts Decimal Odds (2.00) to Probability (0.50)."""
        if odd <= 1.0: return 0.0
        return 1.0 / odd

    @staticmethod
    def calculate_value(model_prob, implied_prob):
        """
        Returns the 'Edge' percentage. 
        Positive = Good Value (Model is more confident than Bookie).
        """
        return model_prob - implied_prob

    # --- 2. POISSON DISTRIBUTION ---
    @staticmethod
    def calculate_poisson_draw_chance(home_avg_goals, away_avg_goals):
        def poisson_pmf(k, lam):
            return (lam**k * math.exp(-lam)) / math.factorial(k)

        prob_draw = 0.0
        # Check scores 0-0, 1-1, 2-2, 3-3
        for i in range(4):
            p_home = poisson_pmf(i, home_avg_goals)
            p_away = poisson_pmf(i, away_avg_goals)
            prob_draw += (p_home * p_away)
        
        return prob_draw

    # --- 3. TRUE ELO CALCULATOR ---
    @staticmethod
    def expected_result(elo_a, elo_b):
        return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

    @staticmethod
    def calculate_elo_change(elo_home, elo_away, home_goals, away_goals, k_factor=30, home_adv=100):
        if home_goals > away_goals: actual = 1.0
        elif home_goals == away_goals: actual = 0.5
        else: actual = 0.0

        expected_home = StatsEngine.expected_result(elo_home + home_adv, elo_away)

        goal_diff = abs(home_goals - away_goals)
        mov_multiplier = 1.0 if goal_diff <= 1 else np.log(goal_diff + 1)

        return k_factor * mov_multiplier * (actual - expected_home)