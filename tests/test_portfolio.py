from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.account import Account
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.position import Position
from app.services.portfolio_service import (
    get_portfolio_summary,
    get_positions_detail,
    snapshot_all_accounts,
)


def fake_prices(mapping):
    async def getter(ticker):
        return Decimal(str(mapping[ticker]))
    return getter


async def _seed_positions(db_session, account_id):
    async with db_session() as session:
        session.add(Position(account_id=account_id, ticker="AAPL",
                             quantity=10, avg_cost_basis=Decimal("40.00")))
        session.add(Position(account_id=account_id, ticker="MSFT",
                             quantity=2, avg_cost_basis=Decimal("100.00")))
        # zero-quantity positions (fully sold) must not appear anywhere
        session.add(Position(account_id=account_id, ticker="TSLA",
                             quantity=0, avg_cost_basis=Decimal("200.00")))
        await session.commit()


@pytest.mark.asyncio
async def test_positions_detail_math(db_session, seeded_account):
    await _seed_positions(db_session, seeded_account)
    prices = fake_prices({"AAPL": "50.00", "MSFT": "90.00"})

    async with db_session() as session:
        account = (await session.execute(
            select(Account).where(Account.id == seeded_account))).scalar_one()
        detail = await get_positions_detail(session, account, prices)

    assert [p["ticker"] for p in detail] == ["AAPL", "MSFT"]

    aapl, msft = detail
    assert aapl["current_value"] == Decimal("500.00")
    assert aapl["unrealized_pl"] == Decimal("100.00")     # (50-40) * 10
    assert aapl["unrealized_pl_pct"] == Decimal("25.00")  # 100 / 400
    assert msft["unrealized_pl"] == Decimal("-20.00")     # (90-100) * 2
    assert msft["unrealized_pl_pct"] == Decimal("-10.00")


@pytest.mark.asyncio
async def test_portfolio_summary_math(db_session, seeded_account):
    await _seed_positions(db_session, seeded_account)
    prices = fake_prices({"AAPL": "50.00", "MSFT": "90.00"})

    async with db_session() as session:
        account = (await session.execute(
            select(Account).where(Account.id == seeded_account))).scalar_one()
        summary = await get_portfolio_summary(session, account, prices)

    # cash 1000 + positions (500 + 180) = 1680; started at 1000
    assert summary["cash_balance"] == Decimal("1000.00")
    assert summary["positions_value"] == Decimal("680.00")
    assert summary["total_value"] == Decimal("1680.00")
    assert summary["total_gain_loss"] == Decimal("680.00")
    assert summary["total_gain_loss_pct"] == Decimal("68.00")


@pytest.mark.asyncio
async def test_summary_falls_back_to_cost_basis_when_price_missing(db_session, seeded_account):
    await _seed_positions(db_session, seeded_account)

    async def flaky(ticker):
        if ticker == "MSFT":
            raise RuntimeError("provider down")
        return Decimal("50.00")

    async with db_session() as session:
        account = (await session.execute(
            select(Account).where(Account.id == seeded_account))).scalar_one()
        summary = await get_portfolio_summary(session, account, flaky)

    # MSFT valued at its 100.00 basis instead of vanishing from the total
    assert summary["positions_value"] == Decimal("700.00")


@pytest.mark.asyncio
async def test_snapshot_all_accounts_writes_rows(db_session, seeded_account):
    await _seed_positions(db_session, seeded_account)
    prices = fake_prices({"AAPL": "50.00", "MSFT": "90.00"})

    written = await snapshot_all_accounts(db_session, prices)
    assert written == 1

    async with db_session() as session:
        snapshot = (await session.execute(select(PortfolioSnapshot))).scalar_one()

    assert snapshot.account_id == seeded_account
    assert snapshot.cash_balance == Decimal("1000.00")
    assert snapshot.positions_value == Decimal("680.00")
    assert snapshot.total_value == Decimal("1680.00")
