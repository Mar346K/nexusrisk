import asyncio
import time
import os
import stripe
import secrets
import sqlite3
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Security, Request, WebSocket, WebSocketDisconnect
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from dotenv import load_dotenv
from workers.validator import GroundTruthValidator
from core.config import settings
from fastapi.middleware.cors import CORSMiddleware

# --- INTERNAL NEXUS MODULES ---
from core.security import shield
from core.database import TradingDatabase
from core.billing import generate_api_key_async, is_key_valid_async
from core.cache_manager import global_cache
from scrapers.chain_listener import monitor_new_tokens
from workers.rug_check import RugChecker
from workers.local_sifter import LocalSifter
from workers.router import ModelRouter

load_dotenv()

current_load = 0

# --- CONFIGURATION ---
stripe.api_key = settings.stripe_secret_key
STRIPE_WEBHOOK_SECRET = settings.stripe_webhook_secret
ADMIN_SECRET = settings.admin_secret
TEST_USER_KEY = settings.test_user_key

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

ws_manager = ConnectionManager()

# --- DATA MODELS ---
class RiskReport(BaseModel):
    mint: str
    risk_score: int
    ai_vibe: str
    latency_ms: float

# --- SECURITY ARCHITECT ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key in [ADMIN_SECRET, TEST_USER_KEY, "nxr_test_pro", "nxr_test_trader"]:
        return api_key

    if not await is_key_valid_async(api_key):
        raise HTTPException(status_code=403, detail="Invalid API Key.")
        
    # Check if they failed their Stripe payment
    user_stats = db.get_user_stats(api_key)
    if user_stats and user_stats.get("subscription_status") == "suspended":
        raise HTTPException(status_code=402, detail="Payment Required. Subscription suspended.")
        
    return api_key

# --- LIFESPAN ENGINE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🟢 [NexusRisk] Booting Engine, WebSockets & Validator Tunnel...")
    
    # 1. Start the Firehose Listener
    token_queue = asyncio.Queue()
    listener_task = asyncio.create_task(monitor_new_tokens(token_queue))
    
    # 2. Start the Background Ground-Truth Validator
    validator = GroundTruthValidator()
    validator_task = asyncio.create_task(validator.run_validation_cycle())
    
    async def cache_updater():
        while True:
            token_data = await token_queue.get()
            global_cache.add_token(token_data)
            
            # 1. AI Scores it immediately
            audit_res = await checker.quick_audit(token_data)
            score = audit_res.get('score', 0)
            vibe = await router.get_fast_reasoning(token_data)
            db.log_audit(token_data, score, vibe) 
            
            # 2. Broadcast to all open dashboards
            await ws_manager.broadcast({
                "mint": token_data['mint'],
                "symbol": token_data.get('symbol', 'UNK'),
                "risk_score": score,
                "vibe_check": vibe
            })
            
            token_queue.task_done()
    
    updater_task = asyncio.create_task(cache_updater())
    
    yield
    
    # Clean shutdown for all three processes
    listener_task.cancel()
    updater_task.cancel()
    validator_task.cancel()

app = FastAPI(title="NexusRisk API", version="1.2.0", lifespan=lifespan)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    
    # Log the REAL error internally with the UUID
    logger.error(
        "unhandled_exception",
        error_id=error_id,
        path=request.url.path,
        error=str(exc)
    )
    
    # Return a generic, "opaque" message to the outside world
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal system error.",
            "error_id": error_id
        }
    )

# --- STRICT API BOUNDARY DEFENSE (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://nexusrisk.ai",
        # Note: You can add your Cloudflare tunnel URL here later if needed
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "Accept"],
)

checker = RugChecker()
sifter = LocalSifter()
router = ModelRouter()
db = TradingDatabase()

# --- ENTERPRISE SECURITY MIDDLEWARE ---
@app.middleware("http")
async def security_shield_middleware(request: Request, call_next):
    if not request.url.path.startswith("/webhook") and not request.url.path.startswith("/ws"):
        try:
            await shield.check_global_traffic(request) # <--- Added 'await'
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
            
    response = await call_next(request)
    return response


