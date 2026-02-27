from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Assignment(Base):
    """Append-only table — no UPDATE, no DELETE."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    item: Mapped["Item"] = relationship(back_populates="assignments")
    location: Mapped["Location"] = relationship(back_populates="assignments")
    user: Mapped["User | None"] = relationship(back_populates="assignments")
