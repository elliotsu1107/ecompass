def test_dashboard_page_exposes_compact_operational_dashboard(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "运营数据看板" in response.text
    assert 'id="dashboard-app"' in response.text
    assert "echarts" in response.text.lower()


def test_dashboard_api_honors_date_range_and_granularity(client):
    response = client.get("/api/dashboard?start=2026-01-01&end=2026-01-31&granularity=month")

    assert response.status_code == 200
    body = response.json()
    assert body["filters"] == {
        "start": "2026-01-01", "end": "2026-01-31", "granularity": "month"
    }
    assert {"stores", "categories", "operators"} <= body.keys()


def test_dashboard_api_rejects_unknown_granularity(client):
    response = client.get("/api/dashboard?granularity=year")

    assert response.status_code == 422
