from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DevicePresence:
    last_seen: datetime | None
    revoked_at: datetime | None = None

    def is_online(self, now: datetime, threshold_seconds: int) -> bool:
        if self.revoked_at is not None or self.last_seen is None:
            return False
        elapsed = (now - self.last_seen).total_seconds()
        return 0 <= elapsed < threshold_seconds


@dataclass(frozen=True, slots=True)
class EnrollmentWindow:
    expires_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None

    def is_valid(self, now: datetime) -> bool:
        return self.used_at is None and self.revoked_at is None and now < self.expires_at
