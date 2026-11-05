import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class ExtensionTrigger(str, enum.Enum):
    BID_RECEIVED = "bid_received"
    ANY_RANK_CHANGE = "any_rank_change"
    L1_RANK_CHANGE = "l1_rank_change"


class ActivityType(str, enum.Enum):
    BID_SUBMITTED = "bid_submitted"
    TIME_EXTENDED = "time_extended"
    AUCTION_CREATED = "auction_created"


class Auction(Base):
    __tablename__ = "auctions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    bid_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bid_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    forced_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pickup_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    trigger_window_minutes: Mapped[int] = mapped_column()
    extension_duration_minutes: Mapped[int] = mapped_column()
    extension_trigger: Mapped[ExtensionTrigger] = mapped_column(Enum(ExtensionTrigger))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bids: Mapped[list["Bid"]] = relationship(back_populates="auction", cascade="all, delete-orphan")
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        back_populates="auction", cascade="all, delete-orphan"
    )


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auctions.id", ondelete="CASCADE"), index=True)
    supplier_name: Mapped[str] = mapped_column(String(160))
    freight_charges: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    origin_charges: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    destination_charges: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), index=True)
    transit_time_days: Mapped[int] = mapped_column()
    validity_days: Mapped[int] = mapped_column()
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    auction: Mapped[Auction] = relationship(back_populates="bids")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auctions.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[ActivityType] = mapped_column(Enum(ActivityType))
    message: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    auction: Mapped[Auction] = relationship(back_populates="activity_logs")
