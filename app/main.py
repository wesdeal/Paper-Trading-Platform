""" FastAPI app and endpoint """

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import accounts, auth, orders, portfolio, stocks, ws
from app.services.background_tasks import start_background_tasks, stop_background_tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # schema is owned by alembic now ("alembic upgrade head" runs before
    # uvicorn -- see docker-compose/Dockerfile), not create_all: create_all
    # can't ALTER existing tables and fights the migration history
    tasks = start_background_tasks() if settings.enable_background_tasks else []
    yield
    await stop_background_tasks(tasks)


app = FastAPI(title="Paper Trading Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(orders.router)
app.include_router(auth.router)
app.include_router(portfolio.router)
app.include_router(stocks.router)
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
