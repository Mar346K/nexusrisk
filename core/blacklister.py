import sqlite3
import os

class Blacklister:
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, "trading_data.db")
        else:
            self.db_path = db_path

    def get_blacklist(self):
        """Returns a list of dev wallets with a trust_score below 30."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT wallet_address FROM developers WHERE trust_score < 30")
            return [row[0] for row in cursor.fetchall()]

    def ban_dev(self, wallet_address, reason="Multiple Losses"):
        """Manually blacklist a developer."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE developers SET trust_score = 0, notes = ? WHERE wallet_address = ?", 
                           (reason, wallet_address))
            conn.commit()
            print(f"🚫 [Blacklister] Wallet {wallet_address[:6]} permanently banned.")

if __name__ == "__main__":
    bl = Blacklister()
    print(f"Current Blacklisted Wallets: {len(bl.get_blacklist())}")