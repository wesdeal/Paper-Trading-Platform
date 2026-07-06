# Portfolio math shared by the REST endpoints, the WebSocket pusher, and the
# snapshot background task. Everything takes a `price_getter` so tests can
# inject fixed prices.

import logging
from decimal import Decimal

from sqlalchemy import select

from app.models.account import Account
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.position import Position
from app.services import market_data

logger = logging.getLogger(__name__)

FOUR_DP = Decimal("0.0001")


async def get_positions_detail(db, account: Account, price_getter=market_data.get_price) -> list[dict]:
    """All open positions with live valuation. A position whose price lookup
    fails is valued at its cost basis rather than dropped, so totals stay
    sane when the provider hiccups."""
    positions_query = (
        select(Position)
        .where(Position.account_id == account.id, Position.quantity > 0)
        .order_by(Position.ticker)
    )
    positions = (await db.execute(positions_query)).scalars().all()

    detail = []
    for position in positions:
        try:
            current_price = Decimal(str(await price_getter(position.ticker)))
        except Exception:
            logger.warning("Price lookup failed for %s; valuing at cost basis", position.ticker)
            current_price = position.avg_cost_basis

        current_value = (current_price * position.quantity).quantize(FOUR_DP)
        cost = (position.avg_cost_basis * position.quantity).quantize(FOUR_DP)
        unrealized = current_value - cost
        unrealized_pct = (unrealized / cost * 100).quantize(FOUR_DP) if cost else Decimal("0")

        detail.append({
            "ticker": position.ticker,
            "quantity": position.quantity,
            "avg_cost_basis": position.avg_cost_basis,
            "current_price": current_price,
            "current_value": current_value,
            "unrealized_pl": unrealized,
            "unrealized_pl_pct": unrealized_pct,
        })
    return detail


async def get_portfolio_summary(db, account: Account, price_getter=market_data.get_price) -> dict:
    positions = await get_positions_detail(db, account, price_getter)
    positions_value = sum((p["current_value"] for p in positions), Decimal("0"))
    total_value = (account.cash_balance + positions_value).quantize(FOUR_DP)

    # gain/loss is measured against the account's starting balance: deposits
    # aren't a feature yet, so starting balance is the full cost of capital
    total_gain_loss = total_value - account.starting_balance
    total_gain_loss_pct = (
        (total_gain_loss / account.starting_balance * 100).quantize(FOUR_DP)
        if account.starting_balance
        else Decimal("0")
    )

    return {
        "cash_balance": account.cash_balance,
        "positions_value": positions_value,
        "total_value": total_value,
        "total_gain_loss": total_gain_loss,
        "total_gain_loss_pct": total_gain_loss_pct,
        "positions": positions,
    }


async def snapshot_all_accounts(session_factory, price_getter=market_data.get_price) -> int:
    """Write one PortfolioSnapshot per account. Called every few minutes by
    the background task; also safe to invoke manually."""
    written = 0
    async with session_factory() as db:
        accounts = (await db.execute(select(Account))).scalars().all()

        for account in accounts:
            try:
                summary = await get_portfolio_summary(db, account, price_getter)
            except Exception:
                logger.exception("Snapshot failed for account %s", account.id)
                continue
            db.add(PortfolioSnapshot(
                account_id=account.id,
                cash_balance=summary["cash_balance"],
                positions_value=summary["positions_value"],
                total_value=summary["total_value"],
            ))
            written += 1

        await db.commit()
    return written
