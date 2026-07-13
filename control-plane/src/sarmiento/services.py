from __future__ import annotations

import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import Settings
from .domain import DevicePresence, EnrollmentWindow
from .models import AuditEvent, Device, EnrollmentToken, Owner
from .security import (
    decrypt_secret,
    derive_token,
    encrypt_secret,
    generate_recovery_codes,
    generate_token,
    generate_totp_secret,
    hash_password,
    hash_recovery_code,
    hash_token,
    totp_provisioning_uri,
    verify_password,
    verify_totp,
)


class DomainError(Exception):
    status_code = 400


class AuthenticationError(DomainError):
    status_code = 401


class ConflictError(DomainError):
    status_code = 409


class NotFoundError(DomainError):
    status_code = 404


class GoneError(DomainError):
    status_code = 410


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def bootstrap_owner(session: Session, settings: Settings) -> Owner:
    existing = session.scalar(select(Owner).where(Owner.username == settings.owner_username))
    if existing:
        return existing
    if settings.environment.lower() == "production" and (
        not settings.owner_password or settings.owner_password == "change-me-now"
    ):
        raise RuntimeError("Set SARMIENTO_OWNER_PASSWORD for the first production bootstrap")
    owner = Owner(
        username=settings.owner_username,
        password_hash=hash_password(settings.owner_password),
    )
    session.add(owner)
    session.commit()
    session.refresh(owner)
    return owner


def audit(
    session: Session,
    *,
    actor_type: str,
    actor_id: str | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    source_ip: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        source_ip=source_ip,
        details=details or {},
    )
    session.add(event)
    return event


def owner_mfa_enabled(owner: Owner) -> bool:
    return bool(owner.mfa_enabled_at and owner.mfa_secret_encrypted)


def login_lock_remaining(owner: Owner, now: datetime | None = None) -> int:
    moment = now or datetime.now(UTC)
    locked_until = aware(owner.locked_until)
    if not locked_until or locked_until <= moment:
        return 0
    return max(1, int((locked_until - moment).total_seconds()))


def register_login_failure(
    session: Session,
    *,
    owner: Owner,
    settings: Settings,
    source_ip: str | None,
    reason: str,
    now: datetime | None = None,
) -> None:
    moment = now or datetime.now(UTC)
    remaining = login_lock_remaining(owner, moment)
    if remaining:
        audit(
            session,
            actor_type="anonymous",
            actor_id=None,
            action="auth.login_blocked",
            target_type="owner",
            target_id=owner.id,
            source_ip=source_ip,
        )
        session.commit()
        return
    if owner.locked_until:
        owner.locked_until = None
        owner.failed_login_count = 0
    owner.failed_login_count += 1
    if owner.failed_login_count >= settings.login_lockout_attempts:
        owner.locked_until = moment + timedelta(minutes=settings.login_lockout_minutes)
    audit(
        session,
        actor_type="anonymous",
        actor_id=None,
        action="auth.login_failed",
        target_type="owner",
        target_id=owner.id,
        source_ip=source_ip,
        details={"username": owner.username, "reason": reason},
    )
    session.commit()


def register_login_success(
    session: Session,
    *,
    owner: Owner,
    source_ip: str | None,
    now: datetime | None = None,
) -> None:
    moment = now or datetime.now(UTC)
    owner.failed_login_count = 0
    owner.locked_until = None
    owner.last_login_at = moment
    audit(
        session,
        actor_type="owner",
        actor_id=owner.id,
        action="auth.login_succeeded",
        source_ip=source_ip,
    )
    session.commit()


def verify_owner_second_factor(
    session: Session,
    *,
    owner: Owner,
    code: str | None,
    settings: Settings,
    source_ip: str | None,
    now: datetime | None = None,
) -> bool:
    if not owner_mfa_enabled(owner):
        return True
    if not code or not owner.mfa_secret_encrypted:
        return False
    moment = now or datetime.now(UTC)
    secret = decrypt_secret(owner.mfa_secret_encrypted, settings.effective_token_pepper)
    used_step = verify_totp(
        secret,
        code,
        now=moment,
        last_used_step=owner.mfa_last_used_step,
    )
    if used_step is not None:
        owner.mfa_last_used_step = used_step
        audit(
            session,
            actor_type="owner",
            actor_id=owner.id,
            action="auth.mfa_verified",
            source_ip=source_ip,
            details={"method": "totp"},
        )
        return True

    candidate = hash_recovery_code(code, settings.effective_token_pepper)
    hashes = list(owner.mfa_recovery_hashes or [])
    matched_index: int | None = None
    for index, stored in enumerate(hashes):
        if hmac.compare_digest(candidate, stored):
            matched_index = index
    if matched_index is None:
        return False
    hashes.pop(matched_index)
    owner.mfa_recovery_hashes = hashes
    audit(
        session,
        actor_type="owner",
        actor_id=owner.id,
        action="auth.mfa_verified",
        source_ip=source_ip,
        details={"method": "recovery_code", "remaining": len(hashes)},
    )
    return True


