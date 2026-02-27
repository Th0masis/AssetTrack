import enum
from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, String, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DisposalReason(str, enum.Enum):
    liquidation = "liquidation"   # Likvidace
    sale = "sale"                 # Prodej
    donation = "donation"         # Darování
    theft = "theft"               # Krádež
    loss = "loss"                 # Ztráta
    transfer = "transfer"         # Převod na jinou organizaci


class Disposal(Base):
    """Záznam o vyřazení majetku — append-only event."""

    __tablename__ = "disposals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(
        SAEnum(DisposalReason, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    disposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    disposed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    document_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    item: Mapped["Item"] = relationship(back_populates="disposals")
    disposed_by_user: Mapped["User | None"] = relationship(back_populates="disposals")
