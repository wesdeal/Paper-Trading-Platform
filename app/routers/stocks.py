from fastapi import APIRouter, Depends, HTTPException
from app.services.quote_service import get_quote_from_cache

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{ticker}/quote")
async def get_stock_quote(ticker: str):
    print(f"Ticker: {ticker}")
    price = await get_quote_from_cache(ticker)
    if price is None:
        raise HTTPException(status_code=404, detail="Quote not found.")
    return {
        "ticker": ticker.upper(),
        "price": price,
    }



from app.redis_client import redis_client
import time
@router.get("/watchlist")
async def get_watchlist():
    now = time.time()
    cutoff = now - 3600
    tickers = await redis_client.zrangebyscore("watchlist", cutoff, "+inf")
    return tickers


@router.get("/cache")
async def print_all_quotes():
    keys = await redis_client.keys("quote:*")
    for key in keys:
        value = await redis_client.get(key)
        ttl = await redis_client.ttl(key)
        print(f"{key}: {value}  (ttl={ttl}s)")

    return keys
    