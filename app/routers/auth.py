from app.schemas.login import LoginRequest
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.models.user import User
from sqlalchemy import select
from app.core.security import create_access_token, verify_password
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

router = APIRouter(prefix="/auth", tags=["auth"])

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



    
