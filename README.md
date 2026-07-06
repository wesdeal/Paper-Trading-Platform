# papertrade

A personal paper trading platform: FastAPI + PostgreSQL backend, React frontend,
live prices from Yahoo Finance via `yfinance`.

## Features

- Market and limit orders with an atomic Order + Execution + double-entry LedgerEntry write
- Background worker fills pending limit orders when the live price crosses the limit
- Portfolio summary, positions with unrealized P&L, and value history (5-minute snapshots)
- Live portfolio updates over WebSocket (`/ws/portfolio?token=<jwt>`)
- JWT auth (HS256, 24h), bcrypt password hashing
- Robinhood-inspired React UI with light/dark themes

## Local development

Prereqs: Docker, Node 20+ (22 recommended).

### Backend (Docker)

```bash
# .env at the repo root needs at least:
#   SECRET_KEY=<any long random hex string>
docker compose up --build
```

That starts Postgres, Redis (currently unused), and the API on
http://localhost:8000 (docs at `/docs`). Migrations (`alembic upgrade head`)
run automatically before uvicorn starts.

Run the tests inside the API container:

```bash
docker compose exec api python -m pytest -q
```

### Backend (bare virtualenv, optional)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
export DATABASE_URL=postgresql+asyncpg://trader:trader@localhost:5433/paper_trading
export TEST_DATABASE_URL=postgresql+asyncpg://trader:trader@localhost:5433/paper_trading_test
export SECRET_KEY=dev-secret
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL defaults to http://localhost:8000
npm run dev            # http://localhost:5173
```

### Existing databases and migrations

Databases created before Alembic was adopted (via `Base.metadata.create_all`)
must be stamped once before upgrading:

```bash
alembic stamp 5f558479fe41   # mark the pre-existing schema as the baseline
alembic upgrade head         # then apply everything newer
```

Fresh databases just run `alembic upgrade head` (the start command does this).

## Configuration

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | yes | — | `postgresql+asyncpg://...` |
| `SECRET_KEY` | yes | — | JWT signing key (HS256) |
| `CORS_ORIGINS` | no | localhost:5173/3000 | comma-separated allowed frontend origins |
| `TEST_DATABASE_URL` | tests only | `""` | pytest database |
| `PRICE_CACHE_TTL_SECONDS` | no | 15 | in-memory quote cache TTL |
| `LIMIT_ORDER_POLL_SECONDS` | no | 20 | limit-order fill sweep interval |
| `SNAPSHOT_INTERVAL_SECONDS` | no | 300 | portfolio snapshot interval |
| `WS_UPDATE_INTERVAL_SECONDS` | no | 15 | WebSocket push interval |
| `ENABLE_BACKGROUND_TASKS` | no | true | disable loops for scripts/tests |

Frontend: `VITE_API_URL` — base URL of the API.

## Deploying on Railway

Two services in one Railway project.

**1. PostgreSQL add-on** — provision it; Railway exposes `DATABASE_URL`.

**2. API service** (this repo's root, built from the `Dockerfile`):
- `DATABASE_URL`: reference the Postgres add-on's URL, **changing the scheme to
  `postgresql+asyncpg://`** (Railway hands out `postgresql://`).
- `SECRET_KEY`: a long random hex string (`openssl rand -hex 32`).
- `CORS_ORIGINS`: the frontend's public URL, e.g. `https://papertrade.up.railway.app`.
- No start command needed — the Dockerfile CMD runs `alembic upgrade head`
  then binds uvicorn to Railway's `$PORT`.

**3. Frontend service** (root directory `frontend/`):
- Build command `npm install && npm run build`, serve the `dist/` folder
  (Railway's static site preset, or `npx serve dist`).
- `VITE_API_URL`: the API service's public URL. Build-time variable — redeploy
  after changing it.

Single-process caveat: the limit-order fill sweep runs inside the API process.
Keep the API at **one replica**; two replicas would sweep (and race) twice.
