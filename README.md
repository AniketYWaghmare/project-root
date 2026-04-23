# Customer Data Pipeline

A 3-service Docker data pipeline: Flask mock server → FastAPI ingestion → PostgreSQL storage.

## Architecture

```
Flask (port 5000) ──► FastAPI (port 8000) ──► PostgreSQL (port 5432)
  Mock Server            Pipeline                  Database
```

## Project Structure

```
project-root/
├── docker-compose.yml          ← Orchestrates all 3 services
├── README.md
├── mock-server/
│   ├── app.py                  ← Flask REST API
│   ├── Dockerfile
│   ├── requirements.txt
│   └── data/
│       └── customers.json      ← 22 customer records (source of truth)
└── pipeline-service/
    ├── main.py                 ← FastAPI app + all endpoints
    ├── database.py             ← SQLAlchemy engine + session + init_db()
    ├── Dockerfile
    ├── requirements.txt
    ├── models/
    │   └── customer.py         ← SQLAlchemy ORM model
    └── services/
        └── ingestion.py        ← Pagination fetch + upsert logic
```

## Quick Start

```bash
# 1. Build and start all services
docker-compose up -d --build

# 2. Wait ~15 seconds for services to be healthy, then test:

# Health checks
curl http://localhost:5000/api/health
curl http://localhost:8000/api/health

# Flask: paginated customer list
curl "http://localhost:5000/api/customers?page=1&limit=5"

# Flask: single customer
curl http://localhost:5000/api/customers/CUST001

# FastAPI: trigger ingestion (Flask → PostgreSQL)
curl -X POST http://localhost:8000/api/ingest

# FastAPI: paginated customers from DB
curl "http://localhost:8000/api/customers?page=1&limit=5"

# FastAPI: single customer from DB
curl http://localhost:8000/api/customers/CUST001

# Stop all services
docker-compose down
```

## API Reference

### Flask Mock Server (port 5000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/customers?page=1&limit=10` | Paginated customer list |
| GET | `/api/customers/{id}` | Single customer or 404 |

### FastAPI Pipeline (port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/ingest` | Fetch from Flask, upsert to PostgreSQL |
| GET | `/api/customers?page=1&limit=10` | Paginated results from DB |
| GET | `/api/customers/{id}` | Single customer from DB or 404 |
| GET | `/docs` | Auto-generated Swagger UI |

## Key Design Decisions

- **Auto-pagination during ingest**: The ingestion service loops through all Flask pages automatically — no manual pagination needed.
- **Upsert logic**: Uses PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` so running `/api/ingest` multiple times is idempotent.
- **Health checks in Compose**: `pipeline-service` waits for both `postgres` and `mock-server` to pass health checks before starting, preventing connection errors on cold start.
- **Persistent volume**: PostgreSQL data is stored in a named Docker volume (`pgdata`) so data survives `docker-compose restart`.
