# pessamistic locking strategy to ensure 2 transactions dont conflict balances or each other

from decimal import Decimal

from sqlalchemy import select

from app.models.account import Account
from app.models.order import Order
from app.models.ledger_entry import LedgerEntry
from app.models.position import Position
from app.models.execution import Execution


async def get_account_for_update(db, account_id) -> Account:

    # use select() to query for an account by account_id
    # use .scalar_one() to ensure only one result comes back; fails if none or multiple are pulled. account_id is unique and should pull one
    account_query = select(Account).where(Account.id == account_id).with_for_update() # SELECT * FROM Account WHERE 

    # execute on the db. Use await since this is async
    result = await db.execute(account_query)

    # use .scalar_one() to ensure only one result comes back; fails if none or multiple are pulled. account_id is unique and should pull one
    account = result.scalar_one()
    return account
    # Note:
    """ 
     scalar_one() if fail will return a bland 500 server error. fine for now
     build handles later to catch and classify as a more descriptive 404
       """

async def get_order_by_idempotency_key(db, idempotency_key) -> Order | None:
    key_query = select(Order).where(Order.idempotency_key == idempotency_key)
    result = await db.execute(key_query)

    # .scalar_one_or_none() because it safely returns None if 0 results are found (good), raises only if 2 or more found
    # if 1 if found, still returns an object but easy to check. means there is already an existing order in place.
    existing_order = result.scalar_one_or_none() 
    return existing_order 

async def get_position(db, account_id, ticker) -> Position | None:
    # select Position where account_id matches AND ticker matches
    # no locking needed here -- why not? (hint: you're already holding
    # the account lock from get_account_for_update -- does that protect
    # this row too, given how account_id ties them together?)

    # query for position | check if it exists (filter for account id and ticker)

    position_query = select(Position).where(
        Position.account_id == account_id,
        Position.ticker == ticker
        )
    
    existing_position = (await db.execute(position_query)).scalar_one_or_none()
    return existing_position


async def place_order(db, account_id, ticker, side, quantity, price, idempotency_key) -> Order | None:

    price = Decimal(str(price))

    # check idempotency key
    order_by_key = await get_order_by_idempotency_key(db, idempotency_key)
    if order_by_key is not None:
        print(f"Order already exists, {order_by_key}")
        return order_by_key


    account = await get_account_for_update(db, account_id)

    total_order_cost = price * quantity

    # BUY side logic for Position
    if side == "BUY":
        if account.cash_balance < total_order_cost:
            print("Insufficient funds")
            return None # or some kind of error raise
        
        cash_direction="DEBIT"
        position_direction="CREDIT"
        
        position = await get_position(db, account.id, ticker)

        if position is None:
            # create a new position for this BUY order. ]
            new_position = Position(
                account_id=account_id,
                ticker=ticker,
                quantity=quantity,
                avg_cost_basis=price, # new position, avg cost basis is simple the fill price for the order
            )
            # add to db
            db.add(new_position)
        else: # position exists, need to update quantity, 
            new_quantity = position.quantity + quantity

            #calc new avg cost basis with simple formula: 
            #((old quantity x old acb) + (order quanity x order fill price)) / new quantity
            new_avg_cost_basis = ((position.quantity * position.avg_cost_basis) + (quantity * price)) / new_quantity
            position.avg_cost_basis = new_avg_cost_basis

            position.quantity = new_quantity

            # no need to commit as the db.commit() happens at end of outter most function

        # update cash balance
        account.cash_balance -= total_order_cost


    # SELL side logic for Position
    elif side == "SELL":
        cash_direction="CREDIT"
        position_direction="DEBIT"
        # position should exist if selling, but check anyway
        position = await get_position(db, account.id, ticker)

        if position is None:
            # raise some sort of error but print and return for now.
            print(f"Sell Error: You currently don't have a position for {ticker}.")
            return None
        else: 
            # queck if they have enough shares to sell

            if position.quantity < quantity:
                # raise some sort of error but print and return is fine for now
                print(f"Sell Error: Insufficent share quantity. Your current holding quantity: {position.quantity}. Your requested sell quantity: {quantity}.")
                return None
            
            new_quantity = position.quantity - quantity
            position.quantity = new_quantity

            # avg cost basis does not get updated for a sell.
            # update cash balance: 
            account.cash_balance += total_order_cost
    else:
        print("Order error. Try again.")

    # insert into order
    new_order = Order(
        account_id=account_id,
        idempotency_key=idempotency_key,
        ticker=ticker,
        side=side,
        order_type="MARKET",
        quantity=quantity,
        status="FILLED",
    ) # order status default to pending...change to FILLED when??
    db.add(new_order)
    await db.flush()  # need new_order.id before creating execution/ledger rows

    # insert into execution
    new_execution = Execution(
        order_id=new_order.id,
        fill_quantity=quantity,
        fill_price=price,
    )
    db.add(new_execution)

    # ledger entry inserts: 1 for cash bal update, 1 for position update
    ledger_cash_balance = LedgerEntry(
        account_id=account_id,
        order_id=new_order.id,
        entry_type="TRADE",
        amount=total_order_cost,
        direction=cash_direction, # assigned in buy/sell logic
    )
    db.add(ledger_cash_balance)
    
    ledger_position = LedgerEntry(
        account_id=account_id,
        order_id=new_order.id,
        entry_type= "TRADE",
        amount=total_order_cost,
        direction=position_direction, # assigned in buy/sell logic
    )
    db.add(ledger_position)

    await db.commit()

    return new_order


