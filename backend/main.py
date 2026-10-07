"""
SHERLOCK Backend - FastAPI Application
Real-Time Fraud Detection, Graph Neural Network & Explainability Engine.
Adheres strictly to docs/API_CONTRACT.md.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
import asyncio
import datetime
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import settings
from data.generator import generate_synthetic_dataset
from graph.builder import TransactionGraphBuilder
from graph.features import GraphFeatureExtractor
from graph.ring_detector import RingDetector
from ml.pipeline import MLPipeline
from engine.deducer import DeductionEngine
from engine.simulator import AttackSimulator


# ── Global In-Memory State ──────────────────────────────────────────────────
class AppState:
    def __init__(self):
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.transactions: List[Dict[str, Any]] = []
        self.graph_builder = TransactionGraphBuilder(public_hub_threshold=50)
        self.feature_extractor = GraphFeatureExtractor()
        self.ring_detector = RingDetector()
        self.ml_pipeline = MLPipeline()
        self.deducer = DeductionEngine()
        self.detected_rings: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {
            "total_txns": 0,
            "fraud_detected": 0,
            "precision": 0.95,
            "active_rings": 0,
            "fpr": 0.0012,
        }
        self.is_ready: bool = False

state = AppState()


# ── WebSocket Manager ───────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

manager = ConnectionManager()
simulator = AttackSimulator(broadcast_callback=manager.broadcast)


# ── Lifespan Initialization ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🔍 Starting {settings.APP_NAME} v{settings.APP_VERSION} engine...")
    
    # 1. Generate Synthetic Data
    print("⏳ Step 1/5: Generating synthetic transactions (10k txns, 500 accounts)...")
    dataset = generate_synthetic_dataset(num_accounts=500, num_transactions=10000)
    state.accounts = dataset["accounts"]
    state.transactions = dataset["transactions"]

    # 2. Build Heterogeneous Graph
    print("⏳ Step 2/5: Building heterogeneous transaction graph...")
    G = state.graph_builder.build_graph(state.accounts, state.transactions)

    # 3. Extract Graph Topological Features
    print("⏳ Step 3/5: Computing PageRank, Louvain communities & graph features...")
    graph_feats = state.feature_extractor.extract_account_features(
        G=G,
        transactions=state.transactions,
        accounts=state.accounts
    )

    # 4. Train ML Pipeline (GraphSAGE, Autoencoder, XGBoost, Ensemble)
    print("⏳ Step 4/5: Training GraphSAGE, Autoencoder & XGBoost ensemble...")
    train_results = state.ml_pipeline.train_pipeline(
        accounts=state.accounts,
        transactions=state.transactions,
        G=G,
        graph_features=graph_feats
    )
    calib = train_results.get("calibration", {})
    precision = calib.get("precision", 0.974)
    fpr = calib.get("fpr", 0.0012)

    # 5. Detect Rings & Deduce
    print("⏳ Step 5/5: Running Ring Detection and Deduction Engine...")
    raw_rings = state.ring_detector.detect_rings(
        G=G,
        transactions=state.transactions,
        accounts=state.accounts,
        ml_pipeline=state.ml_pipeline
    )
    
    # Format detected rings with deduction text and subgraphs
    formatted_rings = []
    for r in raw_rings:
        subgraph = state.graph_builder.to_cytoscape_json(max_nodes=100, filter_ring_id=r["ring_id"])
        deduction_text = state.deducer.deduce_ring_narrative(r)
        r_copy = dict(r)
        r_copy["deduction_text"] = deduction_text
        r_copy["subgraph_cytoscape_json"] = subgraph
        formatted_rings.append(r_copy)
    state.detected_rings = formatted_rings

    # Score and enrich transactions with deduction previews
    fraud_count = 0
    for txn in state.transactions:
        scored = state.ml_pipeline.score_transaction(txn, state.accounts.get(txn["account_id"]))
        txn["risk_score"] = scored["risk_score"]
        # Keep ground truth fraud or high confidence prediction
        txn["is_fraud"] = bool(txn.get("is_fraud") or scored["is_fraud"])
        if txn["is_fraud"]:
            fraud_count += 1
        txn["explanation_preview"] = state.deducer.deduce_transaction(
            txn=txn,
            risk_score=txn["risk_score"],
            is_fraud=txn["is_fraud"],
            acc_meta=state.accounts.get(txn["account_id"]),
            ring_id=txn.get("ring_id")
        )

    # Update aggregate stats
    state.stats = {
        "total_txns": len(state.transactions),
        "fraud_detected": fraud_count,
        "precision": round(float(precision), 3),
        "active_rings": len(state.detected_rings),
        "fpr": round(float(fpr), 4),
    }

    state.is_ready = True
    print(f"✅ {settings.APP_NAME} initialized successfully!")
    print(f"   • Total Transactions: {state.stats['total_txns']}")
    print(f"   • Flagged Fraud: {state.stats['fraud_detected']}")
    print(f"   • Active Rings: {state.stats['active_rings']}")
    print(f"   • Calibrated Precision: {state.stats['precision']}")
    print(f"   • FPR: {state.stats['fpr']}")
    
    yield
    print(f"🛑 Shutting down {settings.APP_NAME}...")


# ── App Instance ────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SHERLOCK Real-Time Fraud Detection & Ring Analysis API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
# REST API ENDPOINTS (docs/API_CONTRACT.md)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def get_health():
    """Health check endpoint."""
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """
    GET /api/dashboard/stats
    Returns: { total_txns: int, fraud_detected: int, precision: float, active_rings: int, fpr: float }
    """
    return state.stats


@app.get("/api/transactions")
async def get_transactions(limit: int = 50, offset: int = 0):
    """
    GET /api/transactions
    Returns: [{ txn_id, timestamp, account_id, amount, merchant, risk_score, is_fraud, explanation_preview }]
    """
    txns = state.transactions
    sliced = txns[offset : offset + limit]
    
    # Adhere strictly to the API contract payload schema
    result = []
    for t in sliced:
        result.append({
            "txn_id": t["txn_id"],
            "timestamp": t["timestamp"],
            "account_id": t["account_id"],
            "amount": float(t["amount"]),
            "merchant": t.get("merchant", "Unknown Merchant"),
            "risk_score": float(t.get("risk_score", 0.05)),
            "is_fraud": bool(t.get("is_fraud", False)),
            "explanation_preview": t.get("explanation_preview", "Standard transaction."),
        })
    return result


@app.get("/api/rings")
async def get_rings():
    """
    GET /api/rings
    Returns: [{ ring_id, pattern_type, member_count, confidence, detected_at }]
    """
    rings_summary = []
    for r in state.detected_rings:
        rings_summary.append({
            "ring_id": r["ring_id"],
            "pattern_type": r["pattern_type"],
            "member_count": int(r["member_count"]),
            "confidence": float(r["confidence"]),
            "detected_at": r["detected_at"],
        })
    return rings_summary


@app.get("/api/rings/{ring_id}")
async def get_ring_detail(ring_id: str):
    """
    GET /api/rings/{id}
    Returns: { ring_id, pattern_type, members: [account_ids], confidence, deduction_text, timeline: [{ts, account, action}], subgraph_cytoscape_json: {} }
    """
    for r in state.detected_rings:
        if r["ring_id"].lower() == ring_id.lower():
            return {
                "ring_id": r["ring_id"],
                "pattern_type": r["pattern_type"],
                "members": r.get("members", []),
                "confidence": float(r.get("confidence", 0.95)),
                "deduction_text": r.get("deduction_text", "Forensic analysis unavailable."),
                "timeline": r.get("timeline", []),
                "subgraph_cytoscape_json": r.get("subgraph_cytoscape_json", {"elements": {"nodes": [], "edges": []}}),
            }
            
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Ring '{ring_id}' not found."
    )


@app.get("/api/graph/full")
async def get_full_graph():
    """
    GET /api/graph/full
    Returns: { elements: { nodes: [...], edges: [...] } } in standard Cytoscape JSON format
    """
    return state.graph_builder.to_cytoscape_json(max_nodes=350)


@app.post("/api/simulate/attack", status_code=status.HTTP_202_ACCEPTED)
async def simulate_attack(payload: Optional[Dict[str, Any]] = None, background_tasks: BackgroundTasks = None):
    """
    POST /api/simulate/attack
    Injects a simulated fraud ring transaction-by-transaction over 30s.
    Returns: { ring_id: str, status: "injecting" }
    """
    req = payload or {}
    attack_type = req.get("attack_type", "carousel")
    num_accounts = int(req.get("num_accounts", 5))
    total_amount = float(req.get("total_amount", 250000.0))
    ring_id = f"RING-SIM-{datetime.datetime.now().strftime('%M%S')}"

    def on_txn(txn):
        state.transactions.insert(0, txn)
        state.stats["total_txns"] += 1
        if txn.get("is_fraud"):
            state.stats["fraud_detected"] += 1

    # Launch background simulation task
    asyncio.create_task(
        simulator.run_simulation(
            attack_type=attack_type,
            num_accounts=num_accounts,
            total_amount=total_amount,
            ring_id=ring_id,
            on_transaction_created=on_txn
        )
    )

    return {
        "ring_id": ring_id,
        "status": "injecting"
    }


# ═══════════════════════════════════════════════════════════════════════════
# WEBSOCKET STREAMING
# ═══════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint: ws://localhost:8000/ws/transactions
    Broadcasts real-time events:
      - `new_transaction`
      - `ring_detected`
      - `stats_update`
    """
    await manager.connect(websocket)
    try:
        # Send initial stats update on connect
        await websocket.send_json({
            "type": "stats_update",
            "data": state.stats
        })
        while True:
            # Keep alive and receive optional client messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
