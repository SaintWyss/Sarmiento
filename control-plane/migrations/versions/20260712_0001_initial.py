"""Sarmiento 1.0 initial schema.

Revision ID: 20260712_0001
Revises:
Create Date: 2026-07-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260712_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "owners",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("session_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_owners_username", "owners", ["username"], unique=True)
    op.create_table(
        "devices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rustdesk_id", sa.String(64), nullable=False),
        sa.Column("alias", sa.String(120), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(80), nullable=False),
        sa.Column("architecture", sa.String(80), nullable=False),
        sa.Column("agent_version", sa.String(40), nullable=False),
        sa.Column("rustdesk_version", sa.String(40), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("last_ip", sa.String(64)),
        sa.Column("last_seen", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("rustdesk_id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_devices_rustdesk_id", "devices", ["rustdesk_id"], unique=True)
    op.create_index("ix_devices_token_hash", "devices", ["token_hash"], unique=True)
    op.create_index("ix_devices_last_seen", "devices", ["last_seen"])
    op.create_table(
        "enrollment_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("owners.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_enrollment_tokens_token_hash", "enrollment_tokens", ["token_hash"], unique=True)
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_type", sa.String(24), nullable=False),
        sa.Column("actor_id", sa.String(80)),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("target_type", sa.String(40)),
        sa.Column("target_id", sa.String(80)),
        sa.Column("source_ip", sa.String(64)),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("enrollment_tokens")
    op.drop_table("devices")
    op.drop_table("owners")
