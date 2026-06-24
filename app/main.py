""" FastAPI app and endpoint """

from fastapi import FastAPI

from contextlib import asynccontextmanager
from app.database import init_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield

app = FastAPI(title="Paper Trading Platform", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}

