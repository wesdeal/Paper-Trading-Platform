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