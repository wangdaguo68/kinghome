import os

from app.db import consume_quota, ensure_user


def test_anonymous_user_gets_daily_quota(tmp_path) -> None:
    os.environ["APP_DB_PATH"] = str(tmp_path / "app.db")

    profile = ensure_user("test-user")

    assert profile["user_id"] == "test-user"
    assert profile["quota_remaining"] == 5
    assert len(profile["recovery_code"]) == 6


def test_quota_consumes_until_empty(tmp_path) -> None:
    os.environ["APP_DB_PATH"] = str(tmp_path / "app.db")

    remaining = None
    for _ in range(5):
        allowed, remaining = consume_quota("quota-user")
        assert allowed

    assert remaining == 0
    allowed, remaining = consume_quota("quota-user")
    assert not allowed
    assert remaining == 0
