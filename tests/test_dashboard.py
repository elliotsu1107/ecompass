import calendar
import sqlite3
from datetime import date


def test_dashboard_api_defaults_to_current_calendar_month(client):
    today = date.today()
    expected_start = today.replace(day=1).isoformat()
    expected_end = today.replace(day=calendar.monthrange(today.year, today.month)[1]).isoformat()
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    assert response.json()["filters"]["start"] == expected_start
    assert response.json()["filters"]["end"] == expected_end
    assert response.json()["filters"]["granularity"] == "month"


def test_dashboard_api_returns_seeded_store_and_category_data(client):
    connection = client.app.state.db()
    connection.execute("INSERT INTO operators(id, name) VALUES (1, '运营')")
    connection.execute("INSERT INTO stores(id, name, platform) VALUES (1, '测试店', '淘宝')")
    connection.execute("INSERT INTO categories(id, name, operator_id) VALUES (1, '类目', 1)")
    connection.execute("INSERT INTO products(store_id, product_id, name, category_id, operator_id) VALUES (1, 'P1', '商品', 1, 1)")
    connection.execute("INSERT INTO fact_store_daily(date, store_id, pay_amount, refund_amount, ad_cost, visitors, buyers) VALUES ('2026-09-01', 1, 100, 10, 5, 20, 3)")
    connection.execute("INSERT INTO fact_product_daily(date, store_id, product_id, product_name, category_id, operator_id, pay_amount, refund_amount, pay_qty, visitors, buyers) VALUES ('2026-09-01', 1, 'P1', '商品', 1, 1, 100, 10, 2, 20, 3)")
    connection.commit()
    connection.close()

    response = client.get("/api/dashboard?start=2026-09-01&end=2026-09-30&granularity=month")

    assert response.status_code == 200
    body = response.json()
    assert len(body["stores"]) == 1
    assert body["stores"][0]["summary"]["settlement_amount"] == 90.0
    assert body["stores"][0]["store_name"] == "测试店"
    assert body["categories"][0]["store_id"] == 1
    assert body["categories"][0]["rows"][0]["settlement_amount"] == 90.0


def test_dashboard_page_uses_current_month_controls(client):
    response = client.get("/")
    assert 'id="month" type="month"' in response.text
    assert 'id="day-range"' in response.text
    assert 'id="granularity"' in response.text


def test_dashboard_api_can_filter_one_store(client):
    connection = client.app.state.db()
    connection.execute("INSERT INTO operators(id, name) VALUES (1, '运营')")
    connection.execute("INSERT INTO stores(id, name, platform) VALUES (1, 'A店', '淘宝')")
    connection.execute("INSERT INTO stores(id, name, platform) VALUES (2, 'B店', '淘宝')")
    connection.execute("INSERT INTO categories(id, name, operator_id) VALUES (1, '类目', 1)")
    connection.execute("INSERT INTO products(store_id, product_id, name, category_id, operator_id) VALUES (1, 'P1', '商品', 1, 1)")
    connection.execute("INSERT INTO fact_store_daily(date, store_id, pay_amount, refund_amount, ad_cost) VALUES ('2026-09-01', 1, 100, 0, 0)")
    connection.commit()
    connection.close()

    response = client.get("/api/dashboard?start=2026-09-01&end=2026-09-30&granularity=month&store_id=1")
    assert response.status_code == 200
    assert [item["store_id"] for item in response.json()["stores"]] == [1]


def test_dashboard_api_rejects_non_integer_store_id(client):
    response = client.get("/api/dashboard?start=2026-09-01&end=2026-09-30&store_id=bad")
    assert response.status_code == 422


def test_dashboard_api_honors_date_range_and_granularity(client):
    response = client.get("/api/dashboard?start=2026-01-01&end=2026-01-31&granularity=month")
    assert response.status_code == 200
    body = response.json()
    assert body["filters"]["start"] == "2026-01-01"
    assert body["filters"]["end"] == "2026-01-31"
    assert body["filters"]["granularity"] == "month"
    assert {"stores", "categories", "operators"} <= body.keys()


def test_dashboard_api_rejects_unknown_granularity(client):
    response = client.get("/api/dashboard?granularity=year")
    assert response.status_code == 422
