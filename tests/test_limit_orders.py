from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.account import Account
from app.models.execution import Execution
from app.models.ledger_entry import LedgerEntry
from app.models.order import Order
from app.models.position import Position
from app.services.limit_order_worker import process_open_limit_orders
from app.services.order_service import cancel_order, fill_limit_order, place_order


async def _place_limit_buy(db_session, account_id, *, limit_price="50.00",
                           quantity=10, key="limit-buy-1", ticker="AAPL"):
    async with db_session() as session:
        return await place_order(
            session, account_id, ticker=ticker, side="BUY",
            quantity=quantity, price=None, idempotency_key=key,
            order_type="LIMIT", limit_price=Decimal(limit_price),
        )


def fake_prices(mapping):
    async def getter(ticker):
        return Decimal(str(mapping[ticker]))
    return getter


@pytest.mark.asyncio
async def test_limit_order_placement_stays_pending(db_session, seeded_account):
    order = await _place_limit_buy(db_session, seeded_account)

    assert order is not None
    assert order.status == "PENDING"
    assert order.order_type == "LIMIT"
    assert order.limit_price == Decimal("50.00")

    async with db_session() as session:
        account = (await session.execute(
            select(Account).where(Account.id == seeded_account))).scalar_one()
        executions = (await session.execute(select(Execution))).scalars().all()
        ledger = (await session.execute(select(LedgerEntry))).scalars().all()

    # nothing moves until the fill: no cash change, no execution, no ledger rows
    assert account.cash_balance == Decimal("1000.00")
    assert executions == []
    assert ledger == []


@pytest.mark.asyncio
async def test_limit_buy_rejected_when_unaffordable_at_placement(db_session, seeded_account):
    # 100 shares * $50 = $5000 against a $1000 balance
    order = await _place_limit_buy(db_session, seeded_account, quantity=100)
    assert order is None


@pytest.mark.asyncio
async def test_limit_sell_rejected_without_position(db_session, seeded_account):
    async with db_session() as session:
        order = await place_order(
            session, seeded_account, ticker="AAPL", side="SELL",
            quantity=5, price=None, idempotency_key="limit-sell-1",
            order_type="LIMIT", limit_price=Decimal("50.00"),
        )
    assert order is None


@pytest.mark.asyncio
async def test_limit_order_requires_limit_price(db_session, seeded_account):
    async with db_session() as session:
        with pytest.raises(ValueError):
            await place_order(
                session, seeded_account, ticker="AAPL", side="BUY",
                quantity=1, price=None, idempotency_key="limit-nolimit",
                order_type="LIMIT", limit_price=None,
            )


@pytest.mark.asyncio
async def test_cancel_pending_limit_order(db_session, seeded_account):
    order = await _place_limit_buy(db_session, seeded_account)

    async with db_session() as session:
        canceled = await cancel_order(session, order.id, {seeded_account})
    assert canceled.status == "CANCELED"

    # a canceled order can't be canceled (or filled) again
    async with db_session() as session:
        with pytest.raises(ValueError):
            await cancel_order(session, order.id, {seeded_account})

    async with db_session() as session:
        result = await fill_limit_order(session, order.id, Decimal("40.00"))
    assert result is None


@pytest.mark.asyncio
async def test_cancel_rejects_other_users_order(db_session, seeded_account):
    import uuid
    order = await _place_limit_buy(db_session, seeded_account)

    async with db_session() as session:
        with pytest.raises(LookupError):
            await cancel_order(session, order.id, {uuid.uuid4()})


@pytest.mark.asyncio
async def test_limit_buy_fills_when_price_crosses(db_session, seeded_account):
    order = await _place_limit_buy(db_session, seeded_account, limit_price="50.00")

    # market above the limit: no fill
    async with db_session() as session:
        assert await fill_limit_order(session, order.id, Decimal("55.00")) is None

    # market at/below the limit: fills at the market price, not the limit price
    async with db_session() as session:
        filled = await fill_limit_order(session, order.id, Decimal("48.00"))
    assert filled is not None
    assert filled.status == "FILLED"

    async with db_session() as session:
        account = (await session.execute(
            select(Account).where(Account.id == seeded_account))).scalar_one()
        position = (await session.execute(
            select(Position).where(Position.account_id == seeded_account))).scalar_one()
        executions = (await session.execute(select(Execution))).scalars().all()
        ledger = (await session.execute(select(LedgerEntry))).scalars().all()

    assert account.cash_balance == Decimal("520.00")  # 1000 - 10 * 48
    assert position.ticker == "AAPL"
    assert position.quantity == 10
    assert position.avg_cost_basis == Decimal("48.00")
    assert len(executions) == 1
    assert executions[0].fill_price == Decimal("48.00")
    assert len(ledger) == 2  # atomic pattern preserved: cash leg + position leg
    assert {entry.direction for entry in ledger} == {"DEBIT", "CREDIT"}


