from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ActivityLog, ActivityType, Auction, Bid, ExtensionTrigger
from .schemas import BidCreate


def auction_status(auction: Auction, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    if now >= auction.forced_close_at:
        return "force_closed"
    if now < auction.bid_start_at:
        return "scheduled"
    if now < auction.bid_close_at:
        return "active"
    return "closed"


def ranked_bids(bids: list[Bid]) -> list[Bid]:
    return sorted(bids, key=lambda bid: (bid.total_amount, bid.submitted_at, str(bid.id)))


async def submit_bid(session: AsyncSession, auction: Auction, payload: BidCreate) -> Bid:
    now = datetime.now(timezone.utc)
    if auction_status(auction, now) != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Auction is not accepting bids")

    total = payload.freight_charges + payload.origin_charges + payload.destination_charges
    existing = (await session.execute(select(Bid).where(Bid.auction_id == auction.id))).scalars().all()
    lowest = min((bid.total_amount for bid in existing), default=None)
    if lowest is not None and total >= lowest:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Bid must be lower than the current lowest bid")

    before = ranked_bids(list(existing))
    bid = Bid(auction_id=auction.id, total_amount=total, **payload.model_dump())
    session.add(bid)
    await session.flush()
    after = ranked_bids([*existing, bid])
    before_names = [item.supplier_name for item in before]
    after_names = [item.supplier_name for item in after]
    in_window = now >= auction.bid_close_at - timedelta(minutes=auction.trigger_window_minutes)
    rank_changed = before_names != after_names
    l1_changed = bool(before and before[0].supplier_name != after[0].supplier_name)
    trigger = auction.extension_trigger
    triggered = in_window and (
        trigger == ExtensionTrigger.BID_RECEIVED
        or (trigger == ExtensionTrigger.ANY_RANK_CHANGE and rank_changed)
        or (trigger == ExtensionTrigger.L1_RANK_CHANGE and l1_changed)
    )

    session.add(
        ActivityLog(
            auction_id=auction.id,
            event_type=ActivityType.BID_SUBMITTED,
            message=f"{bid.supplier_name} submitted a bid of {total:.2f}",
            metadata_json={"bid_id": str(bid.id), "total_amount": str(total)},
        )
    )
    if triggered:
        previous_close = auction.bid_close_at
        auction.bid_close_at = min(
            auction.bid_close_at + timedelta(minutes=auction.extension_duration_minutes),
            auction.forced_close_at,
        )
        if auction.bid_close_at > previous_close:
            session.add(
                ActivityLog(
                    auction_id=auction.id,
                    event_type=ActivityType.TIME_EXTENDED,
                    message=(
                        f"Auction extended to {auction.bid_close_at.isoformat()} "
                        f"(reason: {trigger.value.replace('_', ' ')})"
                    ),
                    metadata_json={
                        "reason": trigger.value,
                        "previous_close_at": previous_close.isoformat(),
                        "new_close_at": auction.bid_close_at.isoformat(),
                    },
                )
            )
    return bid
