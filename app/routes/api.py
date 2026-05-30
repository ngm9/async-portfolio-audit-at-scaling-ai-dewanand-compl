from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, AsyncSessionLocal
from app.models.models import Portfolio, Trade, MarketData, AuditLog
from app.schemas.schemas import TradeSummary, TradeOut, AuditLogOut, PortfolioSummary
from sqlalchemy import func
import datetime

router = APIRouter()

@router.get("/portfolio/{portfolio_id}/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(portfolio_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Fetch aggregate metrics (count and sum) directly inside Postgres
    metrics_stmt = select(
        func.count(Trade.id).label("total_trades"),
        func.coalesce(func.sum(Trade.amount), 0.0).label("total_amount")
    ).where(Trade.portfolio_id == portfolio_id)
    
    metrics_res = await db.execute(metrics_stmt)
    metrics_row = metrics_res.first()
    
    total_trades = metrics_row[0] if metrics_row else 0
    total_amount = float(metrics_row[1]) if metrics_row else 0.0

    # 2. Fetch only unique tickers, hitting the index directly
    tickers_stmt = select(Trade.ticker).where(Trade.portfolio_id == portfolio_id).distinct()
    tickers_res = await db.execute(tickers_stmt)
    tickers = list(tickers_res.scalars().all())

    return PortfolioSummary(
        portfolio_id=portfolio_id,
        total_trades=total_trades,
        total_amount=total_amount,
        tickers=tickers
    )

@router.post("/portfolio/{portfolio_id}/trade", response_model=TradeOut)
async def make_trade(portfolio_id: int, trade: TradeSummary, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    t = Trade(
        portfolio_id=portfolio_id,
        ticker=trade.ticker,
        side=trade.side,
        amount=trade.amount,
        price=trade.price,
        trade_time=datetime.datetime.utcnow(),
        status="executed"
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    
    # Enqueue task without passing request's db session to avoid async closed session errors
    background_tasks.add_task(audit_trade_event, t.id, 'TRADE_EXECUTED')
    
    return TradeOut(
        id=t.id, 
        ticker=t.ticker, 
        portfolio_id=t.portfolio_id, 
        side=t.side, 
        amount=t.amount, 
        price=t.price, 
        trade_time=str(t.trade_time), 
        status=t.status
    )

@router.get("/audit/{trade_id}", response_model=list[AuditLogOut])
async def get_audit_logs(trade_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(AuditLog).where(AuditLog.trade_id == trade_id).order_by(AuditLog.log_timestamp.desc()))
    logs = q.scalars().all()
    return [AuditLogOut(id=l.id, event_type=l.event_type, log_timestamp=str(l.log_timestamp), event_data=l.event_data) for l in logs]

async def audit_trade_event(trade_id: int, event_type: str):
    # Instantiate isolated database session with context manager for thread-safe background writing
    async with AsyncSessionLocal() as db:
        async with db.begin():
            a = AuditLog(
                trade_id=trade_id, 
                event_type=event_type, 
                event_data={"msg": "Executed trade"}, 
                log_timestamp=datetime.datetime.utcnow()
            )
            db.add(a)