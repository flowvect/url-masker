"""Link model — the central table: stores every shortened / masked URL."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Sequence,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# Dedicated sequence for generating the integer IDs used by the base62 encoder.
link_id_seq = Sequence("link_id_seq")


class Link(Base):
    __tablename__ = "links"

    # ── Primary key (UUID for external references) ────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Auto-incrementing integer used by the base62 shortener ────────────
    sequence_id: Mapped[int] = mapped_column(
        BigInteger,
        link_id_seq,
        server_default=link_id_seq.next_value(),
        unique=True,
        nullable=False,
    )

    # ── Core fields ───────────────────────────────────────────────────────
    short_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    long_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # ── Ownership (nullable for anonymous links) ──────────────────────────
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # ── Masking / cloaking flag ───────────────────────────────────────────
    is_masked: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_alias: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Expiration ────────────────────────────────────────────────────────
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    click_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── Status ────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────
    owner = relationship("User", back_populates="links", lazy="selectin")
    clicks = relationship("Click", back_populates="link", lazy="selectin")
