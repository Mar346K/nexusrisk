# core/cache_manager.py
from typing import Dict, Any

class TokenCache:
    def __init__(self, max_size=5000):
        # We hold up to 5,000 recent token launches entirely in your 128GB RAM.
        # This takes practically zero memory for you, but provides O(1) instant lookup speeds.
        self.cache: Dict[str, Any] = {}
        self.max_size = max_size
        self.order = [] # Tracks insertion order for fast FIFO eviction

    def add_token(self, token_data: dict):
        """Called by the firehose scraper the millisecond a token is launched."""
        mint = token_data.get('mint')
        if not mint:
            return

        # If it's a new token, add it to RAM
        if mint not in self.cache:
            # If RAM cache is 'full', evict the oldest token
            if len(self.cache) >= self.max_size:
                oldest_mint = self.order.pop(0)
                del self.cache[oldest_mint]
            
            self.order.append(mint)
        
        # Store or update the data
        self.cache[mint] = token_data
        print(f"💾 [RAM Cache] Stored {token_data.get('symbol')} ({mint[:8]}...)")

    def get_token(self, mint: str) -> dict:
        """Called by the FastAPI server when a customer requests a Vibe Check."""
        return self.cache.get(mint)

# Instantiate a single global cache to be shared across the entire API architecture
global_cache = TokenCache()