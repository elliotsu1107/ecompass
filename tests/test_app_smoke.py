import sqlite3

from fastapi.testclient import TestClient

from app import create_app
from app.config import Config


def test_health_still_initializes_database(tmp_path):
    app = create_app(Config(data_dir=tmp_path / "data"))

    assert TestClient(app).get("/api/health").json() == {"ok": True}


def test_health_endpoint_initializes_database(client, db_path):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert db_path.exists()


def test_schema_contains_required_tables_and_business_keys(client, db_path):
    client.get("/api/health")

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "stores",
            "operators",
            "categories",
            "products",
            "fact_store_daily",
            "fact_product_daily",
            "fact_ad_daily",
            "targets_store",
            "targets_category",
            "targets_operator",
            "import_logs",
            "column_map_profiles",
            "column_maps",
        } <= tables

        assert _primary_key_columns(conn, "products") == ["store_id", "product_id"]
        assert _primary_key_columns(conn, "fact_store_daily") == ["date", "store_id"]
        assert _primary_key_columns(conn, "fact_product_daily") == [
            "date",
            "store_id",
            "product_id",
        ]
        assert _primary_key_columns(conn, "fact_ad_daily") == [
            "date",
            "store_id",
            "product_id",
        ]
        assert _primary_key_columns(conn, "targets_store") == ["month", "store_id"]
        assert _primary_key_columns(conn, "targets_category") == [
            "month",
            "store_id",
            "category_id",
        ]
        assert _primary_key_columns(conn, "targets_operator") == ["month", "operator_id"]
        assert _primary_key_columns(conn, "column_map_profiles") == ["id"]
        assert _primary_key_columns(conn, "column_maps") == ["profile_id", "source_column"]

        assert {
            "date",
            "store_id",
            "pay_amount",
            "refund_amount",
            "ad_cost",
            "visitors",
            "buyers",
        } <= _columns(conn, "fact_store_daily")
        assert {
            "date",
            "store_id",
            "product_id",
            "category_id",
            "operator_id",
            "pay_amount",
            "refund_amount",
            "pay_qty",
            "visitors",
        } <= _columns(conn, "fact_product_daily")
        assert {
            "date",
            "store_id",
            "product_id",
            "category_id",
            "operator_id",
            "cost",
            "ad_gmv",
        } <= _columns(conn, "fact_ad_daily")
        assert {
            "created_at",
            "file_type",
            "file_name",
            "file_sha256",
            "data_date",
            "inserted_rows",
            "updated_rows",
            "skipped_rows",
            "unmatched_rows",
            "archive_path",
        } <= _columns(conn, "import_logs")
        assert {
            "store_id",
            "file_type",
            "header_signature",
            "sheet_name",
            "header_row",
            "data_start_row",
            "row_filter",
            "created_at",
            "updated_at",
        } <= _columns(conn, "column_map_profiles")


def _columns(conn, table_name):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")}


def _primary_key_columns(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in sorted(rows, key=lambda row: row[5]) if row[5] > 0]
