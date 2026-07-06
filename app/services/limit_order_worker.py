# Scans PENDING LIMIT orders against live prices and fills the ones that
# qualify. Runs on a plain asyncio loop from the app lifespan -- APScheduler/
# Celery would add a dependency (and a second process) for what is a single
# periodic coroutine in a single-container deployment.

import logging

from sqlalchemy import select

from app.models.order import Order
from app.services import market_data
from app.services.order_service import fill_limit_order

logger = logging.getLogger(__name__)


async def process_open_limit_orders(session_factory, price_getter=market_data.get_price) -> list[Order]:
    """One sweep: fetch open LIMIT orders, price their tickers once each,
    and fill whichever orders qualify. Each fill runs in its own session/
    transaction so one failure can't poison the rest of the sweep.

    `price_getter` is injectable so tests can drive fills without network.
    Returns the orders that were acted on (FILLED or REJECTED).
    """
    async with session_factory() as db:
        pending_query = select(Order.id, Order.ticker, Order.side, Order.limit_price).where(
            Order.status == "PENDING",
            Order.order_type == "LIMIT",
        )
        pending = (await db.execute(pending_query)).all()

    if not pending:
        return []

    # one price lookup per distinct ticker per sweep
    prices = {}
    for ticker in {row.ticker for row in pending}:
        try:
            prices[ticker] = await price_getter(ticker)
        except Exception:
            logger.warning("Skipping %s this sweep: price lookup failed", ticker, exc_info=True)

    acted_on = []
    for row in pending:
        price = prices.get(row.ticker)
        if price is None:
            continue
        # cheap pre-filter; fill_limit_order re-checks under the row locks
        if row.side == "BUY" and price > row.limit_price:
            continue
        if row.side == "SELL" and price < row.limit_price:
            continue

        async with session_factory() as db:
            try:
                order = await fill_limit_order(db, row.id, price)
            except Exception:
                logger.exception("Failed to fill limit order %s", row.id)
                continue
        if order is not None:
            acted_on.append(order)
            logger.info("Limit order %s -> %s at %s", order.id, order.status, price)

    return acted_on
