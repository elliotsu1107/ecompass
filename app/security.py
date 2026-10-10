"""管理员凭据存储与会话签名。

凭据：PBKDF2-HMAC-SHA256 哈希，存 data/admin.json。
会话：cookie 为「用户名:过期时间戳:HMAC 签名」，密钥存 data/secret.key。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "ecompass123"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
MIN_PASSWORD_LENGTH = 8

_ITERATIONS = 120_000


class PasswordError(ValueError):
    """密码不满足强度要求或校验失败。"""


def ensure_secret_key(path: Path) -> bytes:
    """读取会话签名密钥，不存在则生成 32 字节随机密钥并写入。"""
    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        if raw:
            try:
                return bytes.fromhex(raw)
            except ValueError:
                pass
    key = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key.hex(), encoding="utf-8")
    return key


def validate_password(password: str) -> None:
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordError(f"密码长度至少 {MIN_PASSWORD_LENGTH} 位")
    if not any(char.isalpha() for char in password):
        raise PasswordError("密码需包含字母")
    if not any(char.isdigit() for char in password):
        raise PasswordError("密码需包含数字")


def _digest(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS
    ).hex()


class CredentialStore:
    """管理员账号凭据，持久化在 data/admin.json。"""

    def __init__(
        self,
        path: Path,
        username: str = DEFAULT_USERNAME,
        default_password: str = DEFAULT_PASSWORD,
    ) -> None:
        self.path = path
        self.username = username
        self._users = self._read()
        if username not in self._users:
            self._users[username] = self._entry(default_password)
            self._write()

    def _read(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._users, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @staticmethod
    def _entry(password: str) -> dict[str, str]:
        salt = secrets.token_hex(16)
        return {"salt": salt, "hash": _digest(password, salt)}

    def has(self, username: str) -> bool:
        return username in self._users

    def verify(self, username: str, password: str) -> bool:
        entry = self._users.get(username)
        if not entry:
            return False
        try:
            expected = entry["hash"]
            salt = entry["salt"]
        except KeyError:
            return False
        return hmac.compare_digest(_digest(password, salt), expected)

    def set_password(self, username: str, password: str) -> None:
        validate_password(password)
        self._users[username] = self._entry(password)
        self._write()


def issue_session(username: str, key: bytes) -> str:
    expires = int(
        (datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL_SECONDS)).timestamp()
    )
    return _sign(f"{username}:{expires}", key)


def _sign(payload: str, key: bytes) -> str:
    signature = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def verify_session(
    cookie: str | None,
    key: bytes,
    known: Callable[[str], bool] | None = None,
) -> str | None:
    """校验签名 Cookie，返回用户名；无效或过期返回 None。"""
    if not cookie:
        return None
    parts = cookie.split(":")
    if len(parts) != 3:
        return None
    username, expires, signature = parts
    payload = f"{username}:{expires}"
    expected = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        if int(expires) < datetime.now(timezone.utc).timestamp():
            return None
    except ValueError:
        return None
    if known is not None and not known(username):
        return None
    return username
