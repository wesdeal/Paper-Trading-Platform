from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.security import get_current_user
from app.database import get_db
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.user import User
from app.services.account_service import get_account_for_user
from app.services.portfolio_service import get_portfolio_summary, get_positions_detail

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

Period = Literal["1D", "1W", "1M", "3M", "ALL"]

PERIOD_WINDOWS = {
    "1D": timedelta(days=1),
    "1W": timedelta(weeks=1),
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "ALL": None,
}


async def _require_account(db, current_user: User):
    account = await get_account_for_user(db, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="No account found for user")
    return account


@router.get("/summary")
async def portfolio_summary(db = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = await _require_account(db, current_user)
    summary = await get_portfolio_summary(db, account)
    summary.pop("positions")  # /portfolio/positions serves the detail
    return summary


@router.get("/positions")
async def portfolio_positions(db = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = await _require_account(db, current_user)
    return await get_positions_detail(db, account)


@router.get("/history")
async def portfolio_history(period: Period = "1M", db = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    account = await _require_account(db, current_user)

    history_query = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.account_id == account.id)
        .order_by(PortfolioSnapshot.created_at)
    )
    window = PERIOD_WINDOWS[period]
    if window is not None:
        history_query = history_query.where(
            PortfolioSnapshot.created_at >= datetime.now(timezone.utc) - window
        )

    snapshots = (await db.execute(history_query)).scalars().all()
    return {
        "period": period,
        "points": [
            {"timestamp": s.created_at, "total_value": s.total_value,
             "cash_balance": s.cash_balance, "positions_value": s.positions_value}
            for s in snapshots
        ],
    }
