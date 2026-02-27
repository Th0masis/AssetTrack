from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    responsible_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="item", order_by="Assignment.assigned_at"
    )
    audit_scans: Mapped[list["AuditScan"]] = relationship(back_populates="item")
    disposals: Mapped[list["Disposal"]] = relationship(back_populates="item")
