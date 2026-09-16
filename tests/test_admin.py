import pytest

from app.admin.dims import DimensionStore, DuplicateNameError
from app.admin.products import ProductStore
from app.admin.targets import TargetStore
from app.db import connect_db, init_db


@pytest.fixture
def connection(tmp_path):
    db_path = tmp_path / "data" / "ecompass.db"
    init_db(db_path)
    conn = connect_db(db_path)
    yield conn
    conn.close()


def test_dimension_store_creates_store_operator_and_category(connection):
    dims = DimensionStore(connection)

    operator_id = dims.create("operators", {"name": "小王"})
    store_id = dims.create("stores", {"name": "A店铺", "platform": "淘宝"})
    category_id = dims.create("categories", {"name": "咖啡", "operator_id": operator_id})

    assert dims.list("stores") == [
        {"id": store_id, "name": "A店铺", "platform": "淘宝"}
    ]
    assert dims.list("operators") == [{"id": operator_id, "name": "小王"}]
    assert dims.list("categories") == [
        {"id": category_id, "name": "咖啡", "operator_id": operator_id}
    ]


def test_dimension_store_rejects_duplicate_name(connection):
    dims = DimensionStore(connection)
    dims.create("stores", {"name": "A店铺", "platform": "淘宝"})

    with pytest.raises(DuplicateNameError):
        dims.create("stores", {"name": "A店铺", "platform": "天猫"})


def test_dimension_store_requires_mandatory_fields(connection):
    dims = DimensionStore(connection)

    with pytest.raises(ValueError):
        dims.create("stores", {"name": "A店铺"})

    with pytest.raises(ValueError):
        dims.create("categories", {"name": "咖啡"})


def test_product_and_targets_use_business_keys_for_upsert(connection):
    dims = DimensionStore(connection)
    products = ProductStore(connection)
    targets = TargetStore(connection)

    operator_id = dims.create("operators", {"name": "小王"})
    store_id = dims.create("stores", {"name": "A店铺", "platform": "淘宝"})
    category_id = dims.create("categories", {"name": "咖啡", "operator_id": operator_id})

    products.upsert({
        "store_id": store_id,
        "product_id": "p-1",
        "name": "拿铁",
        "category_id": category_id,
        "operator_id": operator_id,
    })
    products.upsert({
        "store_id": store_id,
        "product_id": "p-1",
        "name": "冰拿铁",
        "category_id": category_id,
        "operator_id": operator_id,
    })
    targets.upsert_store("2026-09", store_id, 1000)
    targets.upsert_category("2026-09", store_id, category_id, 600)
    targets.upsert_operator("2026-09", operator_id, 1000)

    assert products.list() == [{
        "store_id": store_id,
        "product_id": "p-1",
        "name": "冰拿铁",
        "category_id": category_id,
        "operator_id": operator_id,
    }]
    assert connection.execute("SELECT target_amount FROM targets_store").fetchone()[0] == 1000
    assert connection.execute("SELECT target_amount FROM targets_category").fetchone()[0] == 600
    assert connection.execute("SELECT target_amount FROM targets_operator").fetchone()[0] == 1000


def test_target_store_reads_back_month_values(connection):
    dims = DimensionStore(connection)
    targets = TargetStore(connection)

    operator_id = dims.create("operators", {"name": "小王"})
    store_id = dims.create("stores", {"name": "A店铺", "platform": "淘宝"})
    category_id = dims.create("categories", {"name": "咖啡", "operator_id": operator_id})

    targets.upsert_store("2026-09", store_id, 1000)
    targets.upsert_category("2026-09", store_id, category_id, 600)
    targets.upsert_operator("2026-09", operator_id, 900)

    values = targets.list_month("2026-09")

    assert values["store"] == {str(store_id): 1000.0}
    assert values["category"] == {f"{store_id}:{category_id}": 600.0}
    assert values["operator"] == {str(operator_id): 900.0}


def test_target_store_updates_existing_month_value(connection):
    dims = DimensionStore(connection)
    targets = TargetStore(connection)

    operator_id = dims.create("operators", {"name": "小王"})
    store_id = dims.create("stores", {"name": "A店铺", "platform": "淘宝"})
    dims.create("categories", {"name": "咖啡", "operator_id": operator_id})

    targets.upsert_store("2026-09", store_id, 1000)
    targets.upsert_store("2026-09", store_id, 2500)

    assert targets.list_month("2026-09")["store"][str(store_id)] == 2500.0
