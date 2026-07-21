from decimal import Decimal
from app.redis_client import redis_client
from app.services.market_data import fetch_quote

TTL_SECONDS = 15

async def get_quote_from_cache(ticker: str) -> Decimal | None:
    ticker = ticker.upper()              # so "aapl" and "AAPL" share one cache entry
    key = f"quote:{ticker}"

    cached = await redis_client.get(key)     # MOVE 1: look in cache
    if cached is not None:
        return Decimal(cached)               #   HIT -> done, no API call

    price = await fetch_quote(ticker)        # MOVE 2: MISS -> hit the API
    if price is None:
        return None

    await redis_client.set(key, str(price), ex=TTL_SECONDS)   # MOVE 3: cache it w/ TTL
    return price
