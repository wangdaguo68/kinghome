import base64
import hashlib
import hmac
import json
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request, status

from .config import get_settings
from .db import connect


COOKIE_NAME = "km_session"
_ph = PasswordHasher()
_attempts: dict[str, deque[float]] = defaultdict(deque)


def ensure_admin() -> None:
    settings = get_settings()
    with connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE username=?", (settings.admin_username,)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO users(username, password_hash) VALUES(?,?)",
                (settings.admin_username, _ph.hash(settings.admin_password)),
            )


def _limited(key: str) -> bool:
    now = time.time()
    attempts = _attempts[key]
    while attempts and attempts[0] < now - 600:
        attempts.popleft()
    return len(attempts) >= 5


def verify_login(username: str, password: str, client: str) -> bool:
    key = f"{client}:{username}"
    if _limited(key):
        raise HTTPException(status_code=429, detail="登录失败次数过多，请稍后再试")
    with connect() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        _attempts[key].append(time.time())
        return False
    try:
        ok = _ph.verify(row["password_hash"], password)
    except VerifyMismatchError:
        ok = False
    if ok:
        _attempts.pop(key, None)
    else:
        _attempts[key].append(time.time())
    return ok


def change_password(username: str, current_password: str, new_password: str) -> bool:
    with connect() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return False
        try:
            _ph.verify(row["password_hash"], current_password)
        except VerifyMismatchError:
            return False
        conn.execute(
            "UPDATE users SET password_hash=? WHERE username=?",
            (_ph.hash(new_password), username),
        )
    return True


def create_session(username: str) -> str:
    settings = get_settings()
    payload = {"sub": username, "exp": int(time.time()) + settings.session_hours * 3600}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(settings.app_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def parse_session(token: str) -> str | None:
    try:
        body, signature = token.rsplit(".", 1)
        expected = hmac.new(get_settings().app_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        if int(payload["exp"]) < int(time.time()):
            return None
        return str(payload["sub"])
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def require_user(request: Request) -> str:
    username = parse_session(request.cookies.get(COOKIE_NAME, ""))
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return username