def begin_mfa_setup(owner: Owner) -> tuple[str, str]:
    if owner_mfa_enabled(owner):
        raise ConflictError("MFA is already enabled")
    secret = generate_totp_secret()
    return secret, totp_provisioning_uri(secret, owner.username)


def enable_owner_mfa(
    session: Session,
    *,
    owner: Owner,
    secret: str,
    code: str,
    settings: Settings,
    source_ip: str | None,
    now: datetime | None = None,
) -> list[str]:
    if owner_mfa_enabled(owner):
        raise ConflictError("MFA is already enabled")
    moment = now or datetime.now(UTC)
    used_step = verify_totp(secret, code, now=moment)
    if used_step is None:
        raise AuthenticationError("Invalid verification code")
    recovery_codes = generate_recovery_codes()
    owner.mfa_secret_encrypted = encrypt_secret(secret, settings.effective_token_pepper)
    owner.mfa_recovery_hashes = [
        hash_recovery_code(item, settings.effective_token_pepper) for item in recovery_codes
    ]
    owner.mfa_enabled_at = moment
    owner.mfa_last_used_step = None
    owner.session_version += 1
    audit(
        session,
        actor_type="owner",
        actor_id=owner.id,
        action="auth.mfa_enabled",
        target_type="owner",
        target_id=owner.id,
        source_ip=source_ip,
    )
    session.commit()
    return recovery_codes


def disable_owner_mfa(
    session: Session,
    *,
    owner: Owner,
    current_password: str,
    code: str,
    settings: Settings,
    source_ip: str | None,
) -> None:
    if not owner_mfa_enabled(owner):
        raise ConflictError("MFA is not enabled")
    if not verify_password(current_password, owner.password_hash):
        raise AuthenticationError("Current password is incorrect")
    if not verify_owner_second_factor(
        session,
        owner=owner,
        code=code,
        settings=settings,
        source_ip=source_ip,
    ):
        raise AuthenticationError("Invalid verification code")
    owner.mfa_secret_encrypted = None
    owner.mfa_recovery_hashes = []
    owner.mfa_enabled_at = None
    owner.mfa_last_used_step = None
    owner.session_version += 1
    audit(
        session,
        actor_type="owner",
        actor_id=owner.id,
        action="auth.mfa_disabled",
        target_type="owner",
        target_id=owner.id,
        source_ip=source_ip,
    )
    session.commit()


def change_owner_password(
    session: Session,
    *,
    owner: Owner,
    current_password: str,
    new_password: str,
    source_ip: str | None,
) -> None:
    if not verify_password(current_password, owner.password_hash):
        raise AuthenticationError("Current password is incorrect")
    if verify_password(new_password, owner.password_hash):
        raise ConflictError("New password must be different")
    owner.password_hash = hash_password(new_password)
    owner.session_version += 1
    audit(
        session,
        actor_type="owner",
        actor_id=owner.id,
        action="auth.password_changed",
        target_type="owner",
        target_id=owner.id,
        source_ip=source_ip,
    )
    session.commit()


def create_enrollment_token(
    session: Session,
    *,
    owner: Owner,
    settings: Settings,
    label: str,
    ttl_minutes: int | None,
    source_ip: str | None,
    now: datetime | None = None,
) -> tuple[EnrollmentToken, str]:
    moment = now or datetime.now(UTC)
    raw = generate_token("set")
    record = EnrollmentToken(
        token_hash=hash_token(raw, settings.effective_token_pepper),
        label=label,
        created_by=owner.id,
        created_at=moment,
        expires_at=moment + timedelta(minutes=ttl_minutes or settings.enrollment_ttl_minutes),
    )
    session.add(record)
    session.flush()
    audit(
        session,
        actor_type="owner",
        actor_id=owner.id,
        action="enrollment_token.created",
        target_type="enrollment_token",
        target_id=record.id,
        source_ip=source_ip,
        details={"label": label, "expires_at": record.expires_at.isoformat()},
    )
    session.commit()
    session.refresh(record)
    return record, raw


def enrollment_status(token: EnrollmentToken, now: datetime) -> str:
    if token.revoked_at:
        return "revoked"
    if token.used_at:
        return "used"
    if aware(token.expires_at) <= now:
        return "expired"
    return "active"


