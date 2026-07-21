from pydantic import BaseModel


class OrderCreate(BaseModel):
    account_id: str
    ticker: str
    side: str
    quantity: int
    idempotency_key: str

class OrderResponse(BaseModel): # for when we return a successfully placed order:
    pass