from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.models.user import User
from app.services import market_data
from app.services.market_data import PriceUnavailableError

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{ticker}/quote")
async def stock_quote(ticker: str, current_user: User = Depends(get_current_user)):
    try:
        return await market_data.get_quote(ticker)
    except PriceUnavailableError:
        raise HTTPException(status_code=404, detail=f"No quote available for {ticker.upper()}")


@router.get("/{ticker}/history")
async def stock_history(ticker: str, period: Literal["1D", "1W", "1M", "3M", "ALL"] = "1M",
                        current_user: User = Depends(get_current_user)):
    try:
        points = await market_data.get_history(ticker, period)
    except PriceUnavailableError:
        raise HTTPException(status_code=404, detail=f"No history available for {ticker.upper()}")
    return {"ticker": ticker.upper(), "period": period, "points": points}
