import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

class PerformanceAnalyst:
    def __init__(self, db_path=None):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = db_path if db_path else os.path.join(self.base_dir, "trading_data.db")
        
    def run_full_analysis(self):
        print(f"🧐 [Analyst] Running Forensic Audit on: {self.db_path}")
        
        with sqlite3.connect(self.db_path) as conn:
            # 1. Load Data into Pandas for high-speed analysis
            df_audits = pd.read_sql_query("SELECT * FROM token_audits", conn)
            df_devs = pd.read_sql_query("SELECT * FROM developers", conn)

        if df_audits.empty:
            return print("❌ No audit data found in the database yet.")

        # 2. Key Metrics Calculation
        total_vibe_checks = len(df_audits)
        avg_risk_score = df_audits['risk_score'].mean()
        ghost_devs = len(df_devs[df_devs['total_launches'] == 1])

        print(f"\n" + "="*40)
        print(f"📊 PERFORMANCE AUDIT: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"="*40)
        print(f"🎯 Total Vibe Checks:  {total_vibe_checks}")
        print(f"🛡️  Avg Developer Risk: {avg_risk_score:.2f}")
        print(f"👻 Ghost Developers:   {ghost_devs}")
        print(f"---")

        # 3. Simple Visualization: Risk Distribution
        self.plot_risk_distribution(df_audits)

    def plot_risk_distribution(self, df):
        plt.figure(figsize=(10, 5))
        df['risk_score'].hist(bins=20, color='skyblue', edgecolor='black')
        plt.title('Developer Risk Score Distribution (Local Sifter Data)')
        plt.xlabel('Risk Score (0 = Safe, 100 = Rug)')
        plt.ylabel('Count of Launches')
        plt.grid(axis='y', alpha=0.75)
        
        # Save to your permanent data folder
        plot_path = os.path.join(self.base_dir, "data", "permanent", "risk_report.png")        plt.savefig(plot_path)
        print(f"📈 Risk distribution chart saved to: {plot_path}")
        plt.show()

if __name__ == "__main__":
    analyst = PerformanceAnalyst()
    analyst.run_full_analysis()