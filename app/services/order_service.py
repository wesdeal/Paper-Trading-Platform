# pessimistic locking strategy to ensure 2 transactions dont conflict balances or each other
#
# Order lifecycle:
#   MARKET -> filled immediately inside place_order (status FILLED)
#   LIMIT  -> stored as PENDING; a background worker calls fill_limit_order()
#             when the live price crosses the limit. PENDING orders can be
#             CANCELED; a fill that no longer passes the funds/shares check
#             is marked REJECTED.
#
# Lock ordering (deadlock safety): fill_limit_order locks the order row first,
# then the account row. cancel_order locks only the order row. place_order
# locks only the account row. No path holds the account lock while waiting on
# an order lock, so there is no cycle.

from decimal import Decimal

from sqlalchemy import select

from app.models.account import Account
from app.models.order import Order
from app.models.ledger_entry import LedgerEntry
from app.models.position import Position
from app.models.execution import Execution


async def get_account_for_update(db, account_id) -> Account:
    account_query = select(Account).where(Account.id == account_id).with_for_update()
    result = await db.execute(account_query)
    # scalar_one(): account_id is unique, anything else is a bug worth a 500
    return result.scalar_one()


async def get_order_by_idempotency_key(db, idempotency_key) -> Order | None:
    key_query = select(Order).where(Order.idempotency_key == idempotency_key)
    result = await db.execute(key_query)
    return result.scalar_one_or_none()


async def get_position(db, account_id, ticker) -> Position | None:
    # no separate lock needed: every writer already holds the account row lock,
    # which serializes access to that account's positions
    position_query = select(Position).where(
        Position.account_id == account_id,
        Position.ticker == ticker,
    )
    return (await db.execute(position_query)).scalar_one_or_none()


async def _apply_fill(db, account: Account, order: Order, price: Decimal) -> bool:
    """Move cash + shares and write the Execution and both LedgerEntry rows.

    Caller must already hold the account row lock and owns the commit/rollback.
    Returns False when the business check fails (insufficient funds/shares)
    without touching anything.
    """
    quantity = order.quantity
    total_cost = price * quantity

    if order.side == "BUY":
        if account.cash_balance < total_cost:
            return False

        cash_direction = "DEBIT"
        position_direction = "CREDIT"

        position = await get_position(db, account.id, order.ticker)
        if position is None:
            db.add(Position(
                account_id=account.id,
                ticker=order.ticker,
                quantity=quantity,
                avg_cost_basis=price,  # first lot: basis is just the fill price
            ))
        else:
            new_quantity = position.quantity + quantity
            # weighted average: ((old qty * old basis) + (qty * fill price)) / new qty
            position.avg_cost_basis = (
                (position.quantity * position.avg_cost_basis) + (quantity * price)
            ) / new_quantity
            position.quantity = new_quantity

        account.cash_balance -= total_cost

    elif order.side == "SELL":
        cash_direction = "CREDIT"
        position_direction = "DEBIT"

        position = await get_position(db, account.id, order.ticker)
        if position is None or position.quantity < quantity:
            return False

        position.quantity -= quantity
        # avg cost basis does not change on a sell
        account.cash_balance += total_cost

    else:
        return False

    await db.flush()  # need order.id persisted before the execution/ledger rows

    db.add(Execution(
        order_id=order.id,
        fill_quantity=quantity,
        fill_price=price,
    ))
    db.add(LedgerEntry(
        account_id=account.id,
        order_id=order.id,
        entry_type="TRADE",
        amount=total_cost,
        direction=cash_direction,
    ))
    db.add(LedgerEntry(
        account_id=account.id,
        order_id=order.id,
        entry_type="TRADE",
        amount=total_cost,
        direction=position_direction,
    ))
    return True


