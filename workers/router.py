import os
import asyncio
import json
import ollama
from dotenv import load_dotenv

# Hardcoded to your secure C: drive location
load_dotenv()

class ModelRouter:
    def __init__(self):
        self.local_model = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
        
        # THE PRODUCT MANAGER: Define a strict, unchangeable schema
        self.output_schema = {
            "type": "object",
            "properties": {
                "risk_score": {"type": "integer"},
                "vibe_check": {"type": "string"},
                "is_testnet": {"type": "boolean"}
            },
            "required": ["risk_score", "vibe_check", "is_testnet"]
        }

    async def get_fast_reasoning(self, token_data):
        prompt = (
            f"Analyze this Solana token. Symbol: {token_data.get('symbol')}, "
            f"Mint: {token_data.get('mint')}. "
            "Output a JSON object containing a 0-100 risk_score, a concise 2-sentence vibe_check, and a boolean is_testnet flag."
        )
        
        try:
            # We switch from generate() to chat() which natively supports strict schema enforcement
            response = await asyncio.to_thread(
                ollama.chat,
                model=self.local_model,
                messages=[{'role': 'user', 'content': prompt}],
                format=self.output_schema, 
                keep_alive="10m",
                options={
                    "num_gpu": 99, 
                    "temperature": 0.0 # Force deterministic, non-creative data extraction
                }
            )
            # Returns a perfectly formatted stringified JSON
            return response['message']['content']
        except Exception as e:
            # Failsafe return so the API never crashes
            return json.dumps({"risk_score": 99, "vibe_check": f"Inference Error: {e}", "is_testnet": False})

if __name__ == "__main__":
    async def test():
        print(f"🔄 Booting ModelRouter in Strict JSON Mode...")
        router = ModelRouter()
        dummy_token = {"symbol": "NEXUS-TEST", "mint": "MockMintAddress123456789"}
        
        start_time = asyncio.get_event_loop().time()
        result = await router.get_fast_reasoning(dummy_token)
        end_time = asyncio.get_event_loop().time()
        
        print(f"\n🧠 [Strict JSON Payload] (Took {end_time - start_time:.2f}s):\n{result}")

    asyncio.run(test())