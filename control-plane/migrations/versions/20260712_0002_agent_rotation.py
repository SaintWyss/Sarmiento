"""Add automatic agent credential rotation state.

Revision ID: 20260712_0002
Revises: 20260712_0001
Create Date: 2026-07-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260712_0002"
down_revision: str | None = "20260712_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("credential_rotation_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "devices", sa.Column("credential_rotation_nonce", sa.String(64), nullable=True)
    )
    op.add_column(
        "devices", sa.Column("pending_token_hash", sa.String(64), nullable=True)
    )
    op.create_index(
        "ix_devices_pending_token_hash", "devices", ["pending_token_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_devices_pending_token_hash", table_name="devices")
    op.drop_column("devices", "pending_token_hash")
    op.drop_column("devices", "credential_rotation_nonce")
    op.drop_column("devices", "credential_rotation_requested_at")
