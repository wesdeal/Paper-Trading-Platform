import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Order(Base):
    __tablename__ = "orders"


    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    idempotency_key: Mapped[str] = mapped_column(String, unique=True)
    ticker: Mapped[str] = mapped_column(String)
    side: Mapped[str] = mapped_column(String) # BUY or SELL
    order_type: Mapped[str] = mapped_column(String) # MARKET or LIMIT
    quantity: Mapped[int] = mapped_column(Integer)
    # only set for LIMIT orders; MARKET orders fill at the live price
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    # PENDING -> FILLED | CANCELED | REJECTED
    status: Mapped[str] = mapped_column(String, default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    account: Mapped["Account"] = relationship(back_populates="orders")
    executions: Mapped[list["Execution"]] = relationship(back_populates="order")