"""SQLAlchemyテーブル定義."""

# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from sqlalchemy import (
    ARRAY,
    Boolean,
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

assets = Table(  # type: ignore[arg-type]
    "assets",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("asset_class", String(16), nullable=False),
    Column("exchange", String(32), nullable=False),
    Column("symbol", String(64), nullable=False),
    Column("name", String(256), nullable=True),
    Column("status", String(16), nullable=False),
    Column("tradable", Boolean, nullable=False),
    Column("marginable", Boolean, nullable=True),
    Column("shortable", Boolean, nullable=True),
    Column("easy_to_borrow", Boolean, nullable=True),
    Column("fractionable", Boolean, nullable=True),
    Column("options_enabled", Boolean, nullable=True),
    Column("maintenance_margin_requirement", Numeric(10, 6), nullable=True),
    Column("min_order_size", String(32), nullable=True),
    Column("min_trade_increment", String(32), nullable=True),
    Column("price_increment", String(32), nullable=True),
    Column("source", String(32), nullable=False, default="alpaca"),
    Column("ingested_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

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
    Column("id", String(64), primary_key=True),
    Column("symbol", String(64), nullable=False, unique=True),
    Column("name", String(128), nullable=True),
    Column("status", String(16), nullable=False),
    Column("tradable", Boolean, nullable=False),
    Column("expiration_date", Date, nullable=False),
    Column("root_symbol", String(32), nullable=False),
    Column("underlying_symbol", String(32), nullable=False),
    Column("underlying_asset_id", String(64), nullable=True),
    Column("type", String(8), nullable=False),
    Column("style", String(16), nullable=True),
    Column("strike_price", Numeric(18, 4), nullable=False),
    Column("multiplier", String(16), nullable=True),
    Column("size", Integer, nullable=True),
    Column("open_interest", Integer, nullable=True),
    Column("open_interest_date", Date, nullable=True),
    Column("close_price", Numeric(18, 4), nullable=True),
    Column("close_price_date", Date, nullable=True),
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
