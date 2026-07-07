from fastapi import APIRouter, Depends
from app.database import get_db
from app.schemas.account import AccountCreate
from app.models.user import User
from app.models.account import Account
from app.core.security import hash_password

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/x")
async def create_account(account_in: AccountCreate, db = Depends(get_db)):
    user = User(email=account_in.email, password_hash=hash_password(account_in.password))
    db.add(user)
    await db.flush()  # need user.id before creating the account

    account = Account(
        user_id=user.id,
        cash_balance=account_in.starting_balance,
        starting_balance=account_in.starting_balance,
    )
    db.add(account)
    await db.commit()

    return {"account_id": account.id, "email": user.email, "cash_balance": account.cash_balance}


# TODO:
# - handle emails that already signed up
# - doesn't handle if this is a second account for a user (users can have many accounts)