# NexusRisk: Bare-Metal Solana Heuristic Engine 🛡️⚡

NexusRisk is a high-frequency, bare-metal heuristic engine designed to audit Solana smart contracts and Pump.fun token launches with sub-second latency. By moving LLM inference from the cloud to local, dedicated hardware, it evaluates on-chain metadata, developer reputation, and social sentiment before malicious actors can pull liquidity.

**Performance Benchmark:** Achieved a **70% predictive accuracy rate** in identifying "Rug Pulls" vs. "Safe Entries" over a 14-day live firehose test.

## 🏗️ Enterprise Architecture

NexusRisk is not a simple script; it is a multi-threaded SaaS ecosystem built for algorithmic trading bots (like OpenClaw or custom Rust snipers) that require zero-latency risk scoring.

* **Local LLM Routing (Ollama + Intel Arc A770):** Bypasses cloud API rate limits and latency by forcing strict JSON-schema adherence via a locally hosted Llama 3.1 (8B) model.
* **Asynchronous WebSocket Firehose:** Maintains a persistent `wss://` connection to Helius RPC nodes, utilizing custom byte-unpacking to decode Solana bonding curve transactions without Rust panics.
* **SaaS Billing & Rate Limiting:** Includes a full Stripe Webhook integration (`api/server.py`) that manages tiered subscriptions, automatically provisioning API keys and enforcing Sliding Window Rate Limits (e.g., 600 req/min for Pro users).
* **Thread-Safe Concurrency:** Utilizes SQLite in `WAL` (Write-Ahead Logging) mode to safely handle simultaneous writes from the WebSockets, the LLM inferences, and user API queries without database locking.
* **Ground Truth Validator:** An autonomous background worker (`workers/validator.py`) that queries 4-hour old tokens via DexScreener to grade the AI's previous predictions, creating a self-improving feedback loop.

## 🛠️ Tech Stack
* **Backend API:** FastAPI, Uvicorn, Pydantic, Asyncio
* **Blockchain Integration:** Solana.py, Solders, Helius RPC
* **AI/Inference:** Ollama, Llama 3.1
* **Data & State:** SQLite (WAL Mode), Pandas, Matplotlib
* **Monetization & Sec:** Stripe API, custom Py-Shield middleware

## 🚀 System Boot

### Prerequisites
* Python 3.11+
* Local Ollama instance running `llama3.1:latest`
* Helius RPC WebSocket URL

### Installation
```bash
git clone [https://github.com/YOUR_GITHUB_USERNAME/nexusrisk.git](https://github.com/YOUR_GITHUB_USERNAME/nexusrisk.git)
cd nexusrisk
python -m venv .venv
source .venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

### Environment Setup

Create a ".env" file in the root directory:
```bash
SOLANA_RPC_URL=wss://[mainnet.helius-rpc.com/?api-key=YOUR_KEY](https://mainnet.helius-rpc.com/?api-key=YOUR_KEY)
OLLAMA_MODEL=llama3.1:latest
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Launching the Daemon

NexusRisk operates via a unified FastAPI lifespan context manager. Launching the server automatically boots the WebSocket firehose and the Validator loop.
```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

