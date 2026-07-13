from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_METADATA_BYTES = 16 * 1024
MAX_METADATA_KEYS = 64


def _validate_metadata(value: dict[str, Any]) -> dict[str, Any]:
    if len(value) > MAX_METADATA_KEYS:
        raise ValueError(f"metadata may contain at most {MAX_METADATA_KEYS} top-level keys")
    try:
        encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("metadata must be JSON serializable") from exc
    if len(encoded) > MAX_METADATA_BYTES:
        raise ValueError(f"metadata must not exceed {MAX_METADATA_BYTES} bytes")
    return value


def _strip_nonempty(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("value must not be blank")
    return normalized


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=512)
    verification_code: str | None = Field(default=None, max_length=64)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=12, max_length=512)


class OwnerView(BaseModel):
    id: str
    username: str
    mfa_enabled: bool = False


class MfaSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MfaEnableRequest(BaseModel):
    secret: str = Field(min_length=16, max_length=128)
    code: str = Field(min_length=6, max_length=64)


class MfaEnableResponse(BaseModel):
    recovery_codes: list[str]


class MfaDisableRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=512)
    code: str = Field(min_length=6, max_length=64)


class EnrollmentTokenCreate(BaseModel):
    label: str = Field(default="", max_length=120)
    ttl_minutes: int | None = Field(default=None, ge=1, le=1440)


class EnrollmentTokenIssued(BaseModel):
    id: str
    token: str
    label: str
    expires_at: datetime


class EnrollmentTokenView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None
    status: str


class AgentEnrollRequest(BaseModel):
    enrollment_token: str = Field(min_length=20, max_length=512)
    rustdesk_id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    alias: str = Field(min_length=1, max_length=120)
    hostname: str = Field(default="", max_length=255)
    platform: str = Field(default="unknown", max_length=80)
    architecture: str = Field(default="unknown", max_length=80)
    agent_version: str = Field(default="unknown", max_length=40)
    rustdesk_version: str = Field(default="unknown", max_length=40)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("alias")
    @classmethod
    def strip_alias(cls, value: str) -> str:
        return _strip_nonempty(value)

    @field_validator("hostname", "platform", "architecture")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_metadata(value)


class AgentEnrollResponse(BaseModel):
    device_id: str
    agent_token: str
    heartbeat_interval_seconds: int
    rustdesk_server: str
    rustdesk_key: str


class HeartbeatRequest(BaseModel):
    rustdesk_id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    hostname: str = Field(default="", max_length=255)
    platform: str = Field(default="unknown", max_length=80)
    architecture: str = Field(default="unknown", max_length=80)
    agent_version: str = Field(default="unknown", max_length=40)
    rustdesk_version: str = Field(default="unknown", max_length=40)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_metadata(value)


class HeartbeatResponse(BaseModel):
    accepted: bool = True
    server_time: datetime
    next_heartbeat_seconds: int
    credential_rotation_required: bool = False


class AgentTokenRotationResponse(BaseModel):
    agent_token: str


class DeviceUpdate(BaseModel):
    alias: str | None = Field(default=None, min_length=1, max_length=120)
    tags: list[str] | None = Field(default=None, max_length=20)

    @field_validator("alias")
    @classmethod
    def normalize_alias(cls, value: str | None) -> str | None:
        return None if value is None else _strip_nonempty(value)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = sorted({tag.strip().lower() for tag in value if tag.strip()})
        if any(len(tag) > 32 for tag in normalized):
            raise ValueError("tags must contain at most 32 characters")
        return normalized


class DeviceView(BaseModel):
    id: str
    rustdesk_id: str
    alias: str
    hostname: str
    platform: str
    architecture: str
    agent_version: str
    rustdesk_version: str
    tags: list[str]
    metadata: dict[str, Any]
    last_ip: str | None
    last_seen: datetime | None
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None
    credential_rotation_pending: bool
    online: bool
    connect_uri: str


class AuditEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_type: str
    actor_id: str | None
    action: str
    target_type: str | None
    target_id: str | None
    source_ip: str | None
    details: dict[str, Any]
    created_at: datetime


class StatsView(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    revoked_devices: int
    server_time: datetime


class PublicConfigView(BaseModel):
    product: str = "Sarmiento"
    version: str
    rustdesk_server: str
    rustdesk_key: str
    presence_threshold_seconds: int
