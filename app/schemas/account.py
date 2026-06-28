from pydantic import BaseModel
from decimal import Decimal


class AccountCreate(BaseModel):
    email: str
    password: str
    starting_balance: Decimal = Decimal("100000.00")