def revoke_enrollment_token(
    session: Session,
    *,
    token_id: str,
    owner: Owner,
    source_ip: str | None,
    now: datetime | None = None,
) -> EnrollmentToken:
    record = session.get(EnrollmentToken, token_id)
    if not record:
        raise NotFoundError("Enrollment token not found")
    if record.used_at:
        raise ConflictError("Used enrollment tokens cannot be revoked")
    if not record.revoked_at:
        record.revoked_at = now or datetime.now(UTC)
        audit(
            session,
            actor_type="owner",
            actor_id=owner.id,
            action="enrollment_token.revoked",
            target_type="enrollment_token",
            target_id=record.id,
            source_ip=source_ip,
        )
        session.commit()
        session.refresh(record)
    return record


def enrollment_token_for_update_statement(token_digest: str):
    """Select one enrollment token and serialize its consumption in PostgreSQL."""
    return (
        select(EnrollmentToken).where(EnrollmentToken.token_hash == token_digest).with_for_update()
    )


def enroll_device(
    session: Session,
    *,
    settings: Settings,
    payload: Any,
    source_ip: str | None,
    now: datetime | None = None,
) -> tuple[Device, str]:
    moment = now or datetime.now(UTC)
    token_digest = hash_token(payload.enrollment_token, settings.effective_token_pepper)
    enrollment = session.scalar(enrollment_token_for_update_statement(token_digest))
    if not enrollment:
        raise AuthenticationError("Invalid enrollment token")
    window = EnrollmentWindow(
        expires_at=aware(enrollment.expires_at),
        used_at=aware(enrollment.used_at),
        revoked_at=aware(enrollment.revoked_at),
    )
    if not window.is_valid(moment):
        raise GoneError("Enrollment token is expired, used, or revoked")

    existing = session.scalar(select(Device).where(Device.rustdesk_id == payload.rustdesk_id))
    if existing and existing.revoked_at is None:
        raise ConflictError("This RustDesk ID is already enrolled")

    raw_agent_token = generate_token("sat")
    digest = hash_token(raw_agent_token, settings.effective_token_pepper)
    if existing:
        device = existing
        device.alias = payload.alias
        device.hostname = payload.hostname
        device.platform = payload.platform
        device.architecture = payload.architecture
        device.agent_version = payload.agent_version
        device.rustdesk_version = payload.rustdesk_version
        device.metadata_json = payload.metadata
        device.token_hash = digest
        device.pending_token_hash = None
        device.credential_rotation_nonce = None
        device.credential_rotation_requested_at = None
        device.revoked_at = None
        device.last_seen = moment
        device.last_ip = source_ip
    else:
        device = Device(
            rustdesk_id=payload.rustdesk_id,
            alias=payload.alias,
            hostname=payload.hostname,
            platform=payload.platform,
            architecture=payload.architecture,
            agent_version=payload.agent_version,
            rustdesk_version=payload.rustdesk_version,
            metadata_json=payload.metadata,
            token_hash=digest,
            last_seen=moment,
            last_ip=source_ip,
        )
        session.add(device)

    enrollment.used_at = moment
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Device enrollment conflict") from exc

    audit(
        session,
        actor_type="agent",
        actor_id=device.id,
        action="device.enrolled",
        target_type="device",
        target_id=device.id,
        source_ip=source_ip,
        details={"rustdesk_id": device.rustdesk_id, "platform": device.platform},
    )
    session.commit()
    session.refresh(device)
    return device, raw_agent_token


