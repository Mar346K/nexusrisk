import sqlite3
import os
from datetime import datetime, timedelta

class TradingDatabase:
    def __init__(self):
        # Dynamically map the path to the root of the project
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "trading_data.db")
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('PRAGMA journal_mode=WAL;')
            cursor = conn.cursor()
            
            # 1. Developer Reputation Table
            cursor.execute('''CREATE TABLE IF NOT EXISTS developers (
                wallet_address TEXT PRIMARY KEY,
                trust_score INTEGER DEFAULT 50,
                total_launches INTEGER DEFAULT 0,
                rug_count INTEGER DEFAULT 0,
                last_seen DATETIME,
                notes TEXT
            )''')
            
            # 2. Token Audit History
            cursor.execute('''CREATE TABLE IF NOT EXISTS token_audits (
                mint TEXT PRIMARY KEY,
                symbol TEXT,
                dev_wallet TEXT,
                risk_score INTEGER,
                ai_vibe_check TEXT,
                timestamp DATETIME,
                FOREIGN KEY(dev_wallet) REFERENCES developers(wallet_address)
            )''')

            # 3. User Usage Table
            cursor.execute('''CREATE TABLE IF NOT EXISTS user_usage (
                api_key TEXT PRIMARY KEY,
                email TEXT,
                request_count INTEGER DEFAULT 0,
                plan_type TEXT DEFAULT 'trial_7day_3free',
                subscription_status TEXT DEFAULT 'active',
                next_billing_date DATETIME,
                last_active DATETIME
            )''')

            # 4. Global Metrics Table
            cursor.execute('''CREATE TABLE IF NOT EXISTS global_metrics (
                metric_name TEXT PRIMARY KEY,
                metric_value INTEGER DEFAULT 0
            )''')
            cursor.execute("INSERT OR IGNORE INTO global_metrics (metric_name, metric_value) VALUES ('lifetime_logs', 0)")
            cursor.execute("INSERT OR IGNORE INTO global_metrics (metric_name, metric_value) VALUES ('lifetime_mints', 0)")

            # 5. NEW: System Vitals Table (The Heartbeat)
            cursor.execute('''CREATE TABLE IF NOT EXISTS system_vitals (
                service_name TEXT PRIMARY KEY,
                status TEXT,
                last_ping DATETIME,
                queue_depth INTEGER DEFAULT 0
            )''')
            cursor.execute("INSERT OR IGNORE INTO system_vitals (service_name, status) VALUES ('firehose', 'offline')")
            cursor.execute("INSERT OR IGNORE INTO system_vitals (service_name, status) VALUES ('arc_a770', 'idle')")
            
            conn.commit()

    # --- 💓 HEARTBEAT & CONGESTION METHODS ---

    def ping_service(self, service, status="online", queue_depth=0):
        """Updates the heartbeat for Admin/User proof of life."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE system_vitals 
                SET status = ?, last_ping = ?, queue_depth = ? 
                WHERE service_name = ?
            """, (status, datetime.now().isoformat(), queue_depth, service))
            conn.commit()

    def get_vitals(self):
        """Pulls live health data for the dashboards."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_vitals")
            return {row[0]: {"status": row[1], "ping": row[2], "queue": row[3]} for row in cursor.fetchall()}

    # --- 📊 LIFETIME STATS METHODS ---

    def update_lifetime_stats(self, logs_increment, mints_increment):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE global_metrics SET metric_value = metric_value + ? WHERE metric_name = 'lifetime_logs'", (logs_increment,))
            cursor.execute("UPDATE global_metrics SET metric_value = metric_value + ? WHERE metric_name = 'lifetime_mints'", (mints_increment,))
            conn.commit()

    def get_lifetime_stats(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metric_name, metric_value FROM global_metrics")
            return {row[0]: row[1] for row in cursor.fetchall()}

    # --- 🆕 STRIPE & USAGE METHODS ---

    def add_new_user(self, api_key: str, email: str, plan: str = "beta_web_15", customer_id: str = None, sub_id: str = None):
        """Registers a new paying customer with Stripe tracking data."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO user_usage (api_key, email, plan_type, subscription_status, stripe_customer_id, stripe_subscription_id) 
                VALUES (?, ?, ?, 'active', ?, ?)
            """, (api_key, email, plan, customer_id, sub_id))
            conn.commit()

    def suspend_user_by_customer_id(self, customer_id: str):
        """Automatically called by Stripe Webhook when a payment fails."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE user_usage 
                SET subscription_status = 'suspended' 
                WHERE stripe_customer_id = ?
            """, (customer_id,))
            conn.commit()

    def regenerate_api_key(self, old_key: str, new_key: str) -> bool:
            """Instantly replaces a compromised API key with a new one."""
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE user_usage 
                    SET api_key = ? 
                    WHERE api_key = ?
                """, (new_key, old_key))
                conn.commit()
                return c.rowcount > 0

    def increment_usage(self, api_key):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_usage 
                SET request_count = request_count + 1, last_active = ?
                WHERE api_key = ?
            ''', (datetime.now().isoformat(), api_key))
            conn.commit()

    def get_user_stats(self, api_key):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_usage WHERE api_key = ?", (api_key,))
            result = cursor.fetchone()
            return dict(result) if result else None

    def get_system_wide_stats(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_usage WHERE subscription_status = 'active'")
            active_users = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM token_audits")
            total_audits = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(request_count) FROM user_usage")
            res = cursor.fetchone()[0]
            total_requests = res if res else 0
            
            return {
                "active_users": active_users, 
                "total_audits": total_audits,
                "total_requests": total_requests
            }

    # --- FORENSIC & AUDIT METHODS ---

    def log_audit(self, token_data, risk_score, vibe_check):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO token_audits 
                (mint, symbol, dev_wallet, risk_score, ai_vibe_check, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)''', 
                (token_data['mint'], token_data['symbol'], token_data.get('dev'), 
                 risk_score, vibe_check, datetime.now().isoformat()))
            conn.commit()

    def get_flagged_rugs(self, limit=10):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""SELECT * FROM token_audits WHERE risk_score > 70 ORDER BY timestamp DESC LIMIT ?""", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_verified_coins(self, limit=10):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""SELECT * FROM token_audits WHERE risk_score < 30 ORDER BY timestamp DESC LIMIT ?""", (limit,))
            return [dict(row) for row in cursor.fetchall()]
        
    def get_all_forensic_records(self, limit=50):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""SELECT mint, risk_score, ai_vibe_check, timestamp FROM token_audits ORDER BY timestamp DESC LIMIT ?""", (limit,))
            return [dict(row) for row in cursor.fetchall()]


    def log_api_query(self, mint: str, api_key: str):
        """Logs an API ping to build the Predator Detection Heatmap."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Create the heatmap table on the fly if it doesn't exist yet
            c.execute("""
                CREATE TABLE IF NOT EXISTS api_heat_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mint TEXT,
                    api_key TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("INSERT INTO api_heat_logs (mint, api_key) VALUES (?, ?)", (mint, api_key))
            conn.commit()

    def get_query_count_last_60s(self, mint: str) -> int:
        """Counts how many unique bots are targeting a token right now."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS api_heat_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mint TEXT,
                    api_key TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Count DISTINCT api keys querying this mint in the last 60 seconds
            c.execute("""
                SELECT COUNT(DISTINCT api_key) 
                FROM api_heat_logs 
                WHERE mint = ? AND timestamp >= datetime('now', '-60 seconds')
            """, (mint,))
            result = c.fetchone()[0]
            return result if result else 0