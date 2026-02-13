import sys
import math

# --------------------------------------------------------------------------
# STATS ENGINE
# --------------------------------------------------------------------------
class StatsEngine:
    @staticmethod
    def calculate_kelly_stake(o, p, fraction=0.25):
        """ Calculates Kelly Criterion stake percentage. """
        if o <= 1: return 0.0
        b = o - 1
        f = (b * p - (1-p)) / b
        return max(0, f * fraction * 100)
    
    @staticmethod
    def calculate_poisson_draw_chance(lambda_home, lambda_away):
        """ Calculates the pure mathematical chance of a draw based on expected goals. """
        # HOCKEY ADAPTATION: Check up to 9-9 scores
        prob_draw = 0.0
        for k in range(0, 10): 
            p_h = (math.pow(lambda_home, k) * math.exp(-lambda_home)) / math.factorial(k)
            p_a = (math.pow(lambda_away, k) * math.exp(-lambda_away)) / math.factorial(k)
            prob_draw += (p_h * p_a)
        return prob_draw

# --------------------------------------------------------------------------
# MAIN CALCULATOR
# --------------------------------------------------------------------------
def calculate_hockey_value():
    print("\n🏒 --- HOCKEY VALUE & DOUBLE CHANCE CALCULATOR --- 🏒")
    print("NOTE: Use Regulation (3-Way) stats.")
    
    try:
        # ------------------------------------------------
        # 1. ODDS INPUT
        # ------------------------------------------------
        print("\n--- 1. BOOKMAKER ODDS (Regulation) ---")
        odd_home = float(input("🏠 Home Reg Win (e.g., 2.10): "))
        odd_draw = float(input("🤝 Reg Draw     (e.g., 4.20): "))
        odd_away = float(input("✈️ Away Reg Win (e.g., 2.90): "))
        
        implied_draw_prob = 1 / odd_draw

        # ------------------------------------------------
        # 2. MODEL PREDICTION
        # ------------------------------------------------
        print("\n--- 2. MODEL PREDICTION ---")
        prob_home = float(input("🏠 Model Home % (e.g., 45): ")) / 100
        prob_draw = float(input("🤝 Model Draw % (e.g., 22): ")) / 100
        
        prob_away = 1.0 - (prob_home + prob_draw)
        
        # [FEATURE 1] Calculate "No Draw" (12) Probability
        prob_no_draw = prob_home + prob_away

        # ------------------------------------------------
        # 3. GOAL METRICS (PHYSICS ENGINE)
        # ------------------------------------------------
        print("\n--- 3. GOAL METRICS (Season Averages) ---")
        # Attack Strength
        h_scored = float(input("🏒 Avg Goals SCORED by Home:   "))
        a_scored = float(input("🏒 Avg Goals SCORED by Away:   "))
        
        # Defense Strength
        h_conceded = float(input("🛡️ Avg Goals CONCEDED by Home: "))
        a_conceded = float(input("🛡️ Avg Goals CONCEDED by Away: "))

        # ------------------------------------------------
        # 4. CALCULATIONS
        # ------------------------------------------------
        
        # Calculate Expected Goals (Attack vs Defense)
        if h_conceded > 0 and a_conceded > 0:
            exp_home_goals = (h_scored + a_conceded) / 2
            exp_away_goals = (a_scored + h_conceded) / 2
            print(f"\n📐 Physics Expectation: {exp_home_goals:.2f} - {exp_away_goals:.2f}")
        else:
            exp_home_goals = h_scored
            exp_away_goals = a_scored

        # Poisson Draw Probability
        poisson_draw = StatsEngine.calculate_poisson_draw_chance(exp_home_goals, exp_away_goals)
        
        # Double Chance Probabilities (Based on your Model)
        prob_1x = prob_home + prob_draw  # Home or Draw
        prob_x2 = prob_away + prob_draw  # Away or Draw
        
        # ------------------------------------------------
        # 5. THE REPORT
        # ------------------------------------------------
        print(f"\n📊 --- STATISTICAL REPORT ---")
        
        # A. PROBABILITIES
        print(f"Probabilities:")
        print(f"   🏠 Home Win: {prob_home:.1%}")
        print(f"   ✈️ Away Win: {prob_away:.1%}")
        print(f"   🤝 Draw:     {prob_draw:.1%}")
        print(f"   -----------------------")
        print(f"   🚫 NO DRAW (12): {prob_no_draw:.1%} (Chance of a Winner)")
        
        # B. DRAW ANALYSIS
        print(f"\nDraw Safety Check:")
        print(f"   Bookie Implied: {implied_draw_prob:.1%}")
        print(f"   Physics (Poisson): {poisson_draw:.1%}")
        
        if poisson_draw > 0.24:
            print("   ⚠️ WARNING: Poisson indicates high draw risk!")

        # C. VALUE CALCULATION (REGULATION)
        edge_home = ((prob_home * odd_home) - 1) * 100
        edge_away = ((prob_away * odd_away) - 1) * 100

        print("\n🏆 --- VERDICT ---")

        # ------------------------------------------------
        # [FEATURE 2] THE "GO AHEAD" SECTION
        # ------------------------------------------------
        
        # Logic for "Go Ahead"
        # We prefer Double Chance if the main win probability is decent, 
        # but we want to cover the draw to be safe.
        
        recommended = False
        
        # Case 1: Favoring HOME
        if prob_home > prob_away:
            print(f"   Signal: Favoring Home")
            if edge_home > 0 and poisson_draw < 0.23:
                print(f"   👉 VALUE: Home Win (Edge +{edge_home:.1f}%)")
                stake = StatsEngine.calculate_kelly_stake(odd_home, prob_home, 0.25)
                print(f"      Kelly Stake: {stake:.2f}%")
            
            # Double Chance Check
            if prob_1x > 0.65: # If combined chance is > 65%
                print(f"\n   🟢 GO AHEAD: Double Chance 1X (Home/Draw)")
                print(f"      Combined Probability: {prob_1x:.1%}")
                recommended = True

        # Case 2: Favoring AWAY
        elif prob_away > prob_home:
            print(f"   Signal: Favoring Away")
            if edge_away > 0 and poisson_draw < 0.23:
                print(f"   👉 VALUE: Away Win (Edge +{edge_away:.1f}%)")
                stake = StatsEngine.calculate_kelly_stake(odd_away, prob_away, 0.25)
                print(f"      Kelly Stake: {stake:.2f}%")

            # Double Chance Check
            if prob_x2 > 0.65:
                print(f"\n   🟢 GO AHEAD: Double Chance X2 (Away/Draw)")
                print(f"      Combined Probability: {prob_x2:.1%}")
                recommended = True

        # Case 3: NO DRAW (Any Winner)
        # If the draw chance is very low, '12' is a good double chance.
        if poisson_draw < 0.18 and prob_no_draw > 0.78:
            print(f"\n   🟢 GO AHEAD: Double Chance 12 (Any Winner)")
            print(f"      Physics Draw Chance is low ({poisson_draw:.1%})")
            recommended = True

        if not recommended:
            print("\n   🔸 STAY AWAY: No strong Double Chance signal found.")

    except ValueError:
        print("❌ Error: Invalid number entered.")
    except ZeroDivisionError:
        print("❌ Error: Odds cannot be zero.")

if __name__ == "__main__":
    while True:
        calculate_hockey_value()
        if input("\nCheck another? (y/n): ").lower() != 'y': break