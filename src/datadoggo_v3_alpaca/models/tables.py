"""SQLAlchemyテーブル定義."""

# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from sqlalchemy import (
    ARRAY,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    func,
)

SCHEMA_NAME = "alpaca"

metadata = MetaData(schema=SCHEMA_NAME)

stock_bars = Table(  # type: ignore[arg-type]
    "stock_bars",
    metadata,
    Column("symbol", String(32), primary_key=True),
    Column("timestamp", DateTime(timezone=True), primary_key=True),
    Column("timeframe", String(16), primary_key=True),
    Column("open", Float, nullable=False),
    Column("high", Float, nullable=False),
    Column("low", Float, nullable=False),
    Column("close", Float, nullable=False),
    Column("volume", Float, nullable=True),
    Column("trade_count", Integer, nullable=True),
    Column("vw", Float, nullable=True),
    Column("source", String(32), nullable=False, default="alpaca"),
    Column("ingested_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

crypto_bars = Table(  # type: ignore[arg-type]
    "crypto_bars",
    metadata,
    Column("symbol", String(32), primary_key=True),
    Column("timestamp", DateTime(timezone=True), primary_key=True),
    Column("timeframe", String(16), primary_key=True),
    Column("exchange", String(16), nullable=True),
    Column("open", Float, nullable=False),
    Column("high", Float, nullable=False),
    Column("low", Float, nullable=False),
    Column("close", Float, nullable=False),
    Column("volume", Float, nullable=True),
    Column("trade_count", Integer, nullable=True),
    Column("vw", Float, nullable=True),
    Column("source", String(32), nullable=False, default="alpaca"),
    Column("ingested_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

option_contracts = Table(  # type: ignore[arg-type]
    "option_contracts",
    metadata,
    Column("symbol", String(64), primary_key=True),
    Column("expiration", Date, nullable=False),
    Column("strike", Numeric(18, 4), nullable=False),
    Column("type", String(8), nullable=False),
    Column("multiplier", Integer, nullable=True),
    Column("root_symbol", String(32), nullable=True),
    Column("source", String(32), nullable=False, default="alpaca"),
    Column("ingested_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

option_bars = Table(  # type: ignore[arg-type]
    "option_bars",
    metadata,
    Column("symbol", String(64), primary_key=True),
    Column("timestamp", DateTime(timezone=True), primary_key=True),
    Column("timeframe", String(16), primary_key=True),
    Column("underlying_symbol", String(32), nullable=True),
    Column("open", Float, nullable=False),
    Column("high", Float, nullable=False),
    Column("low", Float, nullable=False),
    Column("close", Float, nullable=False),
    Column("volume", Float, nullable=True),
    Column("trade_count", Integer, nullable=True),
    Column("vw", Float, nullable=True),
    Column("open_interest", Integer, nullable=True),
    Column("source", String(32), nullable=False, default="alpaca"),
    Column("ingested_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

news_articles = Table(  # type: ignore[arg-type]
    "news_articles",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("headline", String(512), nullable=False),
    Column("summary", String(4096), nullable=True),
    Column("author", String(256), nullable=True),
    Column("url", String(1024), nullable=False),
    Column("source", String(64), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
    Column("symbols", ARRAY(String()), nullable=False),
    Column("ingested_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
