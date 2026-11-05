from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import Base, engine, get_db
from .models import ActivityLog, ActivityType, Auction, Bid
from .schemas import ActivityResponse, AuctionCreate, AuctionDetail, AuctionSummary, BidCreate, BidResponse
from .service import auction_status, ranked_bids, submit_bid


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="GoComet British Auction API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/auctions", response_model=AuctionDetail, status_code=status.HTTP_201_CREATED)
async def create_auction(payload: AuctionCreate, session: AsyncSession = Depends(get_db)):
    existing = await session.scalar(select(Auction).where(Auction.reference_id == payload.reference_id))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Reference ID already exists")
    auction = Auction(**payload.model_dump())
    session.add(auction)
    await session.flush()
    session.add(
        ActivityLog(
            auction_id=auction.id,
            event_type=ActivityType.AUCTION_CREATED,
            message=f"Auction {auction.reference_id} created",
            metadata_json={},
        )
    )
    await session.commit()
    return await get_auction(auction.id, session)


@app.get("/api/v1/auctions", response_model=list[AuctionSummary])
async def list_auctions(session: AsyncSession = Depends(get_db)):
    auctions = (await session.execute(select(Auction).options(selectinload(Auction.bids)).order_by(Auction.created_at.desc()))).scalars()
    return [
        AuctionSummary(
            id=auction.id,
            reference_id=auction.reference_id,
            name=auction.name,
            bid_close_at=auction.bid_close_at,
            forced_close_at=auction.forced_close_at,
            status=auction_status(auction),
            current_lowest_bid=min((bid.total_amount for bid in auction.bids), default=None),
        )
        for auction in auctions
    ]


async def get_auction(auction_id, session: AsyncSession) -> AuctionDetail:
    auction = await session.scalar(
        select(Auction)
        .where(Auction.id == auction_id)
        .options(selectinload(Auction.bids), selectinload(Auction.activity_logs))
    )
    if not auction:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Auction not found")
    bids = ranked_bids(auction.bids)
    bid_responses = [
        BidResponse.model_validate({**BidResponse.model_validate(bid).model_dump(), "rank": rank})
        for rank, bid in enumerate(bids, 1)
    ]
    return AuctionDetail(
        id=auction.id, reference_id=auction.reference_id, name=auction.name,
        bid_start_at=auction.bid_start_at, bid_close_at=auction.bid_close_at,
        forced_close_at=auction.forced_close_at, pickup_at=auction.pickup_at,
        trigger_window_minutes=auction.trigger_window_minutes,
        extension_duration_minutes=auction.extension_duration_minutes,
        extension_trigger=auction.extension_trigger, status=auction_status(auction),
        current_lowest_bid=min((bid.total_amount for bid in auction.bids), default=None),
        bids=bid_responses,
        activity_logs=[ActivityResponse.model_validate(log) for log in sorted(auction.activity_logs, key=lambda item: item.created_at, reverse=True)],
    )


@app.get("/api/v1/auctions/{auction_id}", response_model=AuctionDetail)
async def auction_details(auction_id, session: AsyncSession = Depends(get_db)):
    return await get_auction(auction_id, session)


@app.post("/api/v1/auctions/{auction_id}/bids", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def create_bid(auction_id, payload: BidCreate, session: AsyncSession = Depends(get_db)):
    auction = await session.scalar(select(Auction).where(Auction.id == auction_id).with_for_update())
    if not auction:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Auction not found")
    bid = await submit_bid(session, auction, payload)
    await session.commit()
    await session.refresh(bid)
    bids = (await session.execute(select(Bid).where(Bid.auction_id == auction.id))).scalars().all()
    return BidResponse.model_validate({**BidResponse.model_validate(bid).model_dump(), "rank": ranked_bids(list(bids)).index(bid) + 1})
