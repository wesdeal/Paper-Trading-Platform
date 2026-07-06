import asyncio
import pytest
from app.services.order_service import place_order
from app.models.account import Account
from sqlalchemy import select
from decimal import Decimal


@pytest.mark.asyncio
async def test_excpetion_block(db_session, seeded_account):

    account_id = seeded_account

    session = db_session()

    with pytest.raises(TypeError):
        await place_order(session, account_id, ticker="AAPL", side="BUY",
                       quantity="ten", price=70.00, idempotency_key="order-1")
        

    session_2 = db_session()

    result = await place_order(
        session_2, account_id, ticker="AAPL", side="BUY",
        quantity=10, price=70.00, idempotency_key="order-2"
    )

    assert result is not None
    assert result.status == "FILLED"