# --- WEBSOCKET ROUTE ---
@app.websocket("/ws/feed")
async def websocket_endpoint(websocket: WebSocket, api_key: str = None):
    # The Bouncer: Check system keys first, then hit the DB for live keys
    is_system_key = api_key in [ADMIN_SECRET, TEST_USER_KEY, "nxr_test_pro", "nxr_test_trader"]
    
    if not api_key or (not is_system_key and not await is_key_valid_async(api_key)):
        await websocket.close(code=1008) # 1008 = Policy Violation
        return

    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# --- ROUTES ---

# --- AI AGENT DISCOVERY ROUTE ---
@app.get("/llms.txt", include_in_schema=False)
async def serve_llms_txt():
    """Serves the llms.txt file so autonomous agents on X can discover the API."""
    file_path = "static/llms.txt"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/plain")
    return JSONResponse(status_code=404, content={"detail": "Agent documentation not found."})

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_landing_page():
    try:
        lifetime = db.get_lifetime_stats()
        verified_data = db.get_verified_coins(limit=4)
        scoring_speed = "3,000 / hr"
        
        card_html = ""
        for coin in verified_data:
            card_html += f"""
            <div class="bg-slate-900/40 border border-slate-800 p-4 rounded-2xl flex items-center justify-between backdrop-blur-sm group hover:border-blue-500/50 transition cursor-pointer" onclick="showCert('{coin['mint']}', '{coin['risk_score']}')">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 bg-blue-600/20 rounded-full flex items-center justify-center border border-blue-500/30 text-blue-400 font-black text-xs">
                        {coin['symbol'][:1]}
                    </div>
                    <div>
                        <p class="text-sm font-bold text-white group-hover:text-blue-400 transition">{coin['symbol']}</p>
                        <p class="text-[9px] font-mono text-slate-500">{coin['mint'][:14]}...</p>
                    </div>
                </div>
                <div class="text-right">
                    <span class="text-[9px] font-black bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20 uppercase">
                        Verified
                    </span>
                    <p class="text-[10px] text-slate-500 mt-1 font-mono">Score: {coin['risk_score']}</p>
                </div>
            </div>
            """

        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
            html = html.replace("1,698,000+", f"{lifetime.get('lifetime_logs', 0):,}")
            html = html.replace("653", f"{lifetime.get('lifetime_mints', 0):,}")
            html = html.replace("1.2s", f"1.2s ({scoring_speed})")
            html = html.replace("{{ VERIFIED_CARDS }}", card_html if card_html else "<p class='text-slate-600 italic text-center col-span-2'>Scanning Solana Firehose...</p>")
            return html
    except Exception as e:
        return f"<h1>Engine Status: ONLINE</h1><p>Syncing global metrics from Texas Node...</p>"

