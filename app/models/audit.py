from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)  # open/closed

    created_by_user: Mapped["User"] = relationship(foreign_keys=[created_by], back_populates="audits")
    closed_by_user: Mapped["User | None"] = relationship(foreign_keys=[closed_by])
    scans: Mapped[list["AuditScan"]] = relationship(back_populates="audit")


class AuditScan(Base):
    __tablename__ = "audit_scans"

    __table_args__ = (
        UniqueConstraint("audit_id", "item_id", name="uq_audit_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    scanned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    audit: Mapped["Audit"] = relationship(back_populates="scans")
    item: Mapped["Item"] = relationship(back_populates="audit_scans")
    location: Mapped["Location | None"] = relationship(back_populates="audit_scans")
    scanned_by_user: Mapped["User | None"] = relationship(back_populates="audit_scans")
