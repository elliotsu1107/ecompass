import sqlite3

from app.admin.dims import DimensionStore
from app.admin.products import ProductStore
from app.admin.targets import TargetStore


def make_connection():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE stores (id TEXT PRIMARY KEY, name TEXT NOT NULL, operator_id TEXT);
        CREATE TABLE operators (id TEXT PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE categories (id TEXT PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE products (
            store_id TEXT NOT NULL, product_id TEXT NOT NULL, name TEXT NOT NULL,
            category_id TEXT, operator_id TEXT, PRIMARY KEY (store_id, product_id)
        );
        CREATE TABLE targets_store (month TEXT, store_id TEXT, amount REAL, PRIMARY KEY(month, store_id));
        CREATE TABLE targets_category (month TEXT, store_id TEXT, category_id TEXT, amount REAL, PRIMARY KEY(month, store_id, category_id));
        CREATE TABLE targets_operator (month TEXT, operator_id TEXT, amount REAL, PRIMARY KEY(month, operator_id));
        """
    )
    return connection


def test_dimension_store_upserts_store_operator_and_category():
    store = DimensionStore(make_connection())

    store.upsert("operators", {"id": "op-1", "name": "小王"})
    store.upsert("stores", {"id": "s-1", "name": "旗舰店", "operator_id": "op-1"})
    store.upsert("categories", {"id": "c-1", "name": "咖啡"})

    assert store.list("stores") == [{"id": "s-1", "name": "旗舰店", "operator_id": "op-1"}]
    assert store.list("operators") == [{"id": "op-1", "name": "小王"}]


def test_product_and_targets_use_business_keys_for_upsert():
    connection = make_connection()
    products = ProductStore(connection)
    targets = TargetStore(connection)

    products.upsert({"store_id": "s-1", "product_id": "p-1", "name": "拿铁", "category_id": "c-1", "operator_id": "op-1"})
    products.upsert({"store_id": "s-1", "product_id": "p-1", "name": "冰拿铁", "category_id": "c-1", "operator_id": "op-1"})
    targets.upsert_store("2026-09", "s-1", 1000)
    targets.upsert_category("2026-09", "s-1", "c-1", 600)
    targets.upsert_operator("2026-09", "op-1", 1000)

    assert products.list() == [{"store_id": "s-1", "product_id": "p-1", "name": "冰拿铁", "category_id": "c-1", "operator_id": "op-1"}]
    assert connection.execute("SELECT amount FROM targets_store").fetchone()[0] == 1000
    assert connection.execute("SELECT amount FROM targets_category").fetchone()[0] == 600
    assert connection.execute("SELECT amount FROM targets_operator").fetchone()[0] == 1000