def authenticate_agent(
    session: Session,
    raw_token: str,
    settings: Settings,
    *,
    source_ip: str | None = None,
) -> Device:
    digest = hash_token(raw_token, settings.effective_token_pepper)
    device = session.scalar(select(Device).where(Device.token_hash == digest))
    if device and device.revoked_at is None:
        return device

    pending = session.scalar(
        select(Device)
        .where(Device.pending_token_hash == digest)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not pending or pending.revoked_at is not None:
        raise AuthenticationError("Invalid or revoked agent token")

    pending.token_hash = digest
    pending.pending_token_hash = None
    pending.credential_rotation_nonce = None
    pending.credential_rotation_requested_at = None
    audit(
        session,
        actor_type="agent",
        actor_id=pending.id,
        action="device.credential_rotated",
        target_type="device",
        target_id=pending.id,
        source_ip=source_ip,
    )
    session.commit()
    session.refresh(pending)
    return pending


def record_heartbeat(
    session: Session,
    *,
    device: Device,
    payload: Any,
    source_ip: str | None,
    now: datetime | None = None,
) -> Device:
    if payload.rustdesk_id != device.rustdesk_id:
        raise ConflictError("Heartbeat RustDesk ID does not match the enrolled device")
    moment = now or datetime.now(UTC)
    device.hostname = payload.hostname
    device.platform = payload.platform
    device.architecture = payload.architecture
    device.agent_version = payload.agent_version
    device.rustdesk_version = payload.rustdesk_version
    device.metadata_json = payload.metadata
    device.last_ip = source_ip
    device.last_seen = moment
    session.commit()
    session.refresh(device)
    return device


def device_to_view(
    device: Device, settings: Settings, now: datetime | None = None
) -> dict[str, Any]:
    moment = now or datetime.now(UTC)
    online = DevicePresence(
        last_seen=aware(device.last_seen), revoked_at=aware(device.revoked_at)
    ).is_online(moment, settings.presence_threshold_seconds)
    return {
        "id": device.id,
        "rustdesk_id": device.rustdesk_id,
        "alias": device.alias,
        "hostname": device.hostname,
        "platform": device.platform,
        "architecture": device.architecture,
        "agent_version": device.agent_version,
        "rustdesk_version": device.rustdesk_version,
        "tags": device.tags or [],
        "metadata": device.metadata_json or {},
        "last_ip": device.last_ip,
        "last_seen": aware(device.last_seen),
        "created_at": aware(device.created_at),
        "updated_at": aware(device.updated_at),
        "revoked_at": aware(device.revoked_at),
        "credential_rotation_pending": device.credential_rotation_requested_at is not None,
        "online": online,
        "connect_uri": f"sarmiento://connect/{device.rustdesk_id}",
    }


def list_devices(session: Session) -> list[Device]:
    return list(session.scalars(select(Device).order_by(Device.alias.asc())).all())


def get_device(session: Session, device_id: str) -> Device:
    device = session.get(Device, device_id)
    if not device:
        raise NotFoundError("Device not found")
    return device


def update_device(
    session: Session,
    *,
    device: Device,
    alias: str | None,
    tags: list[str] | None,
    owner: Owner,
    source_ip: str | None,
) -> Device:
    changed: dict[str, Any] = {}
    if alias is not None and alias != device.alias:
        changed["alias"] = {"from": device.alias, "to": alias}
        device.alias = alias
    if tags is not None and tags != (device.tags or []):
        changed["tags"] = {"from": device.tags or [], "to": tags}
        device.tags = tags
    if changed:
        audit(
            session,
            actor_type="owner",
            actor_id=owner.id,
            action="device.updated",
            target_type="device",
            target_id=device.id,
            source_ip=source_ip,
            details=changed,
        )
        session.commit()
        session.refresh(device)
    return device


def revoke_device(
    session: Session,
    *,
    device: Device,
    owner: Owner,
    source_ip: str | None,
    now: datetime | None = None,
) -> Device:
    if device.revoked_at is None:
        device.revoked_at = now or datetime.now(UTC)
        device.pending_token_hash = None
        device.credential_rotation_nonce = None
        device.credential_rotation_requested_at = None
        audit(
            session,
            actor_type="owner",
            actor_id=owner.id,
            action="device.revoked",
            target_type="device",
            target_id=device.id,
            source_ip=source_ip,
        )
        session.commit()
        session.refresh(device)
    return device


def request_agent_token_rotation(
    session: Session,
    *,
    device: Device,
    owner: Owner,
    source_ip: str | None,
    now: datetime | None = None,
) -> Device:
    if device.revoked_at is not None:
        raise ConflictError("Cannot rotate credentials for a revoked device")
    if device.credential_rotation_requested_at is None:
        device.credential_rotation_requested_at = now or datetime.now(UTC)
        device.credential_rotation_nonce = generate_token("nonce")
        device.pending_token_hash = None
        audit(
            session,
            actor_type="owner",
            actor_id=owner.id,
            action="device.credential_rotation_requested",
            target_type="device",
            target_id=device.id,
            source_ip=source_ip,
        )
        session.commit()
        session.refresh(device)
    return device


def prepare_agent_token_rotation(
    session: Session,
    *,
    device: Device,
    settings: Settings,
    source_ip: str | None,
) -> str:
    locked = session.scalar(
        select(Device)
        .where(Device.id == device.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not locked or locked.revoked_at is not None:
        raise ConflictError("Cannot rotate credentials for a revoked device")
    if not locked.credential_rotation_requested_at or not locked.credential_rotation_nonce:
        raise ConflictError("Credential rotation was not requested")

    raw = derive_token(
        "sat",
        subject=locked.id,
        nonce=locked.credential_rotation_nonce,
        pepper=settings.effective_token_pepper,
    )
    digest = hash_token(raw, settings.effective_token_pepper)
    if locked.pending_token_hash != digest:
        locked.pending_token_hash = digest
        audit(
            session,
            actor_type="agent",
            actor_id=locked.id,
            action="device.credential_rotation_issued",
            target_type="device",
            target_id=locked.id,
            source_ip=source_ip,
        )
        session.commit()
    return raw


def list_audit_events(session: Session, limit: int) -> list[AuditEvent]:
    return list(
        session.scalars(select(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(limit)).all()
    )
