from __future__ import annotations

import hmac
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import __version__
from .config import Settings
from .models import Device, EnrollmentToken, Owner
from .schemas import (
    AgentEnrollRequest,
    AgentEnrollResponse,
    AgentTokenRotationResponse,
    AuditEventView,
    DeviceUpdate,
    DeviceView,
    EnrollmentTokenCreate,
    EnrollmentTokenIssued,
    EnrollmentTokenView,
    HeartbeatRequest,
    HeartbeatResponse,
    LoginRequest,
    OwnerView,
    PasswordChangeRequest,
    PublicConfigView,
    StatsView,
)
from .security import (
    DUMMY_PASSWORD_HASH,
    decode_session_token,
    generate_csrf_token,
    issue_session_token,
    verify_password,
)
from .services import (
    AuthenticationError,
    audit,
    authenticate_agent,
    change_owner_password,
    create_enrollment_token,
    device_to_view,
    enroll_device,
    enrollment_status,
    get_device,
    list_audit_events,
    list_devices,
    prepare_agent_token_rotation,
    record_heartbeat,
    request_agent_token_rotation,
    revoke_device,
    revoke_enrollment_token,
    update_device,
)

router = APIRouter(prefix="/api/v1")
bearer = HTTPBearer(auto_error=False)


def settings_for(request: Request) -> Settings:
    return request.app.state.settings


def db_for(request: Request):
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


Db = Annotated[Session, Depends(db_for)]
SettingsDep = Annotated[Settings, Depends(settings_for)]


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def require_owner(request: Request, db: Db, settings: SettingsDep) -> Owner:
    raw = request.cookies.get("sarmiento_session")
    if not raw:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_session_token(raw, settings.session_secret)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc
    owner = db.get(Owner, str(payload["sub"]))
    if not owner:
        raise HTTPException(status_code=401, detail="Session owner no longer exists")
    if int(payload.get("session_version", 0)) != owner.session_version:
        raise HTTPException(status_code=401, detail="Session has been invalidated")
    if settings.csrf_enabled and request.method not in {"GET", "HEAD", "OPTIONS"}:
        cookie_token = request.cookies.get("sarmiento_csrf", "")
        header_token = request.headers.get("x-sarmiento-csrf", "")
        if not cookie_token or not hmac.compare_digest(cookie_token, header_token):
            raise HTTPException(status_code=403, detail="CSRF validation failed")
    return owner


OwnerDep = Annotated[Owner, Depends(require_owner)]


