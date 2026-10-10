import sqlite3

from app.metrics.category_metrics import category_metrics
from app.metrics.operator_metrics import operator_metrics
from app.metrics.store_metrics import store_metrics


def _connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE fact_store_daily (
            date TEXT, store_id TEXT, pay_amount REAL, refund_amount REAL,
            ad_cost REAL, visitors INTEGER, buyers INTEGER,
            PRIMARY KEY (date, store_id)
        );
        CREATE TABLE fact_product_daily (
            date TEXT, store_id TEXT, product_id TEXT, category_id TEXT,
            operator_id TEXT, pay_amount REAL, refund_amount REAL,
            PRIMARY KEY (date, store_id, product_id)
        );
        CREATE TABLE fact_ad_daily (
            date TEXT, store_id TEXT, product_id TEXT, category_id TEXT,
            operator_id TEXT, cost REAL,
            PRIMARY KEY (date, store_id, product_id)
        );
        CREATE TABLE targets_store (month TEXT, store_id TEXT, target_amount REAL);
        CREATE TABLE targets_category (month TEXT, store_id TEXT, category_id TEXT, target_amount REAL);
        CREATE TABLE targets_operator (month TEXT, operator_id TEXT, target_amount REAL);
        """
    )
    return connection


def test_store_metrics_takes_ad_cost_from_ad_report_without_reconciliation():
    connection = _connection()
    connection.execute("INSERT INTO fact_store_daily VALUES ('2026-01-02', 'A', 1000, 100, 7, 10, 2)")
    connection.execute("INSERT INTO fact_ad_daily VALUES ('2026-01-02', 'A', 'p1', 'c1', 'u1', 90)")
    connection.execute("INSERT INTO targets_store VALUES ('2026-01', 'A', 1200)")

    result = store_metrics(connection, "A", "2026-01-02", "2026-01-02", "day")

    assert result["summary"] == {
        "pay_amount": 1000.0,
        "refund_amount": 100.0,
        "settlement_amount": 900.0,
        "ad_cost": 90.0,
        "cost_ratio": 0.1,
        "target_amount": 1200.0,
    }
    assert "reconciliation" not in result


def test_category_metrics_groups_fact_snapshots_and_uses_store_category_target():
    connection = _connection()
    connection.execute("INSERT INTO fact_product_daily VALUES ('2026-01-02', 'A', 'p1', 'c1', 'u1', 100, 10)")
    connection.execute("INSERT INTO fact_ad_daily VALUES ('2026-01-02', 'A', 'p1', 'c1', 'u1', 18)")
    connection.execute("INSERT INTO targets_category VALUES ('2026-01', 'A', 'c1', 300)")

    result = category_metrics(connection, "A", "2026-01-02", "2026-01-02", "day")

    assert result["rows"] == [{
        "category_id": "c1", "pay_amount": 100.0, "refund_amount": 10.0,
        "settlement_amount": 90.0, "ad_cost": 18.0, "cost_ratio": 0.2,
        "target_amount": 300.0,
    }]


def test_operator_metrics_returns_two_store_breakdown_share_and_null_ratio_for_zero_settlement():
    connection = _connection()
    connection.executemany(
        "INSERT INTO fact_product_daily VALUES (?, ?, ?, ?, ?, ?, ?)",
        [("2026-01-02", "A", "p1", "c1", "u1", 100, 20), ("2026-01-02", "B", "p2", "c2", "u1", 50, 50)],
    )
    connection.executemany(
        "INSERT INTO fact_ad_daily VALUES (?, ?, ?, ?, ?, ?)",
        [("2026-01-02", "A", "p1", "c1", "u1", 16), ("2026-01-02", "B", "p2", "c2", "u1", 5)],
    )
    connection.execute("INSERT INTO targets_operator VALUES ('2026-01', 'u1', 300)")

    result = operator_metrics(connection, "2026-01-02", "2026-01-02", "day")

    assert result["rows"] == [{
        "operator_id": "u1", "pay_amount": 150.0, "refund_amount": 70.0,
        "settlement_amount": 80.0, "ad_cost": 21.0, "cost_ratio": 21 / 80,
        "target_amount": 300.0,
        "stores": [
            {"store_id": "A", "settlement_amount": 80.0, "share": 1.0},
            {"store_id": "B", "settlement_amount": 0.0, "share": 0.0},
        ],
    }]
