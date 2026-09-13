from pathlib import Path


def admin_headers(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "ecompass123"},
        follow_redirects=False,
    )
    return {"Cookie": f"admin_session={response.cookies['admin_session']}"}


def test_reset_api_requires_admin(client):
    response = client.post("/api/admin/reset", json={"confirmation": "CLEAR"})

    assert response.status_code == 401


def test_reset_api_get_is_not_a_dimension_endpoint(client, monkeypatch):
    headers = admin_headers(client)

    def unexpected_dimension_list(*args, **kwargs):
        raise AssertionError("GET /api/admin/reset entered list_dimension")

    monkeypatch.setattr(
        "app.web.routes_admin.DimensionStore.list", unexpected_dimension_list
    )

    response = client.get("/api/admin/reset", headers=headers)

    assert response.status_code == 405


def test_reset_api_rejects_confirmation_other_than_clear(client):
    headers = admin_headers(client)

    response = client.post(
        "/api/admin/reset", json={"confirmation": "clear"}, headers=headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "请输入 CLEAR 确认清空"


def test_reset_api_clears_business_data_and_returns_backup_stats(client, app_config):
    headers = admin_headers(client)
    connection = client.app.state.db()
    connection.execute("INSERT INTO stores (name, platform) VALUES (?, ?)", ("旗舰店", "平台"))
    connection.commit()
    connection.close()

    response = client.post(
        "/api/admin/reset", json={"confirmation": "CLEAR"}, headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["before"]["stores"] == 1
    assert body["after"]["stores"] == 0
    assert Path(body["backup_path"]).exists()
    assert Path(body["backup_path"]).parent == app_config.data_dir / "backups"
