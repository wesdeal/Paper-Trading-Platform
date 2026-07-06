from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.account import AccountCreate
from app.services.account_service import (
    EmailAlreadyRegisteredError,
    create_user_with_account,
    get_account_for_user,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/", status_code=201)
async def create_account(account_in: AccountCreate, db = Depends(get_db)):
    try:
        user, account = await create_user_with_account(
            db, account_in.email, account_in.password, account_in.starting_balance
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(status_code=409, detail="That email is already registered")

    return {"account_id": account.id, "email": user.email, "cash_balance": account.cash_balance}


@router.get("/me")
async def read_my_account(db = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = await get_account_for_user(db, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="No account found for user")

    return {
        "account_id": account.id,
        "email": current_user.email,
        "cash_balance": account.cash_balance,
        "starting_balance": account.starting_balance,
        "created_at": account.created_at,
    }
