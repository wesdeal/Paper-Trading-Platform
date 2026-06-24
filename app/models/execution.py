import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"))
    fill_quantity: Mapped[int] = mapped_column(Integer)
    fill_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order: Mapped["Order"] = relationship(back_populates="executions")