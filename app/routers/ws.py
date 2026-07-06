# Live portfolio pushes. Browsers can't set an Authorization header on a
# WebSocket handshake, so the JWT rides in as ?token=<jwt> and is verified
# with the same decode path as get_current_user.

import asyncio
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.config import settings
from app.core.security import decode_token
from app.database import SessionLocal
from app.models.account import Account
from app.models.user import User
from app.services.portfolio_service import get_portfolio_summary

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

WS_POLICY_VIOLATION = 1008  # RFC 6455 close code for auth failures


async def _fetch_update(user_id: uuid.UUID) -> dict | None:
    # fresh short-lived session per tick; the connection itself can live hours
    async with SessionLocal() as db:
        account_query = (
            select(Account).where(Account.user_id == user_id)
            .order_by(Account.created_at).limit(1)
        )
        account = (await db.execute(account_query)).scalar_one_or_none()
        if account is None:
            return None
        summary = await get_portfolio_summary(db, account)

    return {
        "type": "portfolio_update",
        "total_value": float(summary["total_value"]),
        "cash_balance": float(summary["cash_balance"]),
        "positions_value": float(summary["positions_value"]),
        "total_gain_loss": float(summary["total_gain_loss"]),
        "total_gain_loss_pct": float(summary["total_gain_loss_pct"]),
        "positions": [
            {key: (float(value) if key != "ticker" and key != "quantity" else value)
             for key, value in position.items()}
            for position in summary["positions"]
        ],
    }


@router.websocket("/ws/portfolio")
async def portfolio_ws(websocket: WebSocket, token: str = Query(...)):
    user_id = decode_token(token)
    if user_id is None:
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        while True:
            update = await _fetch_update(user.id)
            if update is None:
                await websocket.close(code=WS_POLICY_VIOLATION)
                return
            await websocket.send_json(update)
            await asyncio.sleep(settings.ws_update_interval_seconds)
    except WebSocketDisconnect:
        pass  # client went away; nothing to clean up
    except Exception:
        logger.exception("portfolio websocket errored for user %s", user_id)
