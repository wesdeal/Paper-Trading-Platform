from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.database import get_db
from app.models.account import Account
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderCreate, OrderResponse
from app.services import market_data
from app.services.account_service import get_account_for_user
from app.services.market_data import PriceUnavailableError
from app.services.order_service import cancel_order, place_order

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_to_response(order: Order, fill_price=None) -> dict:
    return {
        "id": order.id,
        "ticker": order.ticker,
        "side": order.side,
        "order_type": order.order_type,
        "quantity": order.quantity,
        "limit_price": order.limit_price,
        "fill_price": fill_price,
        "status": order.status,
        "created_at": order.created_at,
    }


async def _resolve_account(db, order_in: OrderCreate, current_user: User) -> Account:
    if order_in.account_id is not None:
        account_query = select(Account).where(
            Account.id == order_in.account_id, Account.user_id == current_user.id
        )
        account = (await db.execute(account_query)).scalar_one_or_none()
    else:
        account = await get_account_for_user(db, current_user)

    if account is None:
        raise HTTPException(status_code=403, detail="Account not found or not yours")
    return account


@router.post("/")
async def create_order(order_in: OrderCreate, db = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = await _resolve_account(db, order_in, current_user)
    ticker = order_in.ticker.strip().upper()

    # MARKET orders fill at the live price; the client-supplied price is only
    # a fallback so scripts/tests can run without the market data provider
    price = order_in.price
    if order_in.order_type == "MARKET" and price is None:
        try:
            price = await market_data.get_price(ticker)
        except PriceUnavailableError:
            raise HTTPException(status_code=502, detail=f"Could not fetch a market price for {ticker}")

    try:
        order = await place_order(
            db, account.id, ticker, order_in.side,
            order_in.quantity, price, order_in.idempotency_key,
            order_type=order_in.order_type, limit_price=order_in.limit_price,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if order is None:
        # conflict with current server state: not enough cash or shares
        detail = "Insufficient Funds" if order_in.side == "BUY" else "Insufficient shares to sell"
        raise HTTPException(status_code=409, detail=detail)

    return {
        "id": order.id,
        "ticker": order.ticker,
        "side": order.side,
        "order_type": order.order_type,
        "quantity": order.quantity,
        "limit_price": order.limit_price,
        "status": order.status,
    }


@router.get("/", response_model=list[OrderResponse])
async def list_orders(ticker: str | None = None, db = Depends(get_db), current_user: User = Depends(get_current_user)):
    orders_query = (
        select(Order)
        .join(Account, Order.account_id == Account.id)
        .where(Account.user_id == current_user.id)
        .options(selectinload(Order.executions))
        .order_by(Order.created_at.desc())
    )
    if ticker is not None:
        orders_query = orders_query.where(Order.ticker == ticker.strip().upper())

    orders = (await db.execute(orders_query)).scalars().all()
    return [
        # fill price lives on the execution; PENDING/CANCELED orders have none
        _order_to_response(order, order.executions[0].fill_price if order.executions else None)
        for order in orders
    ]


@router.delete("/{order_id}", response_model=OrderResponse)
async def cancel_pending_order(order_id: UUID, db = Depends(get_db), current_user: User = Depends(get_current_user)):
    accounts_query = select(Account.id).where(Account.user_id == current_user.id)
    account_ids = set((await db.execute(accounts_query)).scalars().all())

    try:
        order = await cancel_order(db, order_id, account_ids)
    except LookupError:
        raise HTTPException(status_code=404, detail="Order not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    # a just-canceled order was PENDING, so it can't have executions --
    # don't touch the (unloaded) relationship after the commit
    return _order_to_response(order, fill_price=None)
