from datetime import UTC, datetime, timedelta

from sarmiento.domain import DevicePresence, EnrollmentWindow


def test_device_presence_rules():
    now = datetime(2026, 7, 12, 12, tzinfo=UTC)
    assert DevicePresence(now - timedelta(seconds=30)).is_online(now, 90)
    assert not DevicePresence(now - timedelta(seconds=120)).is_online(now, 90)
    assert not DevicePresence(None).is_online(now, 90)
    assert not DevicePresence(now, revoked_at=now).is_online(now, 90)


def test_enrollment_window_rules():
    now = datetime(2026, 7, 12, 12, tzinfo=UTC)
    assert EnrollmentWindow(now + timedelta(minutes=1)).is_valid(now)
    assert not EnrollmentWindow(now).is_valid(now)
    assert not EnrollmentWindow(now + timedelta(minutes=1), used_at=now).is_valid(now)
    assert not EnrollmentWindow(now + timedelta(minutes=1), revoked_at=now).is_valid(now)
