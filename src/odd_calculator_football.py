import sys
import math

class StatsEngine:
    """
    World Class Betting Mathematics Engine
    """
    
    @staticmethod
    def calculate_kelly_stake(odds, prob_win, bankroll_fraction=0.05):
        """
        Calculates Kelly Criterion. 
        Note: We use a conservative multiplier (fraction) because full Kelly is too risky.
        """
        if odds <= 1 or prob_win <= 0: return 0.0
        
        b = odds - 1
        q = 1 - prob_win
        f = (b * prob_win - q) / b
        
        # We cap the stake at max 5% of bankroll for safety, or use the fraction
        return max(0, f * bankroll_fraction * 100)

    @staticmethod
    def calculate_poisson_probability(k, lamb):
        """Standard Poisson formula: (lambda^k * e^-lambda) / k!"""
        return (math.pow(lamb, k) * math.exp(-lamb)) / math.factorial(k)

    @staticmethod
    def simulate_match(lambda_home, lambda_away):
        """
        Generates a probability matrix for scores 0-0 up to 6-6.
        Returns: 
           - prob_draw (sum of diagonal)
           - prob_home_win (sum of lower triangle)
           - prob_away_win (sum of upper triangle)
           - most_likely_score (tuple)
        """
        prob_draw = 0.0
        prob_home = 0.0
        prob_away = 0.0
        max_p = 0.0
        likely_score = (0, 0)

        # Iterate through a goal matrix (0 to 6 goals)
        for h in range(7):
            for a in range(7):
                p_h = StatsEngine.calculate_poisson_probability(h, lambda_home)
                p_a = StatsEngine.calculate_poisson_probability(a, lambda_away)
                p_score = p_h * p_a
                
                # Update precise outcome probabilities
                if h > a:
                    prob_home += p_score
                elif a > h:
                    prob_away += p_score
                else:
                    prob_draw += p_score
                
                # Track most likely exact score
                if p_score > max_p:
                    max_p = p_score
                    likely_score = (h, a)
                    
        return prob_home, prob_draw, prob_away, likely_score

    @staticmethod
    def get_implied_double_chance_odds(odd_home, odd_away):
        """
        Calculates the theoretical Bookmaker odds for '12' (Home or Away)
        derived from the 1X2 market.
        Formula: 1 / ((1/Home) + (1/Away))
        """
        try:
            prob_h_implied = 1 / odd_home
            prob_a_implied = 1 / odd_away
            # The sum of these two probabilities represents the '12' space + vig
            # Implied Odd = 1 / (Sum of probabilities)
            return 1 / (prob_h_implied + prob_a_implied)
        except ZeroDivisionError:
            return 0.0

