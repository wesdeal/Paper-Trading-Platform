import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Numeric, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class PortfolioSnapshot(Base):
    """Point-in-time record of an account's total value, written by a
    background task so /portfolio/history can serve a chart without
    replaying the ledger."""

    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        # history queries are always "one account, ordered by time"
        Index("ix_portfolio_snapshots_account_created", "account_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    positions_value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    account: Mapped["Account"] = relationship(back_populates="snapshots")
