from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.services.order_service import place_order
from app.schemas.order import OrderCreate
from app.core.security import get_current_user
from app.models.user import User
from app.models.account import Account
from app.services.quote_service import get_quote_from_cache
from sqlalchemy import select

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/")
async def create_order(order_in: OrderCreate, db = Depends(get_db), current_user: User = Depends(get_current_user),):

    # get account id by our user...
    # this is assuming user has One account...but what if they have multiple. which account do we use? how do we know
    account_query = select(Account).where(Account.id == order_in.account_id, Account.user_id == current_user.id)
    result = await db.execute(account_query)
    account = result.scalar_one_or_none()

    

    if account is None:
        raise HTTPException(status_code=403, detail="Account not found or not yours")
    
    price = await get_quote_from_cache(order_in.ticker)
    print(f"Price: of {order_in.ticker}: {price}")

    if price is None:
        raise HTTPException(status_code=400, detail="No quote available.")

    order = await place_order(
            db, account.id, order_in.ticker, order_in.side,
            order_in.quantity, price, order_in.idempotency_key
    )

    if order is None:
        raise HTTPException(status_code=409, detail="Insufficient Funds")
        # 409 because its a conflict with the current server state. the accounts cash bal is lower than the requested buy amount.
    
    return {
        "id": order.id,
        "ticker": order.ticker,
        "side": order.side,
        "quantity": order.quantity,
        "status": order.status,
    }

    