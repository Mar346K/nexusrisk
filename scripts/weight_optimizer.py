import sqlite3

# --- CONFIGURATION ---
DB_PATH = "data/training_data.sqlite"

def analyze_feature(cursor, feature_column, feature_name):
    """Calculates the exact rug probability if a token is missing a specific feature."""
    # Count what happens when the feature is MISSING (0)
    cursor.execute(f"SELECT is_safe, COUNT(*) FROM token_anatomy WHERE {feature_column} = 0 GROUP BY is_safe")
    results = dict(cursor.fetchall())
    
    safe_count = results.get(1, 0)
    rug_count = results.get(0, 0)
    total_missing = safe_count + rug_count
    
    if total_missing == 0:
        return 0
        
    rug_probability = (rug_count / total_missing) * 100
    
    print(f"🔍 [Feature: Missing {feature_name}]")
    print(f"   Tokens missing this: {total_missing}")
    print(f"   Resulting Rugs:      {rug_count}")
    print(f"   Rug Probability:     {rug_probability:.1f}%")
    
    # Calculate suggested penalty point (0 to 100 scale)
    # If 90% of coins without a website rug, the penalty should be high (e.g., +45 points)
    suggested_penalty = int((rug_probability / 100) * 50) 
    print(f"   👉 Suggested Penalty: +{suggested_penalty} Risk Points\n")

def run_optimizer():
    print("🧠 Booting NexusRisk Heuristic Optimizer...\n")
    
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM token_anatomy")
        total = c.fetchone()[0]
        
        if total == 0:
            print("❌ Database is empty. Run the miner first.")
            return
            
        print(f"📊 Analyzing {total} labeled tokens from the training database...\n")
        
        # Analyze our three main metadata features
        analyze_feature(c, "has_website", "Website")
        analyze_feature(c, "has_twitter", "Twitter/X")
        analyze_feature(c, "has_telegram", "Telegram")
        
        print("💡 --- OPTIMIZATION COMPLETE ---")
        print("Use these suggested penalties to update the math in your `rug_check.py` _local_heuristic_scan function.")

if __name__ == "__main__":
    run_optimizer()