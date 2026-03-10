import time
from workers.performance_analyst import PerformanceAnalyst

def start_3_hour_watch():
    analyst = PerformanceAnalyst()
    reports_completed = 0
    
    print("🧐 [NexusRisk] 3-Hour Performance Audit Started.")
    
    while reports_completed < 3:
        print(f"\n🔔 [Report {reports_completed + 1}/3] Generating hourly stats...")
        analyst.run_full_analysis() # Prints stats and saves risk_report.png
        
        reports_completed += 1
        if reports_completed < 3:
            print("⏳ Waiting 1 hour for next data sweep...")
            time.sleep(3600) # Wait 1 hour

if __name__ == "__main__":
    start_3_hour_watch()