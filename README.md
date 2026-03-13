### NexusRisk: Distributed Solana Heuristic & Forensic Engine 🛡️⚡

<<<<<<< HEAD
=======
[![NexusRisk CI/CD Pipeline](https://github.com/Mar346K/nexusrisk/actions/workflows/ci.yml/badge.svg)](https://github.com/Mar346K/nexusrisk/actions/workflows/ci.yml)

NexusRisk is a high-frequency, bare-metal heuristic engine designed to audit Solana smart contracts and Pump.fun token launches with sub-second latency. By moving LLM inference from the cloud to local, dedicated hardware, it evaluates on-chain metadata, developer reputation, and social sentiment before malicious actors can pull liquidity.
>>>>>>> 5bb04ab770e907369c386daf70ead49cde20743a


NexusRisk is a high-frequency, distributed heuristic engine designed to audit Solana smart contracts and Pump.fun token launches with sub-second latency. By leveraging Intel Arc A770 hardware and a distributed state-sync architecture, it evaluates on-chain risk before malicious actors can pull liquidity.

# Performance Benchmark: Achieved a 70%+ predictive accuracy rate in identifying "Rug Pulls" over a 14-day live firehose test.

### 🏗️ v1.3.0 Enterprise Architecture
* **NexusRisk has been hardened for high-concurrency production environments, moving from local volatile memory to a decoupled, non-blocking infrastructure.** 

* **Distributed State Store (Docker + Redis): State-sync architecture using Redis for atomic, thread-safe rate limiting and global DDoS protection. Ensures security state (bans/quotas) persists across container restarts.**

* **Native Async I/O (Non-Blocking): Migrated from synchronous requests and sqlite3 to aiohttp and aiosqlite. This prevents event-loop starvation and optimizes the Intel Arc A770’s inference pipeline during peak Solana traffic.**

* **Zero-Trust Security Layer: * SHA-256 Key Hashing: API keys are never stored in plain text; authenticated via cryptographically secure hashes.**

* **WebSocket Gatekeeping: Strict policy-based handshakes (Code 1008) for live data feeds.**

* **CORS & Opaque Errors: Hardened API boundaries with global exception masking to prevent internal footprint leakage.**

* **Local LLM Routing (Ollama + A770): Bypasses cloud latency via a locally hosted Llama 3.1 (8B) model, enforcing strict JSON-schema adherence for sub-second forensic verdicts.**

* **Ground Truth Validator: An autonomous background worker (workers/validator.py) that audits 4-hour-old tokens to grade AI predictions, maintaining a 24/7 accuracy feedback loop.**

#### 🛠️ Tech Stack
* **Backend: FastAPI, Uvicorn, Pydantic (Settings v2), Structlog**

* **Infrastructure: Docker, Redis (Distributed State), SQLite (WAL Mode)**

* **AI/Inference: Ollama (Llama 3.1), Intel Arc A770 Hardware**

* **Networking: Aiohttp (Async HTTP), WebSockets, Helius RPC**

### 🚀 System Boot
Prerequisites
* Docker Desktop & Python 3.12+

* Intel Arc A770 (Recommended for 1.2s inference)

* Ollama instance running llama3.1:latest

### Installation
<<<<<<< HEAD
```Bash
git clone https://github.com/MARQUIS_SANCHEZ/nexusrisk.git
=======
```bash
git clone [https://github.com/Mar346K/nexusrisk.git](https://github.com/Mar346K/nexusrisk.git)
>>>>>>> 5bb04ab770e907369c386daf70ead49cde20743a
cd nexusrisk
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```
### Distributed Setup
NexusRisk now utilizes Docker for infrastructure. Launch the state store first:

<<<<<<< HEAD
```Bash
docker compose up -d redis
```
## Launching the Engine
```Bash
.\venv\Scripts\python.exe -m uvicorn api.server:app --reload
```

#### 🛡️ Security Policy
NexusRisk follows Zero-Trust principles. All critical failures return an error_id UUID for internal log correlation via Structlog, keeping the external attack surface opaque.
=======
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
>>>>>>> 5bb04ab770e907369c386daf70ead49cde20743a
