from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.routers.accounts import create_account, read_my_account
from app.routers.auth import register
from app.schemas.account import AccountCreate
from app.services.account_service import (
    EmailAlreadyRegisteredError,
    create_user_with_account,
    get_account_for_user,
)


@pytest.mark.asyncio
async def test_signup_then_duplicate_email_conflicts(db_session):
    payload = AccountCreate(email="dup@example.com", password="hunter22")

    async with db_session() as session:
        created = await create_account(payload, db=session)
    assert created["email"] == "dup@example.com"
    assert created["cash_balance"] == Decimal("100000.00")

    async with db_session() as session:
        with pytest.raises(HTTPException) as exc_info:
            await create_account(payload, db=session)
    assert exc_info.value.status_code == 409

    # /auth/register shares the same service, so it conflicts the same way
    async with db_session() as session:
        with pytest.raises(HTTPException) as exc_info:
            await register(payload, db=session)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_email_is_case_insensitive(db_session):
    async with db_session() as session:
        await create_user_with_account(session, "Case@Example.com", "pw", Decimal("1000"))

    async with db_session() as session:
        with pytest.raises(EmailAlreadyRegisteredError):
            await create_user_with_account(session, "case@example.com", "pw", Decimal("1000"))


@pytest.mark.asyncio
async def test_register_returns_working_token(db_session):
    from app.core.security import get_current_user

    async with db_session() as session:
        result = await register(
            AccountCreate(email="new@example.com", password="hunter22"), db=session)

    assert result["token_type"] == "bearer"
    assert result["email"] == "new@example.com"

    async with db_session() as session:
        user = await get_current_user(token=result["access_token"], db=session)
    assert user.email == "new@example.com"


@pytest.mark.asyncio
async def test_accounts_me_returns_account_info(db_session):
    async with db_session() as session:
        user, account = await create_user_with_account(
            session, "me@example.com", "pw", Decimal("5000"))

    async with db_session() as session:
        me = await read_my_account(db=session, current_user=user)

    assert me["account_id"] == account.id
    assert me["email"] == "me@example.com"
    assert me["cash_balance"] == Decimal("5000")
    assert me["starting_balance"] == Decimal("5000")


@pytest.mark.asyncio
async def test_accounts_me_404s_without_account(db_session):
    from app.models.user import User

    async with db_session() as session:
        user = User(email="noacct@example.com", password_hash="not-a-real-hash")
        session.add(user)
        await session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await read_my_account(db=session, current_user=user)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_account_for_user_picks_oldest(db_session):
    from app.models.account import Account

    async with db_session() as session:
        user, first_account = await create_user_with_account(
            session, "multi@example.com", "pw", Decimal("1000"))
        session.add(Account(user_id=user.id, cash_balance=Decimal("1"),
                            starting_balance=Decimal("1")))
        await session.commit()

    async with db_session() as session:
        resolved = await get_account_for_user(session, user)
    assert resolved.id == first_account.id
