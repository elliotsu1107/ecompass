from __future__ import annotations

import hmac
from typing import Mapping

from fastapi import Cookie, HTTPException, Request

from app.security import CredentialStore, verify_session


def authenticate_admin(username: str, password: str, admins: Mapping[str, str]) -> str | None:
    expected = admins.get(username)
    if expected is not None and hmac.compare_digest(str(expected), str(password)):
        return username
    return None


def require_admin(cookie: str | None, admins: Mapping[str, str]) -> bool:
    return bool(cookie and cookie in admins)


def credentials(request: Request) -> CredentialStore | None:
    return getattr(request.app.state, "credentials", None)


def secret_key(request: Request) -> bytes:
    return getattr(request.app.state, "secret_key", b"")


def current_admin(request: Request, cookie: str | None) -> str | None:
    """校验签名 Cookie 并返回用户名；无效或过期返回 None。"""
    store = credentials(request)
    key = secret_key(request)
    if store is None or not key:
        return None
    return verify_session(cookie, key, store.has)


def admin_required(request: Request, admin_session: str | None = Cookie(default=None)) -> str:
    username = current_admin(request, admin_session)
    if not username:
        raise HTTPException(status_code=401, detail="需要管理员登录")
    return username
