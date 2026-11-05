import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import ActivityType, ExtensionTrigger


class AuctionCreate(BaseModel):
    reference_id: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    bid_start_at: datetime
    bid_close_at: datetime
    forced_close_at: datetime
    pickup_at: datetime
    trigger_window_minutes: int = Field(ge=1, le=1440)
    extension_duration_minutes: int = Field(ge=1, le=1440)
    extension_trigger: ExtensionTrigger

    @model_validator(mode="after")
    def validate_times(self) -> "AuctionCreate":
        if self.bid_start_at >= self.bid_close_at:
            raise ValueError("bid_start_at must be before bid_close_at")
        if self.forced_close_at <= self.bid_close_at:
            raise ValueError("forced_close_at must be later than bid_close_at")
        return self


class BidCreate(BaseModel):
    supplier_name: str = Field(min_length=2, max_length=160)
    freight_charges: Decimal = Field(ge=0, decimal_places=2)
    origin_charges: Decimal = Field(ge=0, decimal_places=2)
    destination_charges: Decimal = Field(ge=0, decimal_places=2)
    transit_time_days: int = Field(ge=0, le=365)
    validity_days: int = Field(ge=1, le=365)


class BidResponse(BidCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    total_amount: Decimal
    submitted_at: datetime
    rank: int = 0


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    event_type: ActivityType
    message: str
    metadata_json: dict
    created_at: datetime


class AuctionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    reference_id: str
    name: str
    bid_close_at: datetime
    forced_close_at: datetime
    status: str
    current_lowest_bid: Decimal | None


class AuctionDetail(AuctionSummary):
    bid_start_at: datetime
    pickup_at: datetime
    trigger_window_minutes: int
    extension_duration_minutes: int
    extension_trigger: ExtensionTrigger
    bids: list[BidResponse]
    activity_logs: list[ActivityResponse]
