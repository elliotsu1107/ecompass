import sqlite3

from app.auth import authenticate_admin, require_admin


def test_authenticate_admin_uses_admin_cookie_secret():
    assert authenticate_admin("admin", "secret", {"admin": "secret"}) == "admin"
    assert authenticate_admin("admin", "bad", {"admin": "secret"}) is None


def test_require_admin_rejects_missing_cookie():
    assert require_admin(None, {"admin": "secret"}) is False
    assert require_admin("admin", {"admin": "secret"}) is True
