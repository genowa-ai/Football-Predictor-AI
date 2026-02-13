import sys

class BettingTools:
    """
    Mathematical tools for betting analysis without Poisson simulation.
    """
    
    @staticmethod
    def calculate_kelly_stake(odds, prob_win, bankroll_fraction=0.05):
        """
        Calculates Kelly Criterion.
        """
        if odds <= 1 or prob_win <= 0: return 0.0
        
        b = odds - 1
        q = 1 - prob_win
        f = (b * prob_win - q) / b
        
        # Max cap at 5% or user defined fraction for safety
        return max(0, f * bankroll_fraction * 100)

    @staticmethod
    def get_synthetic_double_chance_odd(odd_home, odd_away):
        """
        Calculates what the 'No Draw' (12) odds *should* be based on 
        the Home and Away odds provided.
        Formula: 1 / ((1/Home) + (1/Away))
        """
        try:
            prob_h_implied = 1 / odd_home
            prob_a_implied = 1 / odd_away
            return 1 / (prob_h_implied + prob_a_implied)
        except ZeroDivisionError:
            return 0.0

    @staticmethod
    def normalize_percentages(h, d, a):
        """
        If the user inputs percentages that don't sum to exactly 100% 
        (e.g. 45, 30, 20 = 95%), this scales them to equal 1.0 (100%).
        """
        total = h + d + a
        if total == 0: return 0, 0, 0
        return h/total, d/total, a/total

def run_probability_analysis():
    print("\n" + "="*60)
    print("🛡️  ANTI-DRAW PREDICTOR: PROBABILITY EDITION  🛡️")
    print("="*60)

    try:
        # ------------------------------------------------
        # 1. ODDS INPUT
        # ------------------------------------------------
        print("\n📝 SECTION 1: BOOKMAKER ODDS (1X2)")
        try:
            o_h = float(input("   🏠 Home Odd: "))
            o_d = float(input("   🤝 Draw Odd: "))
            o_a = float(input("   ✈️ Away Odd: "))
        except ValueError:
            print("   ❌ Error: Please enter valid numbers.")
            return

        # Calculate Bookie Vig/Overround
        bookie_vig = (1/o_h + 1/o_d + 1/o_a) - 1
        print(f"   ℹ️  Bookie Margin: {bookie_vig:.2%}")

        # ------------------------------------------------
        # 2. PROBABILITY INPUT
        # ------------------------------------------------
        print("\n📝 SECTION 2: WIN PROBABILITIES (External Data)")
        print("   (Enter as numbers, e.g., 50 for 50%)")
        try:
            raw_p_h = float(input("   📊 Home Win %: "))
            raw_p_d = float(input("   📊 Draw %:     "))
            raw_p_a = float(input("   📊 Away Win %: "))
        except ValueError:
            print("   ❌ Error: Probabilities must be numbers.")
            return

        # Normalize inputs (Handle user entering 50, 30, 20 or 0.5, 0.3, 0.2)
        # If user enters integers > 1, assume they are percentages.
        if raw_p_h > 1 or raw_p_d > 1 or raw_p_a > 1:
            raw_p_h /= 100
            raw_p_d /= 100
            raw_p_a /= 100

        # Ensure they sum to 100% mathematically
        prob_home, prob_draw, prob_away = BettingTools.normalize_percentages(raw_p_h, raw_p_d, raw_p_a)
        
        # Calculate "No Draw" Probability (Home + Away)
        prob_no_draw = prob_home + prob_away

        # ------------------------------------------------
        # 3. ANALYSIS & EDGE CALCULATION
        # ------------------------------------------------
        
        # Calculate the implied '12' odds from the bookmaker
        # This assumes you are betting on '12' or 'Lay Draw'
        bookie_12_odd = BettingTools.get_synthetic_double_chance_odd(o_h, o_a)

        # Helper to calc edge
        def calc_edge(my_prob, bookie_odd):
            return (my_prob * bookie_odd - 1) * 100

        edge_h = calc_edge(prob_home, o_h)
        edge_d = calc_edge(prob_draw, o_d)
        edge_a = calc_edge(prob_away, o_a)
        edge_12 = calc_edge(prob_no_draw, bookie_12_odd)

        # ------------------------------------------------
        # 4. REPORT GENERATION
        # ------------------------------------------------
        print("\n" + "-"*60)
        print(f"📊 VALUE REPORT (Normalized Inputs)")
        print("-" * 60)
        
        print(f"{'OUTCOME':<15} | {'YOUR PROB':<12} | {'BOOKIE PROB':<12} | {'VALUE EDGE'}")
        print("-" * 55)

        # Home
        implied_h = 1/o_h
        print(f"{'Home Win':<15} | {prob_home:<12.1%} | {implied_h:<12.1%} | {edge_h:+.2f}%")
        
        # Draw
        implied_d = 1/o_d
        print(f"{'Draw':<15} | {prob_draw:<12.1%} | {implied_d:<12.1%} | {edge_d:+.2f}%")
        
        # Away
        implied_a = 1/o_a
        print(f"{'Away Win':<15} | {prob_away:<12.1%} | {implied_a:<12.1%} | {edge_a:+.2f}%")

        print("-" * 55)

        # ------------------------------------------------
        # 5. THE ANTI-DRAW VERDICT
        # ------------------------------------------------
        print("\n🛡️ --- ANTI-DRAW (12) VERDICT ---")
        
        print(f"   Your 'No Draw' Prob:    {prob_no_draw:.1%}")
        print(f"   Bookie '12' Odds:       {bookie_12_odd:.2f}")
        print(f"   Value Edge on '12':     {edge_12:+.2f}%")

        # Risk Analysis
        risk_flags = []
        if prob_draw > 0.25: risk_flags.append("High Draw Probability (>30%)")
        if abs(prob_home - prob_away) < 0.05: risk_flags.append("Teams are extremely evenly matched")
        if bookie_vig > 0.08: risk_flags.append("Bad Bookmaker Odds (High Vig)")

        if risk_flags:
            print(f"\n   ⚠️ CAUTION: {', '.join(risk_flags)}")

        # Final Recommendation Logic
        print("\n   🏆 RECOMMENDATION:")
        
        if prob_draw >= 0.26:
            print("   ⛔ SKIP BET. Draw probability is too high.")
        elif edge_12 > 1.5:
            print("   ✅ BET DOUBLE CHANCE (12).")
            print("      Explanation: Your data suggests a winner is more likely than odds imply.")
            stake = BettingTools.calculate_kelly_stake(bookie_12_odd, prob_no_draw, 0.25)
            print(f"      Suggested Stake: {stake:.2f}%")
        elif edge_h > 4.0:
            print("   ✅ VALUE ON HOME WIN (High Confidence).")
            print("      Consider taking Home Draw No Bet (DNB) if available.")
            stake = BettingTools.calculate_kelly_stake(o_h, prob_home, 0.25)
            print(f"      Suggested Stake: {stake:.2f}%")
        elif edge_a > 4.0:
            print("   ✅ VALUE ON AWAY WIN (High Confidence).")
            print("      Consider taking Away Draw No Bet (DNB) if available.")
            stake = BettingTools.calculate_kelly_stake(o_a, prob_away, 0.25)
            print(f"      Suggested Stake: {stake:.2f}%")
        else:
            print("   ⏸️ NO BET. No statistical value found vs Bookie odds.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    while True:
        run_probability_analysis()
        if input("\n🔄 Check another match? (y/n): ").lower() != 'y': break