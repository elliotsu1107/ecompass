from io import BytesIO

import openpyxl

from app.imports.product_list import import_products


def workbook_bytes(rows):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def login(client):
    return {
        "Cookie": "admin_session="
        + client.post(
            "/login",
            data={"username": "admin", "password": "ecompass123"},
            follow_redirects=False,
        ).cookies["admin_session"]
    }


def test_import_products_creates_operators_categories_and_products(client):
    headers = login(client)
    for name in ("A店铺", "B店铺"):
        client.post(
            "/api/admin/stores", json={"name": name, "platform": "淘宝"}, headers=headers
        )
    payload = workbook_bytes([
        ["店铺名称", "商品ID", "商品名称", "类目", "运营负责人"],
        ["A店铺", 6712345678901, "咖啡豆 500g", "咖啡", "小王"],
        ["A店铺", "6712345678902", "挂耳咖啡", "咖啡", "小王"],
        ["B店铺", 6712345678903, "保温杯", "杯具", "小李"],
    ])

    response = client.post(
        "/api/import/products-list",
        files={"file": ("商品清单.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    stats = response.json()["stats"]
    assert stats["新增"] == 3
    assert stats["新建运营"] == 2
    assert stats["新建类目"] == 2

    categories = client.get("/api/admin/categories", headers=headers).json()["items"]
    operators = client.get("/api/admin/operators", headers=headers).json()["items"]
    products = client.get("/api/admin/products", headers=headers).json()["items"]

    operator_by_name = {item["name"]: item["id"] for item in operators}
    category_by_name = {item["name"]: item["id"] for item in categories}
    assert sorted(operator_by_name) == ["小李", "小王"]
    assert sorted(category_by_name) == ["咖啡", "杯具"]
    assert len(products) == 3
    assert products[0]["product_id"] == "6712345678901"
    assert products[0]["category_id"] == category_by_name["咖啡"]
    assert products[0]["operator_id"] == operator_by_name["小王"]


def test_import_products_reuses_existing_store_and_updates_same_product(client):
    headers = login(client)
    store_id = client.post(
        "/api/admin/stores", json={"name": "A店铺", "platform": "淘宝"}, headers=headers
    ).json()["id"]
    payload = workbook_bytes([
        ["店铺", "商品ID", "商品名称", "类目", "运营"],
        ["A店铺", "P1", "旧名称", "咖啡", "小王"],
    ])
    client.post(
        "/api/import/products-list",
        files={"file": ("商品清单.xlsx", payload, "xlsx")},
        headers=headers,
    )
    payload = workbook_bytes([
        ["店铺", "商品ID", "商品名称", "类目", "运营"],
        ["A店铺", "P1", "新名称", "咖啡", "小王"],
    ])

    response = client.post(
        "/api/import/products-list",
        files={"file": ("商品清单.xlsx", payload, "xlsx")},
        headers=headers,
    )

    assert response.json()["stats"]["更新"] == 1
    products = client.get("/api/admin/products", headers=headers).json()["items"]
    assert len(products) == 1
    assert products[0]["name"] == "新名称"
    assert products[0]["store_id"] == store_id


def test_import_products_reports_unknown_store_and_missing_columns(tmp_path):
    from app.db import connect_db, init_db

    db_path = tmp_path / "data" / "ecompass.db"
    init_db(db_path)
    connection = connect_db(db_path)

    stats = import_products(connection, [
        {"店铺": "不存在的店", "商品ID": "P1", "商品名称": "咖啡豆", "类目": "咖啡", "运营": "小王"},
        {"店铺": "A店铺", "商品ID": "", "商品名称": "缺ID", "类目": "咖啡", "运营": "小王"},
    ])

    assert stats["未匹配店铺"] == 1
    assert stats["跳过"] == 1
    assert stats["新增"] == 0
    assert "不存在的店" in stats["未匹配店铺名称"]


def test_import_products_normalizes_numeric_product_ids(tmp_path):
    from app.db import connect_db, init_db

    db_path = tmp_path / "data" / "ecompass.db"
    init_db(db_path)
    connection = connect_db(db_path)
    connection.execute("INSERT INTO stores (id, name, platform) VALUES (1, 'A店铺', '淘宝')")
    connection.commit()

    stats = import_products(connection, [
        {"店铺": "A店铺", "商品ID": 6712345678901, "商品名称": "咖啡豆", "类目": "咖啡", "运营": "小王"},
        {"店铺": "A店铺", "商品ID": "6712345678902.0", "商品名称": "挂耳", "类目": "咖啡", "运营": "小王"},
    ])

    assert stats["新增"] == 2
    ids = [row[0] for row in connection.execute("SELECT product_id FROM products ORDER BY product_id")]
    assert ids == ["6712345678901", "6712345678902"]


def test_product_import_endpoint_requires_admin(client):
    response = client.post(
        "/api/import/products-list",
        files={"file": ("商品清单.xlsx", workbook_bytes([["商品ID"]]), "xlsx")},
    )

    assert response.status_code == 401


def test_admin_page_exposes_product_list_import(client):
    headers = login(client)
    response = client.get("/admin", headers=headers)

    assert response.status_code == 200
    assert 'id="product-import-form"' in response.text
