""" FastAPI app and endpoint """

from fastapi import FastAPI

from contextlib import asynccontextmanager
from app.database import init_models
from app.routers import accounts, auth, orders




@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield

app = FastAPI(title="Paper Trading Platform", lifespan=lifespan)

app.include_router(accounts.router)
app.include_router(orders.router)
app.include_router(auth.router)

@app.get("/health")
async def health():
    return {"status": "ok"}

