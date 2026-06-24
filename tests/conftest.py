import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings
from app.models.base import Base
import app.models  # noqa: F401 -- registers all models on Base.metadata


import uuid
from decimal import Decimal
from app.models.user import User
from app.models.account import Account


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.test_database_url)

    # start every test from a known-empty schema
    async with engine.begin() as conn:
        # drop all to start from clean database. no left over state
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # each place_order() needs its own session. do not want 
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    yield session_factory

    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_account(db_session):
    async with db_session() as session:
        user = User(email="test@example.com", password_hash="not-a-real-hash")
        session.add(user)
        await session.flush()  # need user.id before creating the account

        account = Account(
            user_id=user.id,
            cash_balance=Decimal("1000.00"),
            starting_balance=Decimal("1000.00"),
        )
        session.add(account)
        await session.commit()

        return account.id