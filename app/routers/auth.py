from app.schemas.login import LoginRequest
from app.schemas.account import AccountCreate
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.models.user import User
from sqlalchemy import select
from app.core.security import create_access_token, verify_password
from app.services.account_service import EmailAlreadyRegisteredError, create_user_with_account

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(account_in: AccountCreate, db = Depends(get_db)):
    """Signup: creates the user + their paper account and returns a token so
    the frontend can log straight in. Same logic as POST /accounts/."""
    try:
        user, account = await create_user_with_account(
            db, account_in.email, account_in.password, account_in.starting_balance
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(status_code=409, detail="That email is already registered")

    token = create_access_token(str(user.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email,
        "account_id": account.id,
    }

@router.post("/login")
async def login(credentials: LoginRequest, db = Depends(get_db)):
    # 1. look up the User by email -- what should happen if no user has that email?
    #    (think back to get_order_by_idempotency_key vs get_account_for_update --
    #     which "shape" of missing-result handling fits here?)
    user_query = select(User).where(User.email == credentials.email)
    existing_user = (await db.execute(user_query)).scalar_one_or_none()

    if existing_user is None or not verify_password(credentials.password, existing_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # create token
    token = create_access_token(str(existing_user.id))
    return {"access_token": token, "token_type": "bearer"}



    
