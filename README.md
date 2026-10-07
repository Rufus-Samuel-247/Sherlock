# 🔍 SHERLOCK

**Financial Fraud Detection & Ring Analysis Engine**

A real-time fraud detection platform that uses graph neural networks, XGBoost, and SHAP-based explainability to identify and visualize fraud rings in financial transaction data.

---

## Architecture

```
sherlock/
├── backend/          # FastAPI + ML pipeline (Python)
├── frontend/         # Next.js 14 dashboard (TypeScript)
├── docs/             # API contract & documentation
│   └── API_CONTRACT.md
└── docker-compose.yml
```

## Quick Start

```bash
# Clone and run with Docker
git clone <repo-url> && cd sherlock
docker-compose up --build

# Backend only
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# Frontend only
cd frontend && npm install && npm run dev
```

## API Contract

See [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) for the strict payload definitions.

## Git Workflow

| Branch              | Purpose                        |
|---------------------|--------------------------------|
| `main`              | Production releases            |
| `develop`           | Integration branch             |
| `feature/backend-ml`| Backend & ML work (Person A)   |
| `feature/frontend-ui`| Frontend & UI work (Person B) |

## License

MIT
