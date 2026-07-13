"""Add owner login protection and MFA state.

Revision ID: 20260712_0003
Revises: 20260712_0002
Create Date: 2026-07-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260712_0003"
down_revision: str | None = "20260712_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "owners",
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("owners", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("owners", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("owners", sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True))
    op.add_column(
        "owners",
        sa.Column("mfa_recovery_hashes", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column("owners", sa.Column("mfa_enabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("owners", sa.Column("mfa_last_used_step", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("owners", "mfa_last_used_step")
    op.drop_column("owners", "mfa_enabled_at")
    op.drop_column("owners", "mfa_recovery_hashes")
    op.drop_column("owners", "mfa_secret_encrypted")
    op.drop_column("owners", "last_login_at")
    op.drop_column("owners", "locked_until")
    op.drop_column("owners", "failed_login_count")
