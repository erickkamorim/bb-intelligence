"""schema inicial (Etapa 1)

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("license_notes", sa.Text, nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("document_type", sa.String(40), nullable=False),
        sa.Column("period", sa.String(10)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("locator", sa.Text),
        sa.UniqueConstraint("source_id", "file_hash", name="uq_documents_source_hash"),
    )
    op.create_table(
        "indicators",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(60), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("definition", sa.Text, nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
    )
    op.create_table(
        "observations",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("indicator_id", sa.Integer, sa.ForeignKey("indicators.id"), nullable=False),
        sa.Column("period_start", sa.Date),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("period_type", sa.String(10), nullable=False),
        sa.Column("value", sa.Numeric(24, 6), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("entity_scope", sa.String(20), nullable=False),
        sa.Column("source_document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer, nullable=False, server_default="0"),
        sa.Column("derivation", sa.String(60)),
        sa.Column("extra", JSONB),
        sa.CheckConstraint("period_type IN ('quarter','ytd','fy','ltm','instant','daily','monthly')",
                           name="ck_obs_period_type"),
    )
    # period_start pode ser NULL (saldos/séries diárias): NULLS NOT DISTINCT exige PostgreSQL 15+
    op.execute(
        "ALTER TABLE observations ADD CONSTRAINT uq_observation_revision UNIQUE NULLS NOT DISTINCT "
        "(indicator_id, period_start, period_end, period_type, entity_scope, revision)"
    )
    op.create_index("ix_obs_indicator_period", "observations", ["indicator_id", "period_end"])

    op.create_table(
        "market_prices",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("ticker", sa.String(12), nullable=False),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("close", sa.Numeric(18, 6)),
        sa.Column("adjusted_close", sa.Numeric(18, 6)),
        sa.Column("volume", sa.BigInteger),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ticker", "trade_date", "source_id", name="uq_market_price"),
    )
    op.create_table(
        "etl_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_name", sa.String(80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rows_inserted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("rows_updated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text),
        sa.Column("details", JSONB),
    )
    op.create_index("ix_etl_runs_job", "etl_runs", ["job_name", "started_at"])
    op.create_table(
        "forecast_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("target_indicator_id", sa.Integer, sa.ForeignKey("indicators.id"), nullable=False),
        sa.Column("model_version", sa.String(60), nullable=False),
        sa.Column("origin_date", sa.Date, nullable=False),
        sa.Column("horizon", sa.Integer, nullable=False),
        sa.Column("forecast", sa.Float, nullable=False),
        sa.Column("lower_80", sa.Float),
        sa.Column("upper_80", sa.Float),
        sa.Column("actual", sa.Float),
        sa.Column("backtest_metrics", JSONB),
    )


def downgrade() -> None:
    for t in ["forecast_runs", "etl_runs", "market_prices", "observations", "indicators", "documents", "sources"]:
        op.drop_table(t)
