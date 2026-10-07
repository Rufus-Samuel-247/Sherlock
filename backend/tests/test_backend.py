"""
Integration test for SHERLOCK backend.
Tests startup, ML inference, REST endpoints, and attack simulation.
"""

import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend root is in Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from fastapi.testclient import TestClient
from main import app, lifespan

def run_tests():
    print("🧪 Running SHERLOCK Backend End-to-End Tests...")
    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/api/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("✅ Health check passed:", res.json())

        # 2. Dashboard stats
        res = client.get("/api/dashboard/stats")
        assert res.status_code == 200, f"Stats failed: {res.text}"
        stats = res.json()
        assert stats["total_txns"] >= 10000, "Expected >= 10k transactions"
        assert stats["active_rings"] >= 3, "Expected at least 3 fraud rings"
        assert stats["precision"] >= 0.90, f"Precision {stats['precision']} < 0.90"
        print("✅ Dashboard stats passed:", stats)

        # 3. Transactions endpoint
        res = client.get("/api/transactions?limit=10&offset=0")
        assert res.status_code == 200, f"Transactions failed: {res.text}"
        txns = res.json()
        assert len(txns) == 10, "Expected 10 transactions"
        assert "risk_score" in txns[0], "Missing risk_score in transaction payload"
        assert "explanation_preview" in txns[0], "Missing explanation_preview"
        print("✅ Transactions query passed. Sample txn:", txns[0])

        # 4. Rings list endpoint
        res = client.get("/api/rings")
        assert res.status_code == 200, f"Rings list failed: {res.text}"
        rings = res.json()
        assert len(rings) >= 3, f"Expected at least 3 rings, got {len(rings)}"
        print(f"✅ Detected {len(rings)} rings:", [r["ring_id"] for r in rings])

        # 5. Ring detail endpoint
        ring_id = rings[0]["ring_id"]
        res = client.get(f"/api/rings/{ring_id}")
        assert res.status_code == 200, f"Ring detail failed: {res.text}"
        detail = res.json()
        assert "deduction_text" in detail, "Missing deduction_text"
        assert "subgraph_cytoscape_json" in detail, "Missing subgraph_cytoscape_json"
        print(f"✅ Ring detail passed for {ring_id}. Confidence: {detail['confidence']}")

        # 6. Full Graph endpoint
        res = client.get("/api/graph/full")
        assert res.status_code == 200, f"Full graph failed: {res.text}"
        graph_data = res.json()
        assert "elements" in graph_data, "Missing elements in graph"
        print(f"✅ Full graph returned {len(graph_data['elements']['nodes'])} nodes and {len(graph_data['elements']['edges'])} edges.")

        # 7. Attack simulation trigger
        res = client.post("/api/simulate/attack", json={
            "attack_type": "carousel",
            "num_accounts": 5,
            "total_amount": 250000
        })
        assert res.status_code == 202, f"Simulate attack failed: {res.text}"
        sim_res = res.json()
        assert sim_res["status"] == "injecting", "Expected status 'injecting'"
        print("✅ Attack simulation triggered successfully:", sim_res)

        # 8. Test WebSocket
        with client.websocket_connect("/ws/transactions") as websocket:
            init_msg = websocket.receive_json()
            assert init_msg["type"] == "stats_update", f"Unexpected WS message: {init_msg}"
            print("✅ WebSocket connected and received initial message:", init_msg["type"])

    print("\n🎉 ALL BACKEND TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
