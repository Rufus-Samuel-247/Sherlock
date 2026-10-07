# SHERLOCK — Strict API & WebSocket Contract

> **This document is the single source of truth.** Both backend and frontend developers MUST adhere to these exact JSON payloads. Any deviation requires a mutual PR review.

---

## Base URLs

| Service   | URL                        |
|-----------|----------------------------|
| REST API  | `http://localhost:8000/api` |
| WebSocket | `ws://localhost:8000/ws/transactions` |

---

## REST Endpoints

### 1. `GET /api/health`

Health check endpoint.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

### 2. `GET /api/dashboard/stats`

Returns aggregate dashboard statistics.

**Response `200 OK`:**
```json
{
  "total_txns": 125000,
  "fraud_detected": 342,
  "precision": 0.974,
  "active_rings": 7,
  "fpr": 0.0012
}
```

| Field            | Type    | Description                              |
|------------------|---------|------------------------------------------|
| `total_txns`     | `int`   | Total transactions processed             |
| `fraud_detected` | `int`   | Number of flagged fraudulent txns        |
| `precision`      | `float` | Model precision (0.0–1.0)               |
| `active_rings`   | `int`   | Currently active fraud rings             |
| `fpr`            | `float` | False positive rate (0.0–1.0)           |

---

### 3. `GET /api/transactions`

Returns a list of recent transactions.

**Query Parameters (optional):**

| Param   | Type  | Default | Description          |
|---------|-------|---------|----------------------|
| `limit` | `int` | `50`    | Max results returned |
| `offset`| `int` | `0`     | Pagination offset    |

**Response `200 OK`:**
```json
[
  {
    "txn_id": "TXN-00042",
    "timestamp": "2026-10-07T12:34:56Z",
    "account_id": "ACC-1001",
    "amount": 4999.99,
    "merchant": "CryptoSwap Ltd.",
    "risk_score": 0.92,
    "is_fraud": true,
    "explanation_preview": "Unusual velocity: 12 txns in 3 min from dormant account."
  }
]
```

| Field                 | Type     | Description                                |
|-----------------------|----------|--------------------------------------------|
| `txn_id`              | `str`    | Unique transaction identifier              |
| `timestamp`           | `str`    | ISO 8601 timestamp                         |
| `account_id`          | `str`    | Source account identifier                  |
| `amount`              | `float`  | Transaction amount                         |
| `merchant`            | `str`    | Merchant / destination name                |
| `risk_score`          | `float`  | ML-assigned risk score (0.0–1.0)          |
| `is_fraud`            | `bool`   | Whether flagged as fraud                   |
| `explanation_preview` | `str`    | Short SHAP/XAI explanation snippet         |

---

### 4. `GET /api/rings`

Returns all detected fraud rings.

**Response `200 OK`:**
```json
[
  {
    "ring_id": "RING-007",
    "pattern_type": "carousel",
    "member_count": 5,
    "confidence": 0.89,
    "detected_at": "2026-10-07T11:00:00Z"
  }
]
```

| Field          | Type    | Description                                      |
|----------------|---------|--------------------------------------------------|
| `ring_id`      | `str`   | Unique ring identifier                           |
| `pattern_type` | `str`   | Pattern type: `carousel`, `funnel`, `layering`   |
| `member_count` | `int`   | Number of accounts in the ring                   |
| `confidence`   | `float` | Detection confidence (0.0–1.0)                  |
| `detected_at`  | `str`   | ISO 8601 detection timestamp                     |

---

### 5. `GET /api/rings/{id}`

Returns detailed information about a specific fraud ring, including graph data.

**Response `200 OK`:**
```json
{
  "ring_id": "RING-007",
  "pattern_type": "carousel",
  "members": ["ACC-1001", "ACC-1002", "ACC-1003", "ACC-1004", "ACC-1005"],
  "confidence": 0.89,
  "deduction_text": "### Deduction\nAccounts ACC-1001 through ACC-1005 engaged in circular fund transfers totaling $245,000 over 48 hours. The carousel pattern shows funds returning to the originator within 4 hops.",
  "timeline": [
    {
      "ts": "2026-10-06T08:00:00Z",
      "account": "ACC-1001",
      "action": "Initiated $50,000 transfer to ACC-1002"
    },
    {
      "ts": "2026-10-06T08:15:00Z",
      "account": "ACC-1002",
      "action": "Forwarded $49,500 to ACC-1003"
    }
  ],
  "subgraph_cytoscape_json": {
    "elements": {
      "nodes": [
        { "data": { "id": "ACC-1001", "label": "ACC-1001", "is_fraud": true, "risk_score": 0.95 } },
        { "data": { "id": "ACC-1002", "label": "ACC-1002", "is_fraud": true, "risk_score": 0.88 } }
      ],
      "edges": [
        { "data": { "source": "ACC-1001", "target": "ACC-1002", "amount": 50000, "timestamp": "2026-10-06T08:00:00Z" } }
      ]
    }
  }
}
```

