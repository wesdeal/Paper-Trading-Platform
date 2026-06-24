import asyncio
import pytest
from app.services.order_service import place_order
from app.models.account import Account
from sqlalchemy import select
from decimal import Decimal


@pytest.mark.asyncio
async def test_concurrent_orders_cannot_overspend(db_session, seeded_account):
    account_id = seeded_account

    session_1 = db_session()
    session_2 = db_session()

    results = await asyncio.gather(
        place_order(
            session_1, account_id, ticker="AAPL", side="BUY",
            quantity=10, price=70.00, idempotency_key="order-1",
        ),
        place_order(
            session_2, account_id, ticker="AAPL", side="BUY",
            quantity=10, price=70.00, idempotency_key="order-2",
        ),
        return_exceptions=True,
    )

    successful_orders = [r for r in results if r is not None and not isinstance(r, Exception)]
    rejected = [r for r in results if r is None]
    crashed = [r for r in results if isinstance(r, Exception)]

    assert len(successful_orders) == 1, f"Expected exactly 1 success, got {len(successful_orders)}"
    assert len(rejected) == 1, f"Expected exactly 1 rejection, got {len(rejected)}"
    assert len(crashed) == 0, f"Unexpected exceptions: {crashed}"


    async with db_session() as check_session:
        result = await check_session.execute(select(Account).where(Account.id == account_id))
        final_account = result.scalar_one()

    assert final_account.cash_balance == Decimal("300.00"), (
        f"Expected $300 remaining after one $700 trade, got {final_account.cash_balance}"
    )