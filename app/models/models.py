from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, BigInteger, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class Portfolio(Base):
    __tablename__ = 'portfolios'
    id = Column(BigInteger, primary_key=True)
    owner = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    trades = relationship('Trade', back_populates='portfolio')

    __table_args__ = (
        UniqueConstraint('owner', 'name', name='uq_portfolios_owner_name'),
        Index('idx_portfolios_owner', 'owner'),
    )

class Trade(Base):
    __tablename__ = 'trades'
    id = Column(BigInteger, primary_key=True)
    portfolio_id = Column(BigInteger, ForeignKey('portfolios.id'), nullable=False)
    ticker = Column(String(16), nullable=False)
    side = Column(String(8), nullable=False)
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    trade_time = Column(DateTime, nullable=False)
    status = Column(String(16))
    portfolio = relationship('Portfolio', back_populates='trades')
    audit_logs = relationship('AuditLog', back_populates='trade')

    __table_args__ = (
        Index('idx_trades_portfolio_id_trade_time', 'portfolio_id', 'trade_time'),
        Index('idx_trades_ticker', 'ticker'),
        Index('idx_trades_status', 'status'),
    )

class MarketData(Base):
    __tablename__ = 'market_data'
    id = Column(BigInteger, primary_key=True)
    ticker = Column(String(16), nullable=False)
    trade_time = Column(DateTime, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    extra_json = Column(JSON)

    __table_args__ = (
        Index('idx_market_data_ticker_trade_time', 'ticker', 'trade_time'),
    )

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(BigInteger, primary_key=True)
    trade_id = Column(BigInteger, ForeignKey('trades.id'), nullable=True)
    event_type = Column(String(32), nullable=False)
    event_data = Column(JSON, nullable=False)
    log_timestamp = Column(DateTime, nullable=False)
    trade = relationship('Trade', back_populates='audit_logs')

    __table_args__ = (
        Index('idx_audit_logs_trade_id', 'trade_id'),
        Index('idx_audit_logs_log_timestamp', 'log_timestamp'),
    )