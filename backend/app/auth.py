from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, Header, HTTPException

from app.storage import _connect, _ensure_column, _now, _param


MAX_LOGIN_ATTEMPTS = min(max(int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")), 3), 10)
LOCKOUT_MINUTES = min(max(int(os.getenv("LOCKOUT_MINUTES", "15")), 5), 60)
SESSION_HOURS = min(max(int(os.getenv("SESSION_HOURS", "12")), 1), 168)


class LoginLockedError(ValueError):
    def __init__(self, seconds: int):
        self.seconds = max(seconds, 1)
        super().__init__(f"账号已临时锁定，请约 {max(1, (self.seconds + 59) // 60)} 分钟后再试。")


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 210_000)
    return f"{salt}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        salt, _ = encoded.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(_hash_password(password, salt), encoded)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def init_auth() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                password_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL
            )
        """)
        _ensure_column(conn, "users", "failed_login_attempts", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "users", "locked_until", "TEXT")
        _ensure_column(conn, "users", "last_failed_at", "TEXT")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        identifier = os.getenv("ADMIN_USERNAME", os.getenv("ADMIN_EMAIL", "admin12")).strip().lower()
        configured_password = os.getenv("ADMIN_PASSWORD")
        password = configured_password or "2026lhzp"
        existing_identifier = conn.execute(
            _param("SELECT id, role FROM users WHERE email = ?"), (identifier,)
        ).fetchone()
        existing_admin = conn.execute(
            "SELECT id, email FROM users WHERE role='admin' ORDER BY created_at LIMIT 1"
        ).fetchone()

        if existing_identifier and existing_identifier["role"] != "admin":
            raise RuntimeError("管理员账号与现有普通用户账号冲突，请更换 ADMIN_USERNAME。")
        if existing_identifier:
            conn.execute(
                _param("UPDATE users SET name=?, role='admin' WHERE id=?"),
                ("平台管理员", existing_identifier["id"]),
            )
            if configured_password:
                conn.execute(
                    _param("UPDATE users SET password_hash=? WHERE id=?"),
                    (_hash_password(password), existing_identifier["id"]),
                )
        elif existing_admin:
            conn.execute(
                _param("UPDATE users SET email=?, name=?, password_hash=?, role='admin' WHERE id=?"),
                (identifier, "平台管理员", _hash_password(password), existing_admin["id"]),
            )
        else:
            conn.execute(
                _param("INSERT INTO users (id,email,name,password_hash,role,created_at) VALUES (?,?,?,?,?,?)"),
                (secrets.token_hex(16), identifier, "平台管理员", _hash_password(password), "admin", _now()),
            )
        conn.commit()


def register_user(email: str, name: str, password: str) -> dict:
    normalized = email.strip().lower()
    if "@" not in normalized:
        raise ValueError("请输入有效邮箱。")
    if len(password) < 10 or not any(char.isalpha() for char in password) or not any(char.isdigit() for char in password):
        raise ValueError("密码至少 10 位，并同时包含字母和数字。")
    user_id = secrets.token_hex(16)
    try:
        with _connect() as conn:
            conn.execute(
                _param("INSERT INTO users (id,email,name,password_hash,role,created_at) VALUES (?,?,?,?,?,?)"),
                (user_id, normalized, name.strip() or "平台用户", _hash_password(password), "user", _now()),
            )
            conn.commit()
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise ValueError("该邮箱已注册。") from exc
        raise
    return create_session(normalized, password)


def create_session(email: str, password: str, expected_role: str | None = None) -> dict:
    with _connect() as conn:
        row = conn.execute(_param("SELECT * FROM users WHERE email = ?"), (email.strip().lower(),)).fetchone()
        now = datetime.now(timezone.utc)
        if row and row["locked_until"]:
            locked_until = datetime.fromisoformat(row["locked_until"])
            if locked_until > now:
                raise LoginLockedError(int((locked_until - now).total_seconds()))
        if not row or not _verify_password(password, row["password_hash"]):
            if row:
                failures = int(row["failed_login_attempts"] or 0) + 1
                locked_until = None
                if failures >= MAX_LOGIN_ATTEMPTS:
                    locked_until = (now + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
                conn.execute(
                    _param("UPDATE users SET failed_login_attempts=?, locked_until=?, last_failed_at=? WHERE id=?"),
                    (failures, locked_until, _now(), row["id"]),
                )
                conn.commit()
                if locked_until:
                    raise LoginLockedError(LOCKOUT_MINUTES * 60)
            raise ValueError("邮箱或密码错误。")
        if expected_role in {"admin", "user"} and row["role"] != expected_role:
            portal_name = "管理员入口" if expected_role == "admin" else "普通用户入口"
            raise ValueError(f"该账号不能从{portal_name}登录。")
        token = secrets.token_urlsafe(36)
        expires = (now + timedelta(hours=SESSION_HOURS)).isoformat()
        conn.execute(_param("DELETE FROM sessions WHERE expires_at < ?"), (now.isoformat(),))
        conn.execute(_param("UPDATE users SET failed_login_attempts=0, locked_until=NULL, last_failed_at=NULL WHERE id=?"), (row["id"],))
        conn.execute(_param("INSERT INTO sessions (token,user_id,expires_at,created_at) VALUES (?,?,?,?)"), (_token_hash(token), row["id"], expires, _now()))
        conn.commit()
    return {"token": token, "user": {"id": row["id"], "email": row["email"], "name": row["name"], "role": row["role"]}}


def revoke_session(token: str) -> None:
    with _connect() as conn:
        conn.execute(_param("DELETE FROM sessions WHERE token=?"), (_token_hash(token),))
        conn.commit()


def change_password(user_id: str, current_password: str, new_password: str) -> None:
    if len(new_password) < 10:
        raise ValueError("新密码至少 10 位。")
    with _connect() as conn:
        row = conn.execute(_param("SELECT password_hash FROM users WHERE id=?"), (user_id,)).fetchone()
        if not row or not _verify_password(current_password, row["password_hash"]):
            raise ValueError("当前密码错误。")
        conn.execute(_param("UPDATE users SET password_hash=? WHERE id=?"), (_hash_password(new_password), user_id))
        conn.execute(_param("DELETE FROM sessions WHERE user_id=?"), (user_id,))
        conn.commit()


def get_session_token(authorization: str | None, anchor_session: str | None) -> str | None:
    if anchor_session:
        return anchor_session
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def get_current_user(
    authorization: str | None = Header(default=None),
    anchor_session: str | None = Cookie(default=None),
) -> dict:
    token = get_session_token(authorization, anchor_session)
    if not token:
        raise HTTPException(status_code=401, detail="请先登录。")
    with _connect() as conn:
        row = conn.execute(_param("SELECT u.* , s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?"), (_token_hash(token),)).fetchone()
    if not row or datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录。")
    return {"id": row["id"], "email": row["email"], "name": row["name"], "role": row["role"]}


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限。")
    return user
