import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select

from app.core.security import create_access_token, get_current_user
from app.models.account import Account
from app.models.user import User
from app.routers.orders import create_order
from app.schemas.order import OrderCreate


@pytest_asyncio.fixture
async def seeded_user(db_session):
    async with db_session() as session:
        user = User(email="flow@example.com", password_hash="not-a-real-hash")
        session.add(user)
        await session.flush()  # need user.id before creating the account

        account = Account(
            user_id=user.id,
            cash_balance=Decimal("1000.00"),
            starting_balance=Decimal("1000.00"),
        )
        session.add(account)
        await session.commit()

        return user.id, account.id


@pytest.mark.asyncio
async def test_get_current_user_returns_matching_user(db_session, seeded_user):
    user_id, _ = seeded_user
    token = create_access_token(str(user_id))

    async with db_session() as session:
        user = await get_current_user(token=token, db=session)

    assert user.id == user_id


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token(db_session):
    async with db_session() as session:
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="not-a-real-token", db=session)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_unknown_user(db_session):
    token = create_access_token(str(uuid.uuid4()))

    async with db_session() as session:
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=session)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_to_place_order_flow(db_session, seeded_user):
    """Resolves a user from a real token via get_current_user, then drives the
    same create_order endpoint logic the router calls, end to end."""
    user_id, account_id = seeded_user
    token = create_access_token(str(user_id))

    async with db_session() as session:
        current_user = await get_current_user(token=token, db=session)

        order_in = OrderCreate(
            account_id=str(account_id),
            ticker="AAPL",
            side="BUY",
            quantity=10,
            price=70.00,
            idempotency_key="flow-order-1",
        )

        result = await create_order(order_in, db=session, current_user=current_user)

    assert result["ticker"] == "AAPL"
    assert result["side"] == "BUY"
    assert result["quantity"] == 10
    assert result["status"] == "FILLED"

    async with db_session() as session:
        account = (
            await session.execute(select(Account).where(Account.id == account_id))
        ).scalar_one()

    assert account.cash_balance == Decimal("300.00")


@pytest.mark.asyncio
async def test_create_order_rejects_account_not_owned_by_current_user(db_session, seeded_user):
    """A token for a different user than the account owner should be turned
    away by the account ownership check in create_order, not place_order."""
    _, account_id = seeded_user

    async with db_session() as session:
        other_user = User(email="other@example.com", password_hash="not-a-real-hash")
        session.add(other_user)
        await session.commit()

        order_in = OrderCreate(
            account_id=str(account_id),
            ticker="AAPL",
            side="BUY",
            quantity=10,
            price=70.00,
            idempotency_key="flow-order-2",
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_order(order_in, db=session, current_user=other_user)

    assert exc_info.value.status_code == 403
