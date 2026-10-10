"""管理员凭据与会话签名。"""

from pathlib import Path

from app.security import (
    DEFAULT_PASSWORD,
    DEFAULT_USERNAME,
    CredentialStore,
    PasswordError,
    ensure_secret_key,
    issue_session,
    validate_password,
    verify_session,
)


def login_headers(client, password=DEFAULT_PASSWORD):
    response = client.post(
        "/login",
        data={"username": DEFAULT_USERNAME, "password": password},
        follow_redirects=False,
    )
    return {"Cookie": f"admin_session={response.cookies['admin_session']}"}


def test_secret_key_is_created_and_reused(tmp_path):
    path = tmp_path / "secret.key"

    first = ensure_secret_key(path)
    second = ensure_secret_key(path)

    assert len(first) == 32
    assert first == second


def test_validate_password_requires_length_letter_and_digit():
    validate_password("abcd1234")

    for weak in ("short1", "allletters", "12345678", ""):
        try:
            validate_password(weak)
        except PasswordError:
            continue
        raise AssertionError(f"{weak!r} should be rejected")


def test_credential_store_defaults_and_password_change(tmp_path):
    store = CredentialStore(tmp_path / "admin.json")

    assert store.verify(DEFAULT_USERNAME, DEFAULT_PASSWORD)
    assert not store.verify(DEFAULT_USERNAME, "wrong-password")

    store.set_password(DEFAULT_USERNAME, "newpass123")

    assert store.verify(DEFAULT_USERNAME, "newpass123")
    assert not store.verify(DEFAULT_USERNAME, DEFAULT_PASSWORD)


def test_credential_store_persists_across_instances(tmp_path):
    path = tmp_path / "admin.json"
    CredentialStore(path).set_password("admin", "persisted123")

    assert CredentialStore(path).verify("admin", "persisted123")


def test_session_cookie_is_signed_and_expiry_checked():
    key = b"0" * 32
    cookie = issue_session("admin", key)

    assert verify_session(cookie, key, lambda name: name == "admin") == "admin"
    assert verify_session(cookie, b"1" * 32, lambda name: True) is None
    assert verify_session("admin", key, lambda name: True) is None
    assert verify_session(None, key, lambda name: True) is None
    assert verify_session("admin:1:deadbeef", key, lambda name: True) is None
    assert verify_session(cookie, key, lambda name: False) is None


def test_change_password_rejects_bad_input_then_accepts(client):
    headers = login_headers(client)

    assert client.post(
        "/api/admin/password",
        json={"current_password": "wrong", "new_password": "abcd1234", "confirm_password": "abcd1234"},
        headers=headers,
    ).status_code == 400

    assert client.post(
        "/api/admin/password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "abcd1234", "confirm_password": "abcd9999"},
        headers=headers,
    ).status_code == 400

    assert client.post(
        "/api/admin/password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "short1", "confirm_password": "short1"},
        headers=headers,
    ).status_code == 400

    assert client.post(
        "/api/admin/password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": DEFAULT_PASSWORD, "confirm_password": DEFAULT_PASSWORD},
        headers=headers,
    ).status_code == 400

    response = client.post(
        "/api/admin/password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "ecompass456", "confirm_password": "ecompass456"},
        headers=headers,
    )
    assert response.status_code == 200

    assert client.post("/login", data={"username": "admin", "password": "ecompass456"}, follow_redirects=False).status_code == 303
    assert client.post("/login", data={"username": "admin", "password": DEFAULT_PASSWORD}, follow_redirects=False).status_code == 401


def test_change_password_requires_login(client):
    response = client.post(
        "/api/admin/password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "abcd1234", "confirm_password": "abcd1234"},
    )

    assert response.status_code == 401


def test_forged_cookie_is_rejected(client, app_config):
    response = client.get("/api/admin/stores", headers={"Cookie": "admin_session=admin"})

    assert response.status_code == 401


def test_runtime_files_live_in_data_dir(client, app_config):
    assert (Path(app_config.data_dir) / "secret.key").exists()
    assert (Path(app_config.data_dir) / "admin.json").exists()
