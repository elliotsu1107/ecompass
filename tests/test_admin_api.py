def admin_headers(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "ecompass123"},
        follow_redirects=False,
    )
    return {"Cookie": f"admin_session={response.cookies['admin_session']}"}


def create_dimension(client, path, payload):
    headers = admin_headers(client)
    response = client.post(f"/api/admin/{path}", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_admin_endpoints_require_login(client):
    assert client.get("/api/admin/stores").status_code == 401
    assert client.post("/api/admin/stores", json={"name": "A"}).status_code == 401
    assert client.get("/api/admin/targets?month=2026-09").status_code == 401


def test_admin_page_exposes_configuration_sections(client):
    headers = admin_headers(client)
    response = client.get("/admin", headers=headers)

    assert response.status_code == 200
    for section in ("stores", "operators", "categories", "products", "targets"):
        assert f'data-section="{section}"' in response.text


def test_admin_creates_and_lists_stores_operators_categories(client):
    operator_id = create_dimension(client, "operators", {"name": "小王"})
    store_id = create_dimension(client, "stores", {"name": "A店铺", "platform": "淘宝"})
    category_id = create_dimension(
        client, "categories", {"name": "咖啡", "operator_id": operator_id}
    )
    headers = admin_headers(client)

    stores = client.get("/api/admin/stores", headers=headers).json()["items"]
    operators = client.get("/api/admin/operators", headers=headers).json()["items"]
    categories = client.get("/api/admin/categories", headers=headers).json()["items"]

    assert stores == [{"id": store_id, "name": "A店铺", "platform": "淘宝"}]
    assert operators == [{"id": operator_id, "name": "小王"}]
    assert categories == [
        {"id": category_id, "name": "咖啡", "operator_id": operator_id}
    ]


def test_admin_rejects_duplicate_store_name_with_clear_message(client):
    create_dimension(client, "stores", {"name": "A店铺", "platform": "淘宝"})
    headers = admin_headers(client)

    response = client.post(
        "/api/admin/stores",
        json={"name": "A店铺", "platform": "天猫"},
        headers=headers,
    )

    assert response.status_code == 400
    assert "已存在" in response.json()["detail"]


def test_admin_rejects_category_without_operator(client):
    headers = admin_headers(client)

    response = client.post(
        "/api/admin/categories", json={"name": "咖啡"}, headers=headers
    )

    assert response.status_code == 400


def test_admin_targets_roundtrip_for_month(client):
    operator_id = create_dimension(client, "operators", {"name": "小王"})
    store_id = create_dimension(client, "stores", {"name": "A店铺", "platform": "淘宝"})
    category_id = create_dimension(
        client, "categories", {"name": "咖啡", "operator_id": operator_id}
    )
    headers = admin_headers(client)

    assert client.put(
        "/api/admin/targets/store",
        json={"month": "2026-09", "store_id": store_id, "amount": 1000},
        headers=headers,
    ).status_code == 200
    assert client.put(
        "/api/admin/targets/category",
        json={
            "month": "2026-09",
            "store_id": store_id,
            "category_id": category_id,
            "amount": 600,
        },
        headers=headers,
    ).status_code == 200
    assert client.put(
        "/api/admin/targets/operator",
        json={"month": "2026-09", "operator_id": operator_id, "amount": 900},
        headers=headers,
    ).status_code == 200

    body = client.get("/api/admin/targets?month=2026-09", headers=headers).json()

    assert body["store"] == {str(store_id): 1000.0}
    assert body["category"] == {f"{store_id}:{category_id}": 600.0}
    assert body["operator"] == {str(operator_id): 900.0}


def test_admin_rejects_unknown_target_scope(client):
    headers = admin_headers(client)

    response = client.put(
        "/api/admin/targets/unknown", json={"month": "2026-09"}, headers=headers
    )

    assert response.status_code == 400


def test_admin_creates_product_for_category_matching(client):
    operator_id = create_dimension(client, "operators", {"name": "小王"})
    store_id = create_dimension(client, "stores", {"name": "A店铺", "platform": "淘宝"})
    category_id = create_dimension(
        client, "categories", {"name": "咖啡", "operator_id": operator_id}
    )
    headers = admin_headers(client)

    response = client.post(
        "/api/admin/products",
        json={
            "store_id": store_id,
            "product_id": "A100",
            "name": "咖啡豆",
            "category_id": category_id,
            "operator_id": operator_id,
        },
        headers=headers,
    )

    assert response.status_code == 200
    items = client.get("/api/admin/products", headers=headers).json()["items"]
    assert items == [{
        "store_id": store_id,
        "product_id": "A100",
        "name": "咖啡豆",
        "category_id": category_id,
        "operator_id": operator_id,
    }]


def test_import_page_offers_store_report_and_store_list(client):
    headers = admin_headers(client)
    response = client.get("/import", headers=headers)

    assert response.status_code == 200
    assert 'value="store"' in response.text
    assert 'id="store-select"' in response.text


def test_import_logs_endpoint_returns_recent_records(client):
    headers = admin_headers(client)
    connection = client.app.state.db()
    connection.execute(
        "INSERT INTO import_logs (created_at, file_type, file_name, file_sha256, data_date,"
        " inserted_rows, updated_rows, skipped_rows, unmatched_rows, archive_path)"
        " VALUES ('2026-09-05T00:00:00', 'store', 'A.xlsx', 'abc', '2026-09-05', 3, 0, 0, 0, 'p')"
    )
    connection.commit()
    connection.close()

    response = client.get("/api/import/logs", headers=headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["file_name"] == "A.xlsx"
    assert items[0]["inserted_rows"] == 3
