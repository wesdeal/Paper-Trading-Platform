# Signup logic shared by POST /auth/register and POST /accounts/ so the
# duplicate-email handling lives in exactly one place.

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.account import Account
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.user import User


class EmailAlreadyRegisteredError(Exception):
    pass


async def create_user_with_account(db, email: str, password: str,
                                   starting_balance: Decimal) -> tuple[User, Account]:
    email = email.strip().lower()

    # friendly fast-path check...
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)

    try:
        await db.flush()  # need user.id before creating the account
    except IntegrityError as exc:
        # ...and the unique constraint catches the two-signups-at-once race
        await db.rollback()
        raise EmailAlreadyRegisteredError(email) from exc

    account = Account(
        user_id=user.id,
        cash_balance=starting_balance,
        starting_balance=starting_balance,
    )
    db.add(account)
    await db.flush()

    # baseline snapshot so the portfolio chart has a starting point right
    # away instead of waiting for the first background tick
    db.add(PortfolioSnapshot(
        account_id=account.id,
        cash_balance=starting_balance,
        positions_value=Decimal("0"),
        total_value=starting_balance,
    ))
    await db.commit()
    return user, account


async def get_account_for_user(db, user: User) -> Account | None:
    """The user's (oldest) account. Multi-account support isn't built yet,
    so every 'which account?' question resolves here in one place."""
    account_query = (
        select(Account)
        .where(Account.user_id == user.id)
        .order_by(Account.created_at)
        .limit(1)
    )
    return (await db.execute(account_query)).scalar_one_or_none()
