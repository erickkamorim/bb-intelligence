"""tabela peer_values (IF.data)

Revision ID: 0002_peer_values
Revises: 0001_initial
Create Date: 2026-11-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_peer_values"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "peer_values",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("cod_inst", sa.String(12), nullable=False),
        sa.Column("institution", sa.String(80), nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("metric", sa.String(40), nullable=False),
        sa.Column("value", sa.Numeric(24, 6), nullable=False),
        sa.Column("unit", sa.String(10), nullable=False),
        sa.Column("source_document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cod_inst", "period_end", "metric", name="uq_peer_value"),
    )
    op.create_index("ix_peer_period", "peer_values", ["period_end", "metric"])


def downgrade() -> None:
    op.drop_table("peer_values")
