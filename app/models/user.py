# User Model

import uuid 
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4 # uuid python object
        )
    
    email: Mapped[str] = mapped_column(String, unique=True, index=True) # uses email as index
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # A user can have multiple accounts
    accounts: Mapped[list["Account"]] = relationship(back_populates="user")
