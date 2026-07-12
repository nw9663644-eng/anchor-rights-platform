from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException

from app.storage import _connect, _now, _param


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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        email = os.getenv("ADMIN_EMAIL", "admin@anchor-rights.local").strip().lower()
        password = os.getenv("ADMIN_PASSWORD", "ChangeMe-2026!")
        exists = conn.execute(_param("SELECT id FROM users WHERE email = ?"), (email,)).fetchone()
        if not exists:
            conn.execute(
                _param("INSERT INTO users (id,email,name,password_hash,role,created_at) VALUES (?,?,?,?,?,?)"),
                (secrets.token_hex(16), email, "平台管理员", _hash_password(password), "admin", _now()),
            )
        elif os.getenv("ADMIN_PASSWORD"):
            conn.execute(_param("UPDATE users SET password_hash=?, role='admin' WHERE email=?"), (_hash_password(password), email))
        conn.commit()


def register_user(email: str, name: str, password: str) -> dict:
    normalized = email.strip().lower()
    if "@" not in normalized or len(password) < 8:
        raise ValueError("请输入有效邮箱，密码至少 8 位。")
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


def create_session(email: str, password: str) -> dict:
    with _connect() as conn:
        row = conn.execute(_param("SELECT * FROM users WHERE email = ?"), (email.strip().lower(),)).fetchone()
        if not row or not _verify_password(password, row["password_hash"]):
            raise ValueError("邮箱或密码错误。")
        token = secrets.token_urlsafe(36)
        expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
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


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先登录。")
    token = authorization[7:]
    with _connect() as conn:
        row = conn.execute(_param("SELECT u.* , s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?"), (_token_hash(token),)).fetchone()
    if not row or datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录。")
    return {"id": row["id"], "email": row["email"], "name": row["name"], "role": row["role"]}


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限。")
    return user
