from argon2 import PasswordHasher

from app import auth
from app.db import connect, initialize


def create_user(password: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO users(username, password_hash) VALUES(?, ?)",
            ("king", PasswordHasher().hash(password)),
        )


def test_change_password_rejects_wrong_current_password(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "auth.db"))
    auth.get_settings.cache_clear()
    initialize()
    create_user("old-password")

    assert auth.change_password("king", "wrong-password", "new-password") is False
    assert auth.verify_login("king", "old-password", "correct-old-client") is True
    auth.get_settings.cache_clear()


def test_change_password_updates_hash(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "auth.db"))
    auth.get_settings.cache_clear()
    initialize()
    create_user("old-password")

    assert auth.change_password("king", "old-password", "new-password") is True
    assert auth.verify_login("king", "old-password", "rejected-old-client") is False
    assert auth.verify_login("king", "new-password", "accepted-new-client") is True
    auth.get_settings.cache_clear()
