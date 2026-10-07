"""
SHERLOCK Backend — FastAPI Application Entry Point

Provides:
  • CORS middleware (open for development)
  • /api/health endpoint
  • Stub routers for transactions, rings, graph, and simulation
  • WebSocket endpoint placeholder
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List
import asyncio
import json

from config import settings


# ── WebSocket Connection Manager ────────────────────────────────────────────
class ConnectionManager:
    """Manages active WebSocket connections for real-time broadcasting."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send a JSON message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)


manager = ConnectionManager()


# ── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    print(f"🔍 {settings.APP_NAME} v{settings.APP_VERSION} starting up…")
    # TODO: Load ML models, generate synthetic data, etc.
    yield
    print(f"🛑 {settings.APP_NAME} shutting down…")


# ── App Instance ────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Financial Fraud Detection & Ring Analysis Engine",
    lifespan=lifespan,
)

# ── CORS Middleware ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
# REST ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health_check():
    """Health-check endpoint."""
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/dashboard/stats")
async def dashboard_stats():
    """Return aggregate dashboard statistics."""
    # TODO: Replace with real computed stats
    return {
        "total_txns": 0,
        "fraud_detected": 0,
        "precision": 0.0,
        "active_rings": 0,
        "fpr": 0.0,
    }


@app.get("/api/transactions")
async def get_transactions(limit: int = 50, offset: int = 0):
    """Return a paginated list of transactions."""
    # TODO: Implement with real/synthetic data
    return []


@app.get("/api/rings")
async def get_rings():
    """Return all detected fraud rings."""
    # TODO: Implement ring detection results
    return []


@app.get("/api/rings/{ring_id}")
async def get_ring_detail(ring_id: str):
    """Return detailed info about a specific fraud ring."""
    # TODO: Implement ring detail lookup
    return {
        "ring_id": ring_id,
        "pattern_type": "unknown",
        "members": [],
        "confidence": 0.0,
        "deduction_text": "",
        "timeline": [],
        "subgraph_cytoscape_json": {"elements": {"nodes": [], "edges": []}},
    }


@app.get("/api/graph/full")
async def get_full_graph():
    """Return the full transaction graph in Cytoscape.js JSON format."""
    # TODO: Build from NetworkX graph
    return {"elements": {"nodes": [], "edges": []}}


@app.post("/api/simulate/attack", status_code=202)
async def simulate_attack(payload: dict):
    """Inject a simulated fraud attack for demo/testing."""
    # TODO: Implement attack simulation
    return {"ring_id": "RING-SIM-001", "status": "injecting"}


# ═══════════════════════════════════════════════════════════════════════════
# WEBSOCKET
# ═══════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/transactions")
async def websocket_transactions(websocket: WebSocket):
    """Real-time transaction feed via WebSocket."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; listen for client messages if needed
            data = await websocket.receive_text()
            # Echo back for now (clients don't need to send anything)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ═══════════════════════════════════════════════════════════════════════════
# RUN (for development)
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