@pytest.mark.asyncio
async def test_limit_sell_fills_when_price_crosses(db_session, seeded_account):
    # seed a 10-share position to sell out of
    async with db_session() as session:
        session.add(Position(
            account_id=seeded_account, ticker="AAPL",
            quantity=10, avg_cost_basis=Decimal("40.00"),
        ))
        await session.commit()

    async with db_session() as session:
        order = await place_order(
            session, seeded_account, ticker="AAPL", side="SELL",
            quantity=10, price=None, idempotency_key="limit-sell-2",
            order_type="LIMIT", limit_price=Decimal("60.00"),
        )
    assert order.status == "PENDING"

    # below the limit: no fill
    async with db_session() as session:
        assert await fill_limit_order(session, order.id, Decimal("59.99")) is None

    async with db_session() as session:
        filled = await fill_limit_order(session, order.id, Decimal("61.00"))
    assert filled.status == "FILLED"

    async with db_session() as session:
        account = (await session.execute(
            select(Account).where(Account.id == seeded_account))).scalar_one()
        position = (await session.execute(
            select(Position).where(Position.account_id == seeded_account))).scalar_one()

    assert account.cash_balance == Decimal("1610.00")  # 1000 + 10 * 61
    assert position.quantity == 0


@pytest.mark.asyncio
async def test_limit_fill_rejects_when_funds_are_gone(db_session, seeded_account):
    """Placement check passed, but the cash was spent before the fill:
    the order must end up REJECTED, not partially applied."""
    order = await _place_limit_buy(db_session, seeded_account, limit_price="90.00")

    # drain the account with a market order (10 * 95 = 950, leaving $50)
    async with db_session() as session:
        await place_order(
            session, seeded_account, ticker="MSFT", side="BUY",
            quantity=10, price=95.00, idempotency_key="drain-1",
        )

    async with db_session() as session:
        result = await fill_limit_order(session, order.id, Decimal("85.00"))
    assert result.status == "REJECTED"

    # the rejected order left no trace: cash untouched, no AAPL position
    async with db_session() as session:
        account = (await session.execute(
            select(Account).where(Account.id == seeded_account))).scalar_one()
        aapl = (await session.execute(select(Position).where(
            Position.account_id == seeded_account, Position.ticker == "AAPL",
        ))).scalar_one_or_none()
    assert account.cash_balance == Decimal("50.00")
    assert aapl is None


@pytest.mark.asyncio
async def test_worker_sweep_fills_only_qualifying_orders(db_session, seeded_account):
    fillable = await _place_limit_buy(
        db_session, seeded_account, limit_price="50.00", quantity=5, key="sweep-1")
    not_fillable = await _place_limit_buy(
        db_session, seeded_account, limit_price="30.00", quantity=5, key="sweep-2")

    acted_on = await process_open_limit_orders(
        db_session, price_getter=fake_prices({"AAPL": "45.00"}))

    assert [order.id for order in acted_on] == [fillable.id]

    async with db_session() as session:
        statuses = {
            order.id: order.status
            for order in (await session.execute(select(Order))).scalars().all()
        }
    assert statuses[fillable.id] == "FILLED"
    assert statuses[not_fillable.id] == "PENDING"


@pytest.mark.asyncio
async def test_worker_sweep_survives_price_lookup_failure(db_session, seeded_account):
    await _place_limit_buy(db_session, seeded_account, key="sweep-3")

    async def broken_getter(ticker):
        raise RuntimeError("provider down")

    acted_on = await process_open_limit_orders(db_session, price_getter=broken_getter)
    assert acted_on == []

    async with db_session() as session:
        order = (await session.execute(select(Order))).scalar_one()
    assert order.status == "PENDING"
