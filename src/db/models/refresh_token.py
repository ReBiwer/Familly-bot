from datetime import datetime
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import DateTime

from src.db.models.base import BaseModel


class RefreshTokenModel(BaseModel):
    __tablename__ = "refresh_tokens"

    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    device_info: Mapped[str | None] = mapped_column(String, nullable=True)
