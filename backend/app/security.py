from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


KEY_PATH = Path(__file__).resolve().parent.parent / ".data_key"

_SENSITIVE_PATTERNS = (
    (re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), "[身份证号已脱敏]"),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[手机号已脱敏]"),
    (re.compile(r"(?<!\d)\d{16,19}(?!\d)"), "[银行卡号已脱敏]"),
    (re.compile(r"(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![A-Z0-9.-])", re.IGNORECASE), "[邮箱已脱敏]"),
)


def redact_sensitive_text(text: str) -> tuple[str, int]:
    redacted = text
    total = 0
    for pattern, replacement in _SENSITIVE_PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        total += count
    return redacted, total


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _load_or_create_key() -> bytes:
    configured = os.getenv("DATA_ENCRYPTION_KEY", "").strip().encode("ascii")
    if configured:
        return configured
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes().strip()
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key + b"\n")
    try:
        KEY_PATH.chmod(0o600)
    except OSError:
        pass
    return key


def encrypt_evidence(content: bytes) -> bytes:
    return Fernet(_load_or_create_key()).encrypt(content)


def decrypt_evidence(content: bytes) -> bytes:
    try:
        return Fernet(_load_or_create_key()).decrypt(content)
    except InvalidToken as exc:
        raise RuntimeError("证据文件密钥不匹配或文件完整性校验失败。") from exc


def evidence_encryption_ready() -> bool:
    try:
        Fernet(_load_or_create_key())
        return True
    except (ValueError, OSError):
        return False


def file_signature_allowed(filename: str, content: bytes) -> bool:
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        return content.startswith(b"%PDF-")
    if extension in {".png"}:
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if extension in {".docx", ".xlsx"}:
        return content.startswith(b"PK\x03\x04")
    if extension in {".doc", ".xls"}:
        return content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if extension in {".txt", ".csv"}:
        return b"\x00" not in content[:4096]
    return False