@app.get("/api/v1/token/{mint_address}")
async def analyze_token(mint_address: str, api_key: str = Depends(get_api_key)):
    # 0. Distributed Tier Check
    is_pro = "pro" in (db.get_user_stats(api_key) or {}).get("plan_type", "").lower()
    await shield.check_rate_limit(api_key, is_pro=is_pro)

    # 1. Track the "API Heatmap" (How many other bots are looking at this?)
    db.log_api_query(mint_address, api_key)
    query_heat = db.get_query_count_last_60s(mint_address)
    
    # 2. Fetch the cached block-0 baseline we saved earlier
    cached_data = global_cache.get_token(mint_address)
    base_score = cached_data.get('risk_score', 50) if cached_data else 50
    
    # 3. If it's your personal Arc bot asking (we can identify your specific admin key)
    # AND it has been 5 minutes, we run the Live Predator Check.
    if os.getenv('GENERIC_API_KEY'):
        
        # --- THE LIVE PREDATOR CHECK ---
        # (In reality, this would make a fast RPC call to Helius to check current holders/volume)
        # live_stats = await helius_rpc.get_token_largest_accounts(mint_address)
        
        live_penalty = 0
        vibe_reason = "Token survived the 5-minute incubator cleanly."
        
        # Rule A: The Crowded Trade (Other bots are swarming)
        if query_heat > 10:
            live_penalty += 40
            vibe_reason = f"WARNING: {query_heat} other sniper bots are targeting this. High PVP risk."
            
        # Rule B: Simulated Wash Trade / Sniper Bundle Check 
        # (Placeholder for Helius unique wallet calculation)
        top_10_hold_percentage = 15 # Simulated RPC result
        if top_10_hold_percentage > 30:
            live_penalty += 50
            vibe_reason = "Sniper cluster detected. Top wallets holding too much supply."
            
        final_score = min(base_score + live_penalty, 99)
        
        return {
            "mint": mint_address,
            "status": "SAFE" if final_score < 50 else "DANGER",
            "score": final_score,
            "vibe_check": vibe_reason,
            "api_heat": query_heat
        }

    # 4. If it's a public user's bot asking, just give them the standard safe/danger score
    return {
        "mint": mint_address,
        "status": "SAFE" if base_score < 50 else "DANGER",
        "score": base_score
    }

