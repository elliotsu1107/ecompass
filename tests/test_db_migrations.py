import sqlite3

from app.db import init_db


def test_init_db_adds_product_name_to_existing_database_without_losing_rows(tmp_path):
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE fact_product_daily ("
        "date TEXT NOT NULL, store_id INTEGER NOT NULL, product_id TEXT NOT NULL,"
        "category_id INTEGER NOT NULL, operator_id INTEGER NOT NULL,"
        "pay_amount NUMERIC NOT NULL DEFAULT 0, refund_amount NUMERIC NOT NULL DEFAULT 0,"
        "pay_qty INTEGER NOT NULL DEFAULT 0, visitors INTEGER NOT NULL DEFAULT 0,"
        "PRIMARY KEY (date, store_id, product_id))"
    )
    connection.execute(
        "INSERT INTO fact_product_daily (date,store_id,product_id,category_id,operator_id,pay_amount)"
        " VALUES ('2026-09-01',1,'P1',1,1,10)"
    )
    connection.commit()
    connection.close()

    init_db(db_path)

    connection = sqlite3.connect(db_path)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(fact_product_daily)")}
    row = connection.execute(
        "SELECT date, store_id, product_id, product_name, pay_amount FROM fact_product_daily"
    ).fetchone()
    connection.close()

    assert "product_name" in columns
    assert row == ("2026-09-01", 1, "P1", None, 10)