def calculate_bet_value():
    print("\n" + "="*60)
    print("🛡️  ANTI-DRAW PREDICTOR: WORLD CLASS EDITION  🛡️")
    print("="*60)

    try:
        # ------------------------------------------------
        # 1. ODDS INPUT
        # ------------------------------------------------
        print("\n📝 SECTION 1: MARKET DATA")
        try:
            o_h = float(input("   🏠 Home Odd: "))
            o_d = float(input("   🤝 Draw Odd: "))
            o_a = float(input("   ✈️ Away Odd: "))
        except ValueError:
            print("   ❌ Error: Please enter valid numbers (e.g. 2.50).")
            return

        # Calculate Bookie Vig/Margin
        market_margin = (1/o_h + 1/o_d + 1/o_a) - 1
        print(f"   ℹ️  Market Overround (Vig): {market_margin:.2%}")

        # ------------------------------------------------
        # 2. MODEL / STATS INPUT
        # ------------------------------------------------
        print("\n📝 SECTION 2: TEAM STATS (Last 5-10 Games Avg)")
        try:
            h_scored = float(input("   ⚽ Home Avg Scored:   "))
            h_conceded = float(input("   🛡️ Home Avg Conceded: "))
            a_scored = float(input("   ⚽ Away Avg Scored:   "))
            a_conceded = float(input("   🛡️ Away Avg Conceded: "))
        except ValueError:
            print("   ❌ Error: Stats must be numbers.")
            return

        # ------------------------------------------------
        # 3. ADVANCED CALCULATIONS
        # ------------------------------------------------
        
        # A. Expected Goals (xG) Calculation
        # We weigh recent form slightly higher. 
        # Logic: Home Expected = (HomeAttack + AwayDefense) / 2
        
        # Improvement: Prevent Zero Division or illogical stats
        if h_scored < 0 or a_conceded < 0: 
            print("   ❌ Stats cannot be negative.")
            return

        xg_home = (h_scored + a_conceded) / 2
        xg_away = (a_scored + h_conceded) / 2

        # B. Poisson Simulation
        math_home_prob, math_draw_prob, math_away_prob, exact_score = \
            StatsEngine.simulate_match(xg_home, xg_away)
            
        math_no_draw_prob = math_home_prob + math_away_prob

        # C. Double Chance (12) Market Analysis
        # What is the bookie offering for "No Draw"?
        bookie_12_odd = StatsEngine.get_implied_double_chance_odds(o_h, o_a)

        # ------------------------------------------------
        # 4. REPORT GENERATION
        # ------------------------------------------------
        print("\n" + "-"*60)
        print(f"📊 ANALYTICAL REPORT: {xg_home:.2f} xG vs {xg_away:.2f} xG")
        print("-"*60)
        
        # Print Probabilities
        print(f"{'OUTCOME':<15} | {'MATH PROB':<12} | {'BOOKIE PROB':<12} | {'VALUE EDGE'}")
        print("-" * 55)
        
        # Helper to calc edge
        def calc_edge(model_p, odd):
            return (model_p * odd - 1) * 100

        # Home
        edge_h = calc_edge(math_home_prob, o_h)
        implied_h = 1/o_h
        print(f"{'Home Win':<15} | {math_home_prob:<12.1%} | {implied_h:<12.1%} | {edge_h:+.2f}%")
        
        # Draw
        edge_d = calc_edge(math_draw_prob, o_d)
        implied_d = 1/o_d
        print(f"{'Draw':<15} | {math_draw_prob:<12.1%} | {implied_d:<12.1%} | {edge_d:+.2f}%")
        
        # Away
        edge_a = calc_edge(math_away_prob, o_a)
        implied_a = 1/o_a
        print(f"{'Away Win':<15} | {math_away_prob:<12.1%} | {implied_a:<12.1%} | {edge_a:+.2f}%")

        print("-" * 55)
        print(f"🎯 Most Likely Score: {exact_score[0]} - {exact_score[1]}")

        # ------------------------------------------------
        # 5. THE ANTI-DRAW (DOUBLE CHANCE) VERDICT
        # ------------------------------------------------
        print("\n🛡️ --- ANTI-DRAW (12) VERDICT ---")
        
        # 1. Calculate Edge on "12"
        # We use the calculated Bookie 12 Odd.
        edge_12 = calc_edge(math_no_draw_prob, bookie_12_odd)
        
        print(f"   Model 'No Draw' Chance: {math_no_draw_prob:.1%}")
        print(f"   Est. Bookie '12' Odd:   {bookie_12_odd:.2f}")
        print(f"   Value Edge on '12':     {edge_12:+.2f}%")

        # 2. Risk Factors
        risk_flags = []
        if math_draw_prob > 0.25: risk_flags.append("High Poisson Draw Probability")
        if abs(xg_home - xg_away) < 0.25: risk_flags.append("Teams are too evenly matched")
        if market_margin > 0.08: risk_flags.append("High Bookmaker Margin (Bad Odds)")

        if risk_flags:
            print(f"\n   ⚠️ CAUTION: {', '.join(risk_flags)}")
        
        # 3. Final Recommendation
        print("\n   🏆 RECOMMENDATION:")
        
        # Logic Hierarchy
        if math_draw_prob > 0.25:
            print("   ⛔ AVOID MATCH. Extreme Draw Risk detected.")
        elif edge_12 > 2.0:
            print("   ✅ BET DOUBLE CHANCE (12).")
            print("      Explanation: The probability of a winner is higher than odds suggest.")
            stake = StatsEngine.calculate_kelly_stake(bookie_12_odd, math_no_draw_prob, 0.25)
            print(f"      Suggested Stake: {stake:.2f}%")
        elif edge_h > 5.0:
             print("   ✅ VALUE ON HOME WIN (High Confidence).")
             stake = StatsEngine.calculate_kelly_stake(o_h, math_home_prob, 0.25)
             print(f"      Suggested Stake: {stake:.2f}%")
        elif edge_a > 5.0:
             print("   ✅ VALUE ON AWAY WIN (High Confidence).")
             stake = StatsEngine.calculate_kelly_stake(o_a, math_away_prob, 0.25)
             print(f"      Suggested Stake: {stake:.2f}%")
        else:
            print("   ⏸️ NO BET. Market is efficient (No value found).")

    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    while True:
        calculate_bet_value()
        if input("\n🔄 Check another match? (y/n): ").lower() != 'y': break