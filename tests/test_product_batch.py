"""商品批量修改：改类目/运营/状态，可选同步日报。"""

from app.admin.products import ProductStore


def seed(connection):
    connection.executescript(
        """
        INSERT INTO stores VALUES (1, 'A店', '淘宝');
        INSERT INTO operators VALUES (1, '小王');
        INSERT INTO operators VALUES (2, '小李');
        INSERT INTO categories VALUES (1, '类目一', 1);
        INSERT INTO categories VALUES (2, '类目二', 2);
        INSERT INTO products VALUES (1, 'P1', '商品一', 1, 1, 'active');
        INSERT INTO products VALUES (1, 'P2', '商品二', 1, 1, 'active');
        INSERT INTO fact_product_daily VALUES
            ('2026-01-05', 1, 'P1', '商品一', 1, 1, 100, 0, 1, 0, 0),
            ('2026-02-05', 1, 'P1', '商品一', 1, 1, 100, 0, 1, 0, 0);
        INSERT INTO fact_ad_daily VALUES
            ('2026-01-05', 1, 'P1', 1, 1, 10, 50),
            ('2026-02-05', 1, 'P1', 1, 1, 10, 50);
        """
    )


def read_product(connection, product_id):
    return connection.execute(
        "SELECT category_id, operator_id, status FROM products WHERE store_id=1 AND product_id=?",
        (product_id,),
    ).fetchone()


def read_daily(connection, date):
    return connection.execute(
        "SELECT category_id, operator_id FROM fact_product_daily WHERE store_id=1 AND product_id='P1' AND date=?",
        (date,),
    ).fetchone()


def test_batch_update_changes_products_without_touching_daily(db_path):
    from app.db import connect_db, init_db

    init_db(db_path)
    connection = connect_db(db_path)
    seed(connection)

    result = ProductStore(connection).batch_update(
        [{"store_id": 1, "product_id": "P1"}, {"store_id": 1, "product_id": "P2"}],
        {"category_id": 2, "operator_id": 2},
    )

    assert result["updated"] == 2
    assert result["daily_rows"] == 0
    assert tuple(read_product(connection, "P1")) == (2, 2, "active")
    assert tuple(read_daily(connection, "2026-01-05")) == (1, 1)
    connection.close()


def test_batch_update_syncs_only_selected_months(db_path):
    from app.db import connect_db, init_db

    init_db(db_path)
    connection = connect_db(db_path)
    seed(connection)

    result = ProductStore(connection).batch_update(
        [{"store_id": 1, "product_id": "P1"}],
        {"category_id": 2, "operator_id": 2},
        sync_daily=True,
        months=["2026-01"],
    )

    assert result["months"] == ["2026-01"]
    assert result["daily_rows"] == 2
    assert tuple(read_daily(connection, "2026-01-05")) == (2, 2)
    assert tuple(read_daily(connection, "2026-02-05")) == (1, 1)

    ad_row = connection.execute(
        "SELECT category_id FROM fact_ad_daily WHERE store_id=1 AND product_id='P1' AND date='2026-01-05'"
    ).fetchone()
    assert ad_row["category_id"] == 2
    connection.close()


def test_batch_update_rejects_empty_patch_or_items(db_path):
    from app.db import connect_db, init_db

    init_db(db_path)
    connection = connect_db(db_path)
    seed(connection)
    store = ProductStore(connection)

    for kwargs in (
        {"patch": {}},
        {"patch": {"unknown": 1}},
        {"patch": {"category_id": 2}, "sync_daily": True, "months": []},
    ):
        try:
            store.batch_update([{"store_id": 1, "product_id": "P1"}], **kwargs)
        except ValueError:
            continue
        raise AssertionError(f"{kwargs} should be rejected")

    try:
        store.batch_update([], {"category_id": 2})
    except ValueError:
        pass
    else:
        raise AssertionError("empty items should be rejected")
    connection.close()


def test_batch_update_reports_unknown_products(db_path):
    from app.db import connect_db, init_db

    init_db(db_path)
    connection = connect_db(db_path)
    seed(connection)

    result = ProductStore(connection).batch_update(
        [{"store_id": 1, "product_id": "P1"}, {"store_id": 1, "product_id": "GHOST"}],
        {"status": "inactive"},
    )

    assert result["updated"] == 1
    assert result["failed"][0]["item"]["product_id"] == "GHOST"
    assert read_product(connection, "P1")["status"] == "inactive"
    connection.close()


def test_batch_update_endpoint_requires_login_and_items(client):
    assert client.post(
        "/api/admin/products/batch-update",
        json={"items": [{"store_id": 1, "product_id": "P1"}], "patch": {"category_id": 1}},
    ).status_code == 401

    response = client.post(
        "/login",
        data={"username": "admin", "password": "ecompass123"},
        follow_redirects=False,
    )
    headers = {"Cookie": f"admin_session={response.cookies['admin_session']}"}

    assert client.post(
        "/api/admin/products/batch-update",
        json={"items": [], "patch": {"category_id": 1}},
        headers=headers,
    ).status_code == 400