def require_agent(
    request: Request,
    db: Db,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Device:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Agent bearer token required")
    try:
        return authenticate_agent(
            db, credentials.credentials, settings, source_ip=client_ip(request)
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


AgentDep = Annotated[Device, Depends(require_agent)]


@router.post("/auth/login", response_model=OwnerView)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Db,
    settings: SettingsDep,
):
    owner = db.scalar(select(Owner).where(Owner.username == payload.username))
    password_hash = owner.password_hash if owner else DUMMY_PASSWORD_HASH
    password_valid = verify_password(payload.password, password_hash)
    if not owner or not password_valid:
        audit(
            db,
            actor_type="anonymous",
            actor_id=None,
            action="auth.login_failed",
            source_ip=client_ip(request),
            details={"username": payload.username},
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = issue_session_token(
        user_id=owner.id,
        username=owner.username,
        session_version=owner.session_version,
        secret=settings.session_secret,
        ttl_minutes=settings.session_ttl_minutes,
    )
    csrf = generate_csrf_token()
    max_age = settings.session_ttl_minutes * 60
    response.set_cookie(
        "sarmiento_session",
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        "sarmiento_csrf",
        csrf,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    audit(
        db,
        actor_type="owner",
        actor_id=owner.id,
        action="auth.login_succeeded",
        source_ip=client_ip(request),
    )
    db.commit()
    return OwnerView(id=owner.id, username=owner.username)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: Db, owner: OwnerDep):
    audit(
        db,
        actor_type="owner",
        actor_id=owner.id,
        action="auth.logout",
        source_ip=client_ip(request),
    )
    db.commit()
    response.delete_cookie("sarmiento_session", path="/")
    response.delete_cookie("sarmiento_csrf", path="/")


@router.get("/auth/me", response_model=OwnerView)
def me(owner: OwnerDep):
    return OwnerView(id=owner.id, username=owner.username)


@router.post("/auth/change-password", status_code=204)
def password_change(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    db: Db,
    owner: OwnerDep,
):
    change_owner_password(
        db,
        owner=owner,
        current_password=payload.current_password,
        new_password=payload.new_password,
        source_ip=client_ip(request),
    )
    response.delete_cookie("sarmiento_session", path="/")
    response.delete_cookie("sarmiento_csrf", path="/")


@router.get("/config/public", response_model=PublicConfigView)
def public_config(settings: SettingsDep):
    return PublicConfigView(
        version=__version__,
        rustdesk_server=settings.rustdesk_server,
        rustdesk_key=settings.resolved_rustdesk_key,
        presence_threshold_seconds=settings.presence_threshold_seconds,
    )


@router.post("/enrollment-tokens", response_model=EnrollmentTokenIssued, status_code=201)
def issue_enrollment_token(
    payload: EnrollmentTokenCreate,
    request: Request,
    db: Db,
    settings: SettingsDep,
    owner: OwnerDep,
):
    record, raw = create_enrollment_token(
        db,
        owner=owner,
        settings=settings,
        label=payload.label.strip(),
        ttl_minutes=payload.ttl_minutes,
        source_ip=client_ip(request),
    )
    return EnrollmentTokenIssued(
        id=record.id, token=raw, label=record.label, expires_at=record.expires_at
    )


@router.get("/enrollment-tokens", response_model=list[EnrollmentTokenView])
def get_enrollment_tokens(db: Db, owner: OwnerDep):
    del owner
    now = datetime.now(UTC)
    records = list(
        db.scalars(select(EnrollmentToken).order_by(EnrollmentToken.created_at.desc()).limit(100))
    )
    return [
        EnrollmentTokenView(
            id=item.id,
            label=item.label,
            created_at=item.created_at,
            expires_at=item.expires_at,
            used_at=item.used_at,
            revoked_at=item.revoked_at,
            status=enrollment_status(item, now),
        )
        for item in records
    ]


@router.delete("/enrollment-tokens/{token_id}", response_model=EnrollmentTokenView)
def delete_enrollment_token(
    token_id: str,
    request: Request,
    db: Db,
    owner: OwnerDep,
):
    item = revoke_enrollment_token(db, token_id=token_id, owner=owner, source_ip=client_ip(request))
    return EnrollmentTokenView(
        id=item.id,
        label=item.label,
        created_at=item.created_at,
        expires_at=item.expires_at,
        used_at=item.used_at,
        revoked_at=item.revoked_at,
        status=enrollment_status(item, datetime.now(UTC)),
    )


@router.post("/agents/enroll", response_model=AgentEnrollResponse, status_code=201)
def agent_enroll(
    payload: AgentEnrollRequest,
    request: Request,
    db: Db,
    settings: SettingsDep,
):
    device, raw_agent_token = enroll_device(
        db,
        settings=settings,
        payload=payload,
        source_ip=client_ip(request),
    )
    return AgentEnrollResponse(
        device_id=device.id,
        agent_token=raw_agent_token,
        heartbeat_interval_seconds=30,
        rustdesk_server=settings.rustdesk_server,
        rustdesk_key=settings.resolved_rustdesk_key,
    )


@router.post("/agents/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    payload: HeartbeatRequest,
    request: Request,
    db: Db,
    device: AgentDep,
):
    moment = datetime.now(UTC)
    record_heartbeat(
        db,
        device=device,
        payload=payload,
        source_ip=client_ip(request),
        now=moment,
    )
    return HeartbeatResponse(
        server_time=moment,
        next_heartbeat_seconds=30,
        credential_rotation_required=device.credential_rotation_requested_at is not None,
    )


@router.post("/agents/rotate-token", response_model=AgentTokenRotationResponse)
def agent_rotate_token(
    request: Request,
    db: Db,
    settings: SettingsDep,
    device: AgentDep,
):
    raw = prepare_agent_token_rotation(
        db,
        device=device,
        settings=settings,
        source_ip=client_ip(request),
    )
    return AgentTokenRotationResponse(agent_token=raw)


@router.get("/devices", response_model=list[DeviceView])
def devices(db: Db, settings: SettingsDep, owner: OwnerDep, include_revoked: bool = False):
    del owner
    records = list_devices(db)
    if not include_revoked:
        records = [record for record in records if record.revoked_at is None]
    now = datetime.now(UTC)
    return [DeviceView(**device_to_view(record, settings, now)) for record in records]


@router.get("/devices/{device_id}", response_model=DeviceView)
def device_detail(device_id: str, db: Db, settings: SettingsDep, owner: OwnerDep):
    del owner
    return DeviceView(**device_to_view(get_device(db, device_id), settings))


@router.patch("/devices/{device_id}", response_model=DeviceView)
def patch_device(
    device_id: str,
    payload: DeviceUpdate,
    request: Request,
    db: Db,
    settings: SettingsDep,
    owner: OwnerDep,
):
    device = update_device(
        db,
        device=get_device(db, device_id),
        alias=payload.alias,
        tags=payload.tags,
        owner=owner,
        source_ip=client_ip(request),
    )
    return DeviceView(**device_to_view(device, settings))


@router.post("/devices/{device_id}/revoke", response_model=DeviceView)
def revoke(
    device_id: str,
    request: Request,
    db: Db,
    settings: SettingsDep,
    owner: OwnerDep,
):
    device = revoke_device(
        db,
        device=get_device(db, device_id),
        owner=owner,
        source_ip=client_ip(request),
    )
    return DeviceView(**device_to_view(device, settings))


@router.post("/devices/{device_id}/rotate-token", response_model=DeviceView)
def request_token_rotation(
    device_id: str,
    request: Request,
    db: Db,
    settings: SettingsDep,
    owner: OwnerDep,
):
    device = request_agent_token_rotation(
        db,
        device=get_device(db, device_id),
        owner=owner,
        source_ip=client_ip(request),
    )
    return DeviceView(**device_to_view(device, settings))


@router.get("/audit", response_model=list[AuditEventView])
def audit_log(
    db: Db,
    owner: OwnerDep,
    limit: int = Query(default=100, ge=1, le=500),
):
    del owner
    return [AuditEventView.model_validate(item) for item in list_audit_events(db, limit)]


@router.get("/stats", response_model=StatsView)
def stats(db: Db, settings: SettingsDep, owner: OwnerDep):
    del owner
    now = datetime.now(UTC)
    records = list_devices(db)
    active = [item for item in records if item.revoked_at is None]
    online = sum(1 for item in active if device_to_view(item, settings, now)["online"])
    return StatsView(
        total_devices=len(active),
        online_devices=online,
        offline_devices=len(active) - online,
        revoked_devices=len(records) - len(active),
        server_time=now,
    )
