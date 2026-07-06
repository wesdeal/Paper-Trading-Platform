from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class OrderCreate(BaseModel):
    # optional: when omitted, the user's default account is used
    account_id: str | None = None
    ticker: str
    side: Literal["BUY", "SELL"]
    quantity: int = Field(gt=0)
    order_type: Literal["MARKET", "LIMIT"] = "MARKET"
    # MARKET: optional -- server fetches the live price when omitted
    price: float | None = Field(default=None, gt=0)
    # LIMIT only
    limit_price: float | None = Field(default=None, gt=0)
    idempotency_key: str

    @model_validator(mode="after")
    def check_limit_price(self):
        if self.order_type == "LIMIT" and self.limit_price is None:
            raise ValueError("limit_price is required for LIMIT orders")
        return self


class OrderResponse(BaseModel):
    id: UUID
    ticker: str
    side: str
    order_type: str
    quantity: int
    limit_price: Decimal | None
    fill_price: Decimal | None  # from the execution, when filled
    status: str
    created_at: datetime | None