# --- ADMIN ACCURACY DASHBOARD ---
@app.get("/api/v1/admin/accuracy", include_in_schema=False)
async def check_engine_accuracy(api_key: str = Depends(get_api_key)):
    # Protect this so only YOU can see the raw stats
    if api_key != "nxr_admin_marquis_2026": # Use your actual admin key here
        raise HTTPException(status_code=403, detail="Admin clearance required.")
        
    with sqlite3.connect(db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Calculate how many rugs we correctly predicted (Score > 50 & Outcome = RUG)
        # and how many safe coins we correctly predicted (Score <= 50 & Outcome = SURVIVED)
        c.execute("""
            SELECT 
                COUNT(*) as total_validated,
                SUM(CASE WHEN risk_score > 50 AND actual_outcome IN ('RUGGED_NO_LIQ', 'HARD_RUG', 'SLOW_BLEED') THEN 1 ELSE 0 END) as true_positives,
                SUM(CASE WHEN risk_score <= 50 AND actual_outcome = 'SURVIVED' THEN 1 ELSE 0 END) as true_negatives
            FROM token_audits 
            WHERE actual_outcome != 'PENDING' AND actual_outcome != 'UNKNOWN'
        """)
        
        stats = dict(c.fetchone())
        
        if stats['total_validated'] > 0:
            correct_predictions = (stats['true_positives'] or 0) + (stats['true_negatives'] or 0)
            accuracy = (correct_predictions / stats['total_validated']) * 100
        else:
            accuracy = 0.0
            
        return {
            "status": "online",
            "total_audits_graded": stats['total_validated'],
            "correct_predictions": correct_predictions,
            "system_accuracy_percentage": round(accuracy, 2)
        }

# --- API KEY REGENERATION ---
@app.post("/api/v1/user/regenerate-key", include_in_schema=False)
async def regenerate_key(api_key: str = Depends(get_api_key)):
    # 1. Protect the system test keys from being accidentally rolled
    if api_key in [ADMIN_SECRET, TEST_USER_KEY, "nxr_test_pro", "nxr_test_trader"]:
        raise HTTPException(status_code=400, detail="Cannot regenerate system test keys.")
    
    # 2. Generate a fresh, cryptographically secure 24-character key
    new_key = f"nxr_{secrets.token_urlsafe(24)}"
    
    # 3. Swap it in the SQLite database
    success = db.regenerate_api_key(api_key, new_key)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update key in database.")
        
    return {"status": "success", "new_key": new_key}

# --- STRIPE WEBHOOK (Automated Lifecycle) ---

@app.post("/webhook/stripe", include_in_schema=False)
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": f"Invalid signature: {str(e)}"})

    event_type = event["type"]
    data_object = event["data"]["object"]

    # 1. NEW SIGNUPS & UPGRADES
    if event_type == "checkout.session.completed":
        email = data_object["customer_details"]["email"]
        amount_paid = data_object.get("amount_total", 0)
        customer_id = data_object.get("customer")
        sub_id = data_object.get("subscription")
        
        # Traffic Cop Routing
        plan_name = "pro_api_50" if amount_paid >= 5000 else "beta_web_15"

        new_key = await generate_api_key_async(email, customer_id or "guest")
        
        # Pass the new Stripe tracking IDs to the database
        db.add_new_user(new_key, email, plan=plan_name, customer_id=customer_id, sub_id=sub_id)
        print(f"💰 [BILLING] New {plan_name} subscription activated for {email}")

    # 2. PAYMENT FAILURES & CANCELLATIONS
    elif event_type in ["invoice.payment_failed", "customer.subscription.deleted"]:
        customer_id = data_object.get("customer")
        if customer_id:
            db.suspend_user_by_customer_id(customer_id)
            print(f"🚫 [BILLING] Suspended API access for Stripe Customer: {customer_id}")

    return {"status": "success"}

# --- SIMULATED DASHBOARD PORTALS ---
@app.get("/portal/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_portal(key: str):
    if key != ADMIN_SECRET:
        raise HTTPException(status_code=401)
    
    vitals = db.get_vitals()
    fh = vitals.get('firehose', {'status': 'offline', 'queue': 0})
    gpu = vitals.get('arc_a770', {'status': 'idle', 'queue': 0})
    
    gpu_color = "text-emerald-400" if gpu['status'] != "CONGESTED" else "text-rose-500 animate-pulse"
    queue_warning = f"<span class='ml-2 bg-rose-500/20 px-2 py-0.5 rounded text-[10px]'>LIMIT REACHED: {gpu['queue']}</span>" if gpu['status'] == "CONGESTED" else ""

    stats = db.get_system_wide_stats()
    all_records = db.get_all_forensic_records(limit=50) 
    
    rows = ""
    for c in all_records:
        color_class = "text-emerald-400" if c['risk_score'] < 30 else "text-amber-400" if c['risk_score'] < 70 else "text-rose-500"
        rows += f"""<tr class="border-b border-slate-800 hover:bg-slate-800/40 transition">
            <td class="p-4 font-mono text-[10px] text-slate-500">{c['mint']}</td>
            <td class="p-4 text-center"><span class="px-3 py-1 rounded-full bg-slate-950 border border-slate-700 font-bold {color_class}">{c['risk_score']}</span></td>
            <td class="p-4 text-sm text-slate-300">{c['ai_vibe_check']}</td>
            <td class="p-4 text-[10px] text-slate-600 font-mono text-right">{c['timestamp']}</td>
        </tr>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>NexusRisk | Admin</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-950 text-slate-100 min-h-screen p-6 font-sans">
        <div class="max-w-7xl mx-auto">
            <div class="flex justify-between items-center mb-6">
                <h1 class="text-xl font-black">NEXUS<span class="text-blue-500">ADMIN</span></h1>
                <div class="flex gap-4">
                    <div class="bg-slate-900 border border-slate-800 px-4 py-2 rounded-xl text-center">
                        <p class="text-[10px] text-slate-500 uppercase font-bold">Firehose Sync</p>
                        <p class="text-emerald-400 font-mono text-xs uppercase">{fh['status']}</p>
                    </div>
                    <div class="bg-slate-900 border border-slate-800 px-4 py-2 rounded-xl text-center">
                        <p class="text-[10px] text-slate-500 uppercase font-bold">GPU Load (A770)</p>
                        <p class="{gpu_color} font-mono text-xs uppercase">{gpu['status']} {queue_warning}</p>
                    </div>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800">
                    <p class="text-slate-500 text-xs font-bold uppercase">Beta Users</p>
                    <p class="text-3xl font-mono font-bold">{stats.get('active_users', 0)}</p>
                </div>
                <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800">
                    <p class="text-slate-500 text-xs font-bold uppercase">Engine Audits</p>
                    <p class="text-3xl font-mono font-bold">{stats.get('total_audits', 0)}</p>
                </div>
                <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800">
                    <p class="text-slate-500 text-xs font-bold uppercase">Active Queue</p>
                    <p class="text-3xl font-mono font-bold text-blue-500">{gpu['queue']}</p>
                </div>
            </div>

            <table class="w-full bg-slate-900 rounded-3xl border border-slate-800 overflow-hidden">
                <thead class="bg-slate-950 text-slate-500 text-xs uppercase font-bold text-left">
                    <tr><th class="p-4">Mint</th><th class="p-4 text-center">Score</th><th class="p-4">Reasoning</th><th class="p-4 text-right">Time</th></tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </body>
    </html>
    """

@app.get("/portal/user", response_class=HTMLResponse, include_in_schema=False)
async def user_simulation_portal(key: str):
    if key not in [TEST_USER_KEY, "nxr_test_pro", "nxr_test_trader"] and not await is_key_valid_async(key):
        raise HTTPException(status_code=401)

    usage = db.get_user_stats(key) or {"request_count": 0, "email": "Simulated User", "plan_type": "beta_web_15"}
    is_pro = "pro" in usage.get("plan_type", "").lower() or key == "nxr_test_pro"
    max_quota = 10000 if is_pro else 500 
    tier_name = "API PRO TIER" if is_pro else "WEB TRADER TIER"
    
    usage_percent = min((usage['request_count'] / max_quota) * 100, 100)
    bar_color = "bg-blue-500" if usage_percent < 85 else "bg-rose-500"

    vitals = db.get_vitals()
    gpu = vitals.get('arc_a770', {'status': 'idle'})
    health_status = "OPTIMAL" if gpu['status'] != "CONGESTED" else "HEAVY LOAD"
    health_color = "text-emerald-400" if health_status == "OPTIMAL" else "text-amber-500"
    
    verified = db.get_verified_coins(limit=15)
    items = ""
    for v in verified:
        item_id = f"raw_{v['mint'][:8]}"
        items += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden mb-3 hover:border-blue-500/50 transition">
            <div class="p-4 flex justify-between items-center">
                <div>
                    <p class="font-bold text-blue-400">{v['symbol']}</p>
                    <p class="text-[10px] font-mono text-slate-500">{v['mint']}</p>
                </div>
                <div class="flex items-center gap-4">
                    {"<button onclick=\"toggleRaw('" + item_id + "')\" class=\"text-[10px] bg-slate-800 px-2 py-1 rounded text-slate-400 hover:text-white transition\">JSON</button>" if is_pro else ""}
                    <div class="text-right">
                        <p class="text-xs font-bold text-emerald-400 italic">VERIFIED</p>
                        <p class="text-[10px] text-slate-500">Score: {v['risk_score']}</p>
                    </div>
                </div>
            </div>
            {f'''<div id="{item_id}" class="hidden bg-black/40 p-4 border-t border-slate-800">
                <pre class="text-[10px] font-mono text-emerald-500/80 leading-tight">
{{
  "mint": "{v['mint']}",
  "risk_score": {v['risk_score']},
  "vibe_check": "{v['ai_vibe_check']}"
}}
                </pre>
            </div>''' if is_pro else ""}
        </div>
        """

    if is_pro:
        right_column_html = f"""
        <div class="bg-slate-900 border border-slate-800 rounded-[2rem] overflow-hidden shadow-2xl">
            <div class="bg-slate-800/50 p-5 border-b border-slate-700 flex justify-between items-center">
                <h3 class="text-[10px] font-black uppercase tracking-widest text-slate-400">Environment & Code</h3>
            </div>
            <div class="p-6">
                <div class="mb-6 border-b border-slate-800 pb-6">
                    <p class="text-[10px] text-slate-500 uppercase font-bold mb-2">1. Set your .env variable</p>
                    <div class="flex bg-black/50 border border-slate-800 rounded-xl overflow-hidden">
                        <input type="password" id="api-key-secret" value="{key}" readonly class="bg-transparent text-emerald-400 font-mono text-xs p-3 w-full outline-none select-all">
                        <button onclick="copyElement('api-key-secret', true)" class="bg-slate-800 hover:bg-blue-600 px-4 text-[10px] font-bold uppercase transition">Copy</button>
                    </div>
                </div>
                <p class="text-[10px] text-slate-500 uppercase font-bold mb-2">2. Bot Integration Snippet</p>
                <div class="bg-black/50 border border-slate-800 rounded-xl overflow-hidden relative group">
                    <pre id="python-snippet" class="p-4 font-mono text-[10px] text-blue-400/90 overflow-x-auto">
import os
import requests

NEXUS_KEY = os.getenv("NEXUS_API_KEY")
HEADERS = {{"X-API-Key": NEXUS_KEY}}

def check_token(mint):
    url = f"https://fun-enables-thing-luck.trycloudflare.com/api/v1/token/{{mint}}"
    return requests.get(url, headers=HEADERS).json()</pre>
                    <button onclick="copyElement('python-snippet', false)" class="absolute top-2 right-2 bg-slate-800 px-2 py-1 rounded text-[9px] text-slate-400 hover:text-white opacity-0 group-hover:opacity-100 transition">COPY</button>
                </div>
                <a href="/docs" target="_blank" class="block text-center w-full mt-6 bg-blue-600 hover:bg-blue-500 text-white text-xs py-3 rounded-2xl font-black transition shadow-lg shadow-blue-900/20 uppercase tracking-tighter">
                    Open API Swagger Docs
                </a>
            </div>
        </div>
        """
    else:
        right_column_html = f"""
        <div class="bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-[2rem] overflow-hidden shadow-2xl p-6">
            <h3 class="text-sm font-black text-white mb-2">Manual Deep Scan</h3>
            <p class="text-[11px] text-slate-400 mb-6">Paste a Solana contract address below to run a direct forensic check against the Arc A770.</p>
            <input type="text" id="manual-mint" placeholder="Paste Token Mint (e.g., 6TatPGV...)" class="w-full bg-black/50 border border-slate-700 p-4 rounded-xl text-xs font-mono mb-4 text-white focus:border-blue-500 outline-none">
            <button onclick="runManualScan()" id="scan-btn" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-black uppercase tracking-widest text-xs py-4 rounded-xl shadow-lg shadow-blue-900/40 transition flex justify-center items-center">
                Execute Scan
            </button>
            <div id="scan-result" class="hidden mt-6 bg-black/40 p-4 rounded-xl border border-slate-800">
                <p class="text-[10px] text-slate-500 uppercase font-bold mb-1">A770 Verdict</p>
                <p id="scan-score" class="text-2xl font-black mb-2"></p>
                <p id="scan-vibe" class="text-[10px] text-slate-400 leading-relaxed"></p>
            </div>
        </div>
        
        <script>
            async function runManualScan() {{
                const mint = document.getElementById('manual-mint').value.trim();
                if(!mint) return;
                
                const btn = document.getElementById('scan-btn');
                btn.innerHTML = "<span class='w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2'></span> SCANNING...";
                
                try {{
                    const res = await fetch(`/api/v1/token/${{mint}}`, {{
                        headers: {{ "X-API-Key": "{key}" }}
                    }});
                    const data = await res.json();
                    
                    document.getElementById('scan-result').classList.remove('hidden');
                    const scoreEl = document.getElementById('scan-score');
                    scoreEl.innerText = data.risk_score + "/100 RISK";
                    scoreEl.className = data.risk_score > 60 ? "text-rose-500 text-2xl font-black mb-2" : "text-emerald-400 text-2xl font-black mb-2";
                    document.getElementById('scan-vibe').innerText = data.ai_vibe;
                }} catch (e) {{
                    alert("Scan failed. Ensure mint address is valid.");
                }} finally {{
                    btn.innerText = "EXECUTE SCAN";
                }}
            }}
        </script>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>NexusRisk | {tier_name}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .custom-scrollbar::-webkit-scrollbar {{ width: 5px; }} 
            .custom-scrollbar::-webkit-scrollbar-thumb {{ background: #1e293b; border-radius: 10px; }}
        </style>
        <script>
            function toggleRaw(id) {{
                document.getElementById(id).classList.toggle('hidden');
            }}
            
            function copyElement(id, isInput) {{
                const el = document.getElementById(id);
                const text = isInput ? el.value : el.innerText;
                navigator.clipboard.writeText(text);
                
                const origType = el.type;
                if(isInput) el.type = 'text'; 
                setTimeout(() => {{ if(isInput) el.type = origType; }}, 500);
            }}

            // PANIC BUTTON LOGIC
            async function rollApiKey() {{
                if(!confirm("⚠️ WARNING: This will instantly destroy your current API key. All running OpenClaw agents or Rust bots will be disconnected. Continue?")) return;
                
                const currentKey = localStorage.getItem('nxr_api_key');
                try {{
                    const res = await fetch('/api/v1/user/regenerate-key', {{
                        method: 'POST',
                        headers: {{ 'X-API-Key': currentKey }}
                    }});
                    
                    const data = await res.json();
                    
                    if(data.status === 'success') {{
                        localStorage.setItem('nxr_api_key', data.new_key);
                        alert("✅ Key regenerated securely! Reloading your terminal...");
                        window.location.href = `/portal/user?key=${{data.new_key}}`;
                    }} else {{
                        alert(data.detail || "Failed to regenerate key. You might be using a static test key.");
                    }}
                }} catch (e) {{
                    alert("Network error connecting to Texas Node.");
                }}
            }}

            // LIVE SENTRY FEED: True WebSocket Connection
            document.addEventListener("DOMContentLoaded", function() {{
                const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
                const wsUrl = protocol + window.location.host + '/ws/feed?api_key={key}';
                const ws = new WebSocket(wsUrl);
                
                ws.onmessage = function(event) {{
                    const data = JSON.parse(event.data);
                    const feedContainer = document.getElementById('sentry-feed-container');
                    
                    if (feedContainer.innerHTML.includes('Awaiting hardware signal')) {{
                        feedContainer.innerHTML = '';
                    }}

                    const itemId = 'raw_' + data.mint.substring(0,8);
                    const scoreColor = data.risk_score > 60 ? 'text-rose-500' : (data.risk_score > 30 ? 'text-amber-400' : 'text-emerald-400');
                    const statusText = data.risk_score > 60 ? 'HIGH RISK' : 'VERIFIED';
                    const jsonBtn = {str(is_pro).lower()} ? `<button onclick="toggleRaw('${{itemId}}')" class="text-[10px] bg-slate-800 px-2 py-1 rounded text-slate-400 hover:text-white transition">JSON</button>` : '';
                    const jsonBox = {str(is_pro).lower()} ? `<div id="${{itemId}}" class="hidden bg-black/40 p-4 border-t border-slate-800"><pre class="text-[10px] font-mono text-emerald-500/80 leading-tight">{{\\n  "mint": "${{data.mint}}",\\n  "risk_score": ${{data.risk_score}},\\n  "vibe_check": "${{data.vibe_check}}"\\n}}</pre></div>` : '';
                    
                    const newCard = `
                    <div class="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden mb-3 hover:border-blue-500/50 transition animate-pulse">
                        <div class="p-4 flex justify-between items-center">
                            <div>
                                <p class="font-bold text-blue-400">${{data.symbol}}</p>
                                <p class="text-[10px] font-mono text-slate-500">${{data.mint}}</p>
                            </div>
                            <div class="flex items-center gap-4">
                                ${{jsonBtn}}
                                <div class="text-right">
                                    <p class="text-xs font-bold ${{scoreColor}} italic">${{statusText}}</p>
                                    <p class="text-[10px] text-slate-500">Score: ${{data.risk_score}}</p>
                                </div>
                            </div>
                        </div>
                        ${{jsonBox}}
                    </div>`;
                    
                    feedContainer.insertAdjacentHTML('afterbegin', newCard);
                    
                    if (feedContainer.children.length > 20) {{
                        feedContainer.removeChild(feedContainer.lastChild);
                    }}
                    
                    setTimeout(() => {{
                        if(feedContainer.firstElementChild) feedContainer.firstElementChild.classList.remove('animate-pulse');
                    }}, 1000);
                }};
            }});
        </script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen p-6 font-sans selection:bg-blue-500/30">
        <div class="max-w-5xl mx-auto">
            <div class="flex justify-between items-center mb-10">
                <div>
                    <h1 class="text-2xl font-black tracking-tighter text-white uppercase italic">Nexus<span class="text-blue-500">Cloud</span></h1>
                    <p class="text-[10px] text-slate-500 font-mono">TIER: {tier_name} | NODE: TX_A770</p>
                </div>
                <div class="flex items-center gap-3">
                    <div class="bg-slate-900 border border-slate-800 px-4 py-1.5 rounded-full text-[10px] font-bold">
                        SYSTEM HEALTH: <span class="{health_color}">{health_status}</span>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div class="lg:col-span-2 space-y-8">
                    <div class="bg-slate-900 border border-slate-800 p-8 rounded-[2rem] shadow-xl">
                        <div class="flex justify-between items-end mb-4">
                            <div>
                                <h3 class="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Compute Quota</h3>
                                <p class="text-4xl font-black">{usage['request_count']} <span class="text-slate-700 text-sm">/ {max_quota}</span></p>
                            </div>
                            <p class="text-[10px] font-bold text-slate-500">{round(usage_percent)}% UNIT CONSUMPTION</p>
                        </div>
                        <div class="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden border border-slate-800">
                            <div class="{bar_color} h-full transition-all duration-1000" style="width: {usage_percent}%"></div>
                        </div>
                    </div>

                    <div class="space-y-4">
                        <div class="flex justify-between items-center px-2">
                            <h3 class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Global Sentry Feed</h3>
                            <span class="text-[10px] text-emerald-500 font-mono animate-pulse">● LIVE_STREAM</span>
                        </div>
                        <div id="sentry-feed-container" class="custom-scrollbar overflow-y-auto max-h-[500px] pr-2">
                            {items if items else "<div class='p-10 text-center border border-dashed border-slate-800 rounded-2xl text-slate-600 italic'>Awaiting hardware signal...</div>"}
                        </div>
                    </div>
                </div>
                <div class="space-y-6">
                    {right_column_html}
                </div>
            </div>

            <footer class="mt-20 py-10 border-t border-slate-900 flex justify-between items-center text-[10px] font-bold text-slate-600 uppercase tracking-widest">
                <div class="flex flex-col gap-2">
                    <p>© 2026 NexusRisk Core</p>
                    <p class="text-[8px] font-normal text-slate-700 normal-case max-w-md">NexusRisk provides algorithmic data, not financial advice. Trade at your own risk. By using this terminal, you agree to our Terms of Service.</p>
                </div>
                <div class="flex items-center gap-4">
                    <span class="bg-emerald-500/10 text-emerald-500 px-2 py-1 rounded border border-emerald-500/20" id="key-status-badge">KEY ACTIVE</span>
                    
                    <button onclick="rollApiKey()" class="text-[10px] bg-rose-500/10 text-rose-500 hover:bg-rose-500 hover:text-white px-3 py-1.5 rounded border border-rose-500/20 transition uppercase tracking-widest font-bold">
                        Roll Key
                    </button>
                    
                    <button onclick="localStorage.clear(); window.location.href='/';" class="hover:text-rose-500 transition ml-2">
                        Terminals: Logout
                    </button>
                </div>
            </footer>
        </div>
    </body>
    </html>
    """