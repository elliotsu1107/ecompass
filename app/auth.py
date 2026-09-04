from __future__ import annotations

import hmac
from typing import Mapping

from fastapi import Cookie, HTTPException, Request


def authenticate_admin(username: str, password: str, admins: Mapping[str, str]) -> str | None:
    expected = admins.get(username)
    if expected is not None and hmac.compare_digest(str(expected), str(password)):
        return username
    return None


def require_admin(cookie: str | None, admins: Mapping[str, str]) -> bool:
    return bool(cookie and cookie in admins)


def admin_required(request: Request, admin_session: str | None = Cookie(default=None)) -> str:
    admins = getattr(request.app.state, "admins", {"admin": "admin"})
    if not require_admin(admin_session, admins):
        raise HTTPException(status_code=401, detail="需要管理员登录")
    return admin_session