| Field                     | Type     | Description                                   |
|---------------------------|----------|-----------------------------------------------|
| `ring_id`                 | `str`    | Unique ring identifier                        |
| `pattern_type`            | `str`    | Pattern type                                  |
| `members`                 | `[str]`  | List of account IDs in the ring               |
| `confidence`              | `float`  | Detection confidence                          |
| `deduction_text`          | `str`    | Markdown-formatted deduction narrative         |
| `timeline`                | `[obj]`  | Chronological list of events                  |
| `timeline[].ts`           | `str`    | ISO 8601 timestamp                            |
| `timeline[].account`      | `str`    | Account involved                              |
| `timeline[].action`       | `str`    | Human-readable action description             |
| `subgraph_cytoscape_json` | `obj`    | Standard Cytoscape.js JSON for the sub-graph  |

---

### 6. `GET /api/graph/full`

Returns the full transaction graph in Cytoscape.js JSON format.

**Response `200 OK`:**
```json
{
  "elements": {
    "nodes": [
      { "data": { "id": "ACC-1001", "label": "ACC-1001", "is_fraud": true, "risk_score": 0.95, "ring_id": "RING-007" } },
      { "data": { "id": "ACC-2050", "label": "ACC-2050", "is_fraud": false, "risk_score": 0.12, "ring_id": null } }
    ],
    "edges": [
      { "data": { "id": "e1", "source": "ACC-1001", "target": "ACC-1002", "amount": 50000, "is_suspicious": true } }
    ]
  }
}
```

| Node Field   | Type          | Description                        |
|-------------- |---------------|------------------------------------|
| `id`          | `str`         | Account ID                         |
| `label`       | `str`         | Display label                      |
| `is_fraud`    | `bool`        | Flagged as fraudulent              |
| `risk_score`  | `float`       | Risk score (0.0–1.0)             |
| `ring_id`     | `str \| null` | Associated ring, if any            |

| Edge Field      | Type   | Description                     |
|------------------|--------|---------------------------------|
| `id`             | `str`  | Unique edge ID                  |
| `source`         | `str`  | Source account ID               |
| `target`         | `str`  | Target account ID               |
| `amount`         | `float`| Transaction amount              |
| `is_suspicious`  | `bool` | Whether edge is suspicious      |

---

### 7. `POST /api/simulate/attack`

Injects a simulated fraud attack for demo/testing purposes.

**Request Body:**
```json
{
  "attack_type": "carousel",
  "num_accounts": 5,
  "total_amount": 250000
}
```

**Response `202 Accepted`:**
```json
{
  "ring_id": "RING-SIM-001",
  "status": "injecting"
}
```

---

## WebSocket: `ws://localhost:8000/ws/transactions`

Real-time transaction feed. The server pushes messages to all connected clients.

### Server → Client: New Transaction

```json
{
  "type": "new_transaction",
  "data": {
    "txn_id": "TXN-99001",
    "timestamp": "2026-10-07T12:35:01Z",
    "account_id": "ACC-3040",
    "amount": 7200.00,
    "merchant": "ShellCorp International",
    "risk_score": 0.97,
    "is_fraud": true,
    "explanation_preview": "Layering detected: 3-hop transfer from flagged origin."
  }
}
```

### Server → Client: Ring Detected

```json
{
  "type": "ring_detected",
  "data": {
    "ring_id": "RING-008",
    "pattern_type": "funnel",
    "member_count": 4,
    "confidence": 0.91,
    "detected_at": "2026-10-07T12:35:05Z"
  }
}
```

### Server → Client: Stats Update

```json
{
  "type": "stats_update",
  "data": {
    "total_txns": 125001,
    "fraud_detected": 343,
    "precision": 0.974,
    "active_rings": 8,
    "fpr": 0.0012
  }
}
```

---

## Error Response Format (All Endpoints)

```json
{
  "detail": "Human-readable error message.",
  "error_code": "RING_NOT_FOUND"
}
```

| HTTP Status | When                                |
|-------------|-------------------------------------|
| `400`       | Invalid request body / params       |
| `404`       | Resource not found                  |
| `500`       | Internal server error               |

---

## Versioning

All endpoints are unversioned for `v0.1.0`. Future versions will use `/api/v2/...` prefix.
