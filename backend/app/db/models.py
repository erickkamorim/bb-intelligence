"""Modelo de dados mínimo (seção 6 do briefing)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (BigInteger, Date, DateTime, Float, ForeignKey, Index, Integer, Numeric,
                        String, Text, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


JsonType = JSON().with_variant(JSONB(), "postgresql")
# BIGSERIAL no PostgreSQL; INTEGER no SQLite (necessário para autoincremento nos testes)
BigId = BigInteger().with_variant(Integer(), "sqlite")


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(Text)
    license_notes: Mapped[str] = mapped_column(Text)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source_id", "file_hash", name="uq_documents_source_hash"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    document_type: Mapped[str] = mapped_column(String(40))       # ITR, DFP, SGS, RI_RELEASE...
    period: Mapped[str | None] = mapped_column(String(10))       # 2026Q3, 2026, ...
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    file_hash: Mapped[str] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(Text)
    locator: Mapped[str | None] = mapped_column(Text)            # página/aba para curadoria manual


class IndicatorModel(Base):
    __tablename__ = "indicators"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(20))
    frequency: Mapped[str] = mapped_column(String(20))
    definition: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(20))               # consolidado | gerencial | macro


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("indicator_id", "period_start", "period_end", "period_type", "entity_scope",
                         "revision", name="uq_observation_revision"),
        Index("ix_obs_indicator_period", "indicator_id", "period_end"),
    )
    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    period_type: Mapped[str] = mapped_column(String(10))         # quarter | ytd | fy | instant | daily | monthly
    value: Mapped[float] = mapped_column(Numeric(24, 6))
    unit: Mapped[str] = mapped_column(String(20))
    entity_scope: Mapped[str] = mapped_column(String(20))        # consolidado | gerencial | macro
    source_document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=0)
    derivation: Mapped[str | None] = mapped_column(String(60))   # ex.: derived:FY_minus_9M_YTD
    extra: Mapped[dict | None] = mapped_column(JsonType)         # cd_conta, ds_conta, versao...


class MarketPrice(Base):
    __tablename__ = "market_prices"
    __table_args__ = (UniqueConstraint("ticker", "trade_date", "source_id", name="uq_market_price"),)
    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(12))
    trade_date: Mapped[date] = mapped_column(Date)
    close: Mapped[float | None] = mapped_column(Numeric(18, 6))
    adjusted_close: Mapped[float | None] = mapped_column(Numeric(18, 6))
    volume: Mapped[int | None] = mapped_column(BigInteger)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EtlRun(Base):
    __tablename__ = "etl_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String(80))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")  # running | success | failed
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JsonType)


class ForecastRun(Base):
    __tablename__ = "forecast_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_indicator_id: Mapped[int] = mapped_column(ForeignKey("indicators.id"))
    model_version: Mapped[str] = mapped_column(String(60))
    origin_date: Mapped[date] = mapped_column(Date)
    horizon: Mapped[int] = mapped_column(Integer)
    forecast: Mapped[float] = mapped_column(Float)
    lower_80: Mapped[float | None] = mapped_column(Float)
    upper_80: Mapped[float | None] = mapped_column(Float)
    actual: Mapped[float | None] = mapped_column(Float)
    backtest_metrics: Mapped[dict | None] = mapped_column(JsonType)


class PeerValue(Base):
    """Valores do IF.data por instituição (comparação entre bancos)."""
    __tablename__ = "peer_values"
    __table_args__ = (UniqueConstraint("cod_inst", "period_end", "metric", name="uq_peer_value"),)
    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    cod_inst: Mapped[str] = mapped_column(String(12))
    institution: Mapped[str] = mapped_column(String(80))
    period_end: Mapped[date] = mapped_column(Date)
    metric: Mapped[str] = mapped_column(String(40))
    value: Mapped[float] = mapped_column(Numeric(24, 6))
    unit: Mapped[str] = mapped_column(String(10))
    source_document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
