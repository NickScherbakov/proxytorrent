"""SQLAlchemy database models."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class FetchRequest(Base):
    """Database model for fetch requests."""

    __tablename__ = "fetch_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    headers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    ttl: Mapped[int] = mapped_column(Integer, nullable=False)

    # Content metadata
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    content_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Torrent metadata
    infohash: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    torrent_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Auth and rate limiting
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)

    def __repr__(self) -> str:
        """String representation."""
        return f"<FetchRequest(id={self.id}, status={self.status}, url={self.url[:50]})>"
