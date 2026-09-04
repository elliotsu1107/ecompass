import sqlite3

from app.imports.ingester import ingest


def _db():
    connection = sqlite3.connect(":memory:")
    connection.executescript("""
    CREATE TABLE products (store_id TEXT, product_id TEXT, category_id TEXT, operator_id TEXT, PRIMARY KEY(store_id, product_id));
    CREATE TABLE fact_product_daily (
      date TEXT NOT NULL, store_id TEXT NOT NULL, product_id TEXT NOT NULL,
      product_name TEXT, pay_amount REAL, refund_amount REAL, pay_qty INTEGER,
      visitors INTEGER, buyers INTEGER, category_id TEXT, operator_id TEXT,
      PRIMARY KEY (date, store_id, product_id)
    );
    CREATE TABLE fact_ad_daily (
      date TEXT NOT NULL, store_id TEXT NOT NULL, product_id TEXT NOT NULL,
      cost REAL, ad_gmv REAL, category_id TEXT, operator_id TEXT,
      PRIMARY KEY (date, store_id, product_id)
    );
    INSERT INTO products VALUES ('A', 'p1', 'c1', 'u1');
    """)
    return connection


def test_ingest_aggregates_ads_and_reports_counts():
    connection = _db()
    product_rows = [{"日期": "2026-01-02", "商品ID": "p1", "商品名称": "咖啡", "支付金额": "12", "支付件数": "2"}]
    ad_rows = [
        {"日期": "2026-01-02", "主体ID": "p1", "主体类型": "商品", "主体名称": "咖啡", "花费": "1.5", "总成交金额": "8"},
        {"日期": "2026-01-02", "主体ID": "p1", "主体类型": "商品", "主体名称": "咖啡", "花费": "2.5", "总成交金额": "4"},
    ]

    first = ingest(connection, store_id="A", product_rows=product_rows, ad_rows=ad_rows)
    assert first == {"新增": 2, "更新": 0, "跳过": 0, "未匹配": 0}
    assert connection.execute("SELECT pay_amount, pay_qty, category_id, operator_id FROM fact_product_daily").fetchone() == (12.0, 2, "c1", "u1")
    assert connection.execute("SELECT cost, ad_gmv, category_id, operator_id FROM fact_ad_daily").fetchone() == (4.0, 12.0, "c1", "u1")

    second = ingest(connection, store_id="A", product_rows=product_rows, ad_rows=ad_rows)
    assert second == {"新增": 0, "更新": 2, "跳过": 0, "未匹配": 0}


def test_ingest_counts_unmatched_ad_product():
    connection = _db()
    result = ingest(connection, "A", [{"日期": "2026-01-02", "商品ID": "p1"}], [{"日期": "2026-01-02", "主体ID": "missing", "主体类型": "商品", "花费": "1", "总成交金额": "2"}])


def test_ingest_upserts_store_daily_report():
    connection = _db()
    connection.execute("CREATE TABLE fact_store_daily (date TEXT, store_id TEXT, pay_amount REAL, refund_amount REAL, ad_cost REAL, visitors INTEGER, buyers INTEGER, PRIMARY KEY(date, store_id))")
    result = ingest(connection, "A", store_rows=[{"统计日期": "2026-01-02", "支付金额": "100", "成功退款金额": "10", "全站推广花费": "5", "访客数": "20", "支付买家数": "3"}])
    assert result == {"新增": 1, "更新": 0, "跳过": 0, "未匹配": 0}
    assert connection.execute("SELECT pay_amount, refund_amount, ad_cost FROM fact_store_daily").fetchone() == (100.0, 10.0, 5.0)
