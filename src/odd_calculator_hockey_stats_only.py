import sys
import math

# --------------------------------------------------------------------------
# STATS ENGINE STUB
# --------------------------------------------------------------------------
class StatsEngine:
    @staticmethod
    def calculate_kelly_stake(o, p, fraction=0.25):
        if o <= 1: return 0.0
        b = o - 1
        f = (b * p - (1-p)) / b
        return max(0, f * fraction * 100)
    
    @staticmethod
    def calculate_poisson_draw_chance(lambda_home, lambda_away):
        # Calculate chance of exact score matches (0-0, 1-1, ... 9-9)
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
    print("\n🏒 --- HOCKEY H2H VALUE CALCULATOR --- 🏒")
    
    try:
        # ------------------------------------------------
        # 1. ODDS INPUT
        # ------------------------------------------------
        print("\n--- 1. BOOKMAKER ODDS (60 MIN / REGULATION) ---")
        odd_home = float(input("🏠 Home Reg Win (e.g., 2.10): "))
        odd_draw = float(input("🤝 Reg Draw     (e.g., 4.20): "))
        odd_away = float(input("✈️ Away Reg Win (e.g., 2.90): "))
        
        implied_draw_prob = 1 / odd_draw

        # ------------------------------------------------
        # 2. MODEL PREDICTION (Or Personal Confidence)
        # ------------------------------------------------
        print("\n--- 2. YOUR PREDICTION ---")
        prob_home = float(input("🏠 Your Home Win % (e.g., 45): ")) / 100
        prob_draw = float(input("🤝 Your Draw %     (e.g., 22): ")) / 100
        
        prob_away = 1.0 - (prob_home + prob_draw)
        
        # [NEW] Calculate "No Draw" (Any Win) Probability
        prob_no_draw = prob_home + prob_away

        # ------------------------------------------------
        # 3. PREVIOUS MEETINGS (HEAD-TO-HEAD)
        # ------------------------------------------------
        print("\n--- 3. PREVIOUS MEETINGS (H2H) ---")
        print("Enter data from the last few times these teams played each other.")
        
        games_played = int(input("📅 Total Games Checked: "))
        
        if games_played > 0:
            h_wins_h2h = int(input("🏠 Times HOME Team Won: "))
            a_wins_h2h = int(input("✈️ Times AWAY Team Won: "))
            
            # Using Highest Score as a proxy for offensive potential
            # (If a team scored 5 once, they have the potential to score high)
            h_highest = float(input("🔥 Highest goals HOME scored in a single match: "))
            a_highest = float(input("🔥 Highest goals AWAY scored in a single match: "))
            
            # ------------------------------------------------
            # 4. THE ESTIMATION ENGINE
            # ------------------------------------------------
            # Logic: We estimate expected goals based on Win Rate and Peak Performance.
            # If Home wins 80% of H2H, their expected goals shift closer to their highest score.
            
            h_win_rate = h_wins_h2h / games_played
            a_win_rate = a_wins_h2h / games_played
            
            # Base expectation (Average hockey team scores ~2.5 to 3.0)
            base_score = 2.5
            
            # Adjust based on history
            # If they win often, Exp Goals = Weighted avg of Base and Highest
            exp_home_goals = base_score + (h_win_rate * (h_highest - base_score))
            exp_away_goals = base_score + (a_win_rate * (a_highest - base_score))
            
            print(f"\n📐 Estimated Strength (Goals): {exp_home_goals:.2f} - {exp_away_goals:.2f}")
        else:
            # Fallback if no history
            exp_home_goals = 2.7
            exp_away_goals = 2.7
            print("\n📐 No history provided, assuming equal strength.")

        # Poisson Draw Probability
        poisson_draw = StatsEngine.calculate_poisson_draw_chance(exp_home_goals, exp_away_goals)
        
        # ------------------------------------------------
        # 5. THE REPORT
        # ------------------------------------------------
        print(f"\n📊 --- STATISTICAL REPORT ---")
        
        # A. NO DRAW CALCULATION (Requested Feature)
        print(f"Outcome Probabilities:")
        print(f"   Home Win: {prob_home:.1%}")
        print(f"   Away Win: {prob_away:.1%}")
        print(f"   Draw:     {prob_draw:.1%}")
        print(f"   -----------------------")
        print(f"   🚫 NO DRAW (12): {prob_no_draw:.1%} (Chance someone wins in Reg)")

        # B. DRAW ANALYSIS
        print(f"\nDraw Indicators:")
        print(f"   Bookie Implied: {implied_draw_prob:.1%}")
        print(f"   Math (H2H):     {poisson_draw:.1%}")
        
        # C. VALUE CALCULATION
        edge_home = ((prob_home * odd_home) - 1) * 100
        edge_away = ((prob_away * odd_away) - 1) * 100

        print("\n🏆 --- VERDICT ---")

        # HOCKEY SAFETY CHECKS
        is_safe_match = poisson_draw < 0.24 and prob_draw < 0.24

        if not is_safe_match:
            print("⚠️ CAUTION: High Risk of Overtime/Draw.")
            print("   👉 Consider betting 'Moneyline' (Incl. OT).")
        else:
            print("✅ REGULATION BET VIABLE")
            
            # Suggest bet based on "No Draw" strength
            if prob_no_draw > 0.78:
                 print(f"   🔥 Strong 'Any Win' Probability ({prob_no_draw:.1%})")

            if edge_home > 0:
                print(f"   👉 VALUE ON HOME (Edge: +{edge_home:.2f}%)")
                stake = StatsEngine.calculate_kelly_stake(odd_home, prob_home, 0.25)
                print(f"      Kelly Stake: {stake:.2f}%")
            
            elif edge_away > 0:
                print(f"   👉 VALUE ON AWAY (Edge: +{edge_away:.2f}%)")
                stake = StatsEngine.calculate_kelly_stake(odd_away, prob_away, 0.25)
                print(f"      Kelly Stake: {stake:.2f}%")
            else:
                print("   🔸 No Value found on Home or Away Regulation Line.")

    except ValueError:
        print("❌ Error: Invalid number entered.")
    except ZeroDivisionError:
        print("❌ Error: Odds cannot be zero.")

if __name__ == "__main__":
    while True:
        calculate_hockey_value()
        if input("\nCheck another? (y/n): ").lower() != 'y': break