async def place_order(
    db, account_id, ticker, side, quantity, price, idempotency_key,
    order_type="MARKET", limit_price=None,
) -> Order | None:
    """Create an order. MARKET orders fill atomically here; LIMIT orders are
    stored PENDING for the background worker. Returns None on a business
    rejection (insufficient funds/shares, bad side)."""

    # idempotency check happens before any locks: it's read-only
    order_by_key = await get_order_by_idempotency_key(db, idempotency_key)
    if order_by_key is not None:
        return order_by_key

    if order_type == "LIMIT":
        if limit_price is None:
            raise ValueError("limit_price is required for LIMIT orders")
        limit_price = Decimal(str(limit_price))
        if limit_price <= 0:
            raise ValueError("limit_price must be positive")
    elif order_type == "MARKET":
        price = Decimal(str(price))
    else:
        raise ValueError(f"Unsupported order_type: {order_type}")

    try:
        account = await get_account_for_update(db, account_id)

        if order_type == "LIMIT":
            # advisory affordability check at placement time -- the worker
            # re-checks under the lock at fill time, since balances move
            if side == "BUY":
                if account.cash_balance < limit_price * quantity:
                    await db.rollback()
                    return None
            elif side == "SELL":
                position = await get_position(db, account.id, ticker)
                if position is None or position.quantity < quantity:
                    await db.rollback()
                    return None
            else:
                await db.rollback()
                return None

            new_order = Order(
                account_id=account_id,
                idempotency_key=idempotency_key,
                ticker=ticker,
                side=side,
                order_type="LIMIT",
                quantity=quantity,
                limit_price=limit_price,
                status="PENDING",
            )
            db.add(new_order)
            await db.commit()
            return new_order

        # MARKET: fill right now at the provided price
        new_order = Order(
            account_id=account_id,
            idempotency_key=idempotency_key,
            ticker=ticker,
            side=side,
            order_type="MARKET",
            quantity=quantity,
            status="FILLED",
        )
        db.add(new_order)

        filled = await _apply_fill(db, account, new_order, price)
        if not filled:
            await db.rollback()  # releases the account lock too
            return None

        await db.commit()
        return new_order
    except Exception:
        await db.rollback()
        raise


async def fill_limit_order(db, order_id, market_price) -> Order | None:
    """Attempt to fill one PENDING LIMIT order at the given market price.

    Re-checks everything under locks: the order may have been canceled or
    filled since the worker read it, and the account balance may have moved.
    Returns the order (FILLED or REJECTED) when it was acted on, None when
    the limit condition isn't met or the order is no longer fillable.
    """
    market_price = Decimal(str(market_price))

    try:
        order_query = select(Order).where(Order.id == order_id).with_for_update()
        order = (await db.execute(order_query)).scalar_one_or_none()

        if order is None or order.status != "PENDING" or order.order_type != "LIMIT":
            await db.rollback()
            return None

        buy_ready = order.side == "BUY" and market_price <= order.limit_price
        sell_ready = order.side == "SELL" and market_price >= order.limit_price
        if not (buy_ready or sell_ready):
            await db.rollback()
            return None

        account = await get_account_for_update(db, order.account_id)

        filled = await _apply_fill(db, account, order, market_price)
        if not filled:
            # funds/shares evaporated since placement: dead order, not retryable
            order.status = "REJECTED"
            await db.commit()
            return order

        order.status = "FILLED"
        await db.commit()
        return order
    except Exception:
        await db.rollback()
        raise


async def cancel_order(db, order_id, account_ids) -> Order:
    """Cancel a PENDING order owned by one of account_ids.

    Raises LookupError when the order doesn't exist / isn't theirs, and
    ValueError when it's not cancelable. The order row lock makes this safe
    against a concurrent fill_limit_order on the same order.
    """
    try:
        order_query = select(Order).where(Order.id == order_id).with_for_update()
        order = (await db.execute(order_query)).scalar_one_or_none()

        if order is None or order.account_id not in account_ids:
            await db.rollback()
            raise LookupError("Order not found")

        if order.status != "PENDING":
            status = order.status  # read before rollback() expires the object
            await db.rollback()
            raise ValueError(f"Only PENDING orders can be canceled (status is {status})")

        order.status = "CANCELED"
        await db.commit()
        return order
    except (LookupError, ValueError):
        raise
    except Exception:
        await db.rollback()
        raise
