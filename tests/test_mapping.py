"""列映射的配置、保存与生效链路。"""
import sqlite3

from app.db import connect_db, init_db
from app.imports.mapping import (
    header_signature,
    load_mapping,
    save_mapping,
    suggest_mapping,
)

CSV_TEXT = "日期戳,货号,成交额,退款额\n2026-09-01,P1,100,10\n"
HEADERS = ["日期戳", "货号", "成交额", "退款额"]


def login(client):
    return {
        "Cookie": "admin_session="
        + client.post(
            "/login",
            data={"username": "admin", "password": "ecompass123"},
            follow_redirects=False,
        ).cookies["admin_session"]
    }


def upload(client, headers, store_id, file_type, payload=CSV_TEXT):
    return client.post(
        "/api/import/upload",
        files={"file": ("report.csv", payload.encode("utf-8-sig"), "text/csv")},
        data={"store_id": str(store_id), "file_type": file_type},
        headers=headers,
    )


def seed_product(client, headers, store_id):
    operator_id = client.post(
        "/api/admin/operators", json={"name": "小王"}, headers=headers
    ).json()["id"]
    category_id = client.post(
        "/api/admin/categories",
        json={"name": "咖啡", "operator_id": operator_id},
        headers=headers,
    ).json()["id"]
    client.post(
        "/api/admin/products",
        json={
            "store_id": store_id,
            "product_id": "P1",
            "name": "咖啡豆",
            "category_id": category_id,
            "operator_id": operator_id,
        },
        headers=headers,
    )


def seeded_connection(tmp_path):
    """column_map_profiles.store_id 外键引用 stores，先建店铺。"""
    path = tmp_path / "data" / "ecompass.db"
    init_db(path)
    connection = connect_db(path)
    connection.execute("INSERT INTO stores (name, platform) VALUES (?, ?)", ("A店铺", "淘宝"))
    connection.commit()
    return connection


def test_save_and_load_mapping_roundtrip(tmp_path):
    connection = seeded_connection(tmp_path)

    save_mapping(connection, "1", "product", HEADERS, {"date": "日期戳", "product_id": "货号"})

    assert load_mapping(connection, "1", "product", HEADERS) == {
        "date": "日期戳",
        "product_id": "货号",
    }
    connection.close()


def test_load_mapping_returns_empty_when_not_saved(tmp_path):
    connection = seeded_connection(tmp_path)

    assert load_mapping(connection, "1", "product", HEADERS) == {}
    connection.close()


def test_save_mapping_replaces_previous_entries(tmp_path):
    connection = seeded_connection(tmp_path)

    save_mapping(connection, "1", "product", HEADERS, {"date": "日期戳"})
    save_mapping(connection, "1", "product", HEADERS, {"product_id": "货号", "pay_amount": "成交额"})

    assert load_mapping(connection, "1", "product", HEADERS) == {
        "product_id": "货号",
        "pay_amount": "成交额",
    }
    connection.close()


def test_save_mapping_rejects_unknown_store(tmp_path):
    connection = seeded_connection(tmp_path)

    try:
        save_mapping(connection, "999", "product", HEADERS, {"date": "日期戳"})
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("未保存的店铺应触发外键约束")
    connection.close()


def test_save_mapping_ignores_unknown_source_columns(tmp_path):
    connection = seeded_connection(tmp_path)

    save_mapping(connection, "1", "product", HEADERS, {"date": "不存在的列"})

    assert load_mapping(connection, "1", "product", HEADERS) == {}
    connection.close()


def test_suggest_mapping_matches_known_aliases():
    suggested = suggest_mapping(["统计日期", "商品ID", "支付金额"], "product")

    assert suggested["date"] == "统计日期"
    assert suggested["product_id"] == "商品ID"
    assert suggested["pay_amount"] == "支付金额"


def test_suggest_mapping_skips_unknown_headers():
    assert suggest_mapping(HEADERS, "product") == {}


def test_header_signature_is_stable():
    assert header_signature(HEADERS) == header_signature(list(HEADERS))
    assert header_signature(HEADERS) != header_signature(["日期戳", "货号"])


def test_import_page_exposes_mapping_section(client):
    response = client.get("/import", headers=login(client))

    assert response.status_code == 200
    assert 'id="mapping-section"' in response.text
    assert 'id="save-mapping"' in response.text


def test_upload_returns_headers_fields_and_suggested_mapping(client):
    headers = login(client)
    store_id = client.post(
        "/api/admin/stores", json={"name": "A店铺", "platform": "淘宝"}, headers=headers
    ).json()["id"]

    body = upload(client, headers, store_id, "product").json()

    assert body["headers"] == HEADERS
    assert [field["field"] for field in body["fields"]][:3] == [
        "date",
        "product_id",
        "product_name",
    ]
    assert body["mapping"] == {}
    assert body["stats"]["跳过"] == 1


def test_saved_mapping_applies_on_next_upload(client, db_path):
    headers = login(client)
    store_id = client.post(
        "/api/admin/stores", json={"name": "A店铺", "platform": "淘宝"}, headers=headers
    ).json()["id"]
    seed_product(client, headers, store_id)

    first = upload(client, headers, store_id, "product").json()
    assert first["stats"]["新增"] == 0

    response = client.put(
        "/api/import/mappings",
        json={
            "store_id": str(store_id),
            "file_type": "product",
            "headers": first["headers"],
            "mapping": {
                "date": "日期戳",
                "product_id": "货号",
                "pay_amount": "成交额",
                "refund_amount": "退款额",
            },
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text

    second = upload(client, headers, store_id, "product").json()
    assert second["stats"]["新增"] == 1
    assert second["mapping"]["date"] == "日期戳"

    connection = sqlite3.connect(db_path)
    row = connection.execute(
        "SELECT date, product_id, pay_amount, refund_amount FROM fact_product_daily"
    ).fetchall()
    connection.close()
    assert row == [("2026-09-01", "P1", 100.0, 10.0)]


def test_mapping_api_requires_admin(client):
    response = client.put(
        "/api/import/mappings",
        json={"store_id": "1", "file_type": "store", "headers": HEADERS, "mapping": {}},
    )
    assert response.status_code == 401


def test_mapping_api_rejects_unknown_file_type(client):
    headers = login(client)
    response = client.put(
        "/api/import/mappings",
        json={"store_id": "1", "file_type": "unknown", "headers": HEADERS, "mapping": {}},
        headers=headers,
    )
    assert response.status_code == 400
    assert "未知报表类型" in response.json()["detail"]


def test_mapping_api_requires_headers(client):
    headers = login(client)
    response = client.put(
        "/api/import/mappings",
        json={"store_id": "1", "file_type": "store", "mapping": {}},
        headers=headers,
    )
    assert response.status_code == 400
    assert "缺少表头" in response.json()["detail"]
