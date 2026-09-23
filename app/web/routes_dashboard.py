from __future__ import annotations

from datetime import date
from calendar import monthrange
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.metrics.category_metrics import category_metrics
from app.metrics.operator_metrics import operator_metrics
from app.metrics.store_metrics import store_metrics

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _connection(request: Request):
    factory = getattr(request.app.state, "db", None)
    if callable(factory):
        return factory()
    if factory is not None:
        return factory
    raise RuntimeError("数据库尚未初始化")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return _templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"title": "运营数据看板"},
    )


@router.get("/api/dashboard")
def dashboard_api(
    request: Request,
    start: str | None = Query(None),
    end: str | None = Query(None),
    granularity: str | None = Query(None),
    store_id: int | None = None,
):
    today = date.today()
    current_start = today.replace(day=1).isoformat()
    current_end = today.replace(day=monthrange(today.year, today.month)[1]).isoformat()
    if start is None and end is None:
        start = current_start
        end = current_end
        granularity = granularity or "month"
    else:
        start = start or current_start
        end = end or current_end
        granularity = granularity or "day"
    if granularity not in {"day", "month"}:
        raise HTTPException(422, "granularity must be day or month")
    if start > end:
        raise HTTPException(422, "start must not be after end")
    connection = _connection(request)
    try:
        store_rows = connection.execute(
            "SELECT id, name FROM stores WHERE (? IS NULL OR id = ?) ORDER BY id",
            (store_id, store_id),
        ).fetchall()
        stores = []
        categories = []
        for row in store_rows:
            metric = store_metrics(connection, row["id"], start, end, granularity)
            metric["store_name"] = row["name"]
            stores.append(metric)
            categories.append(category_metrics(connection, row["id"], start, end, granularity))
        category_dimensions = [
            dict(row)
            for row in connection.execute("SELECT id, name FROM categories ORDER BY name")
        ]
        operator_dimensions = [
            dict(row)
            for row in connection.execute("SELECT id, name FROM operators ORDER BY name")
        ]
        return {
            "filters": {
                "start": start,
                "end": end,
                "granularity": granularity,
                "store_id": store_id,
            },
            "stores": stores,
            "categories": categories,
            "operators": operator_metrics(connection, start, end, granularity)["rows"],
            "dimensions": {
                "categories": category_dimensions,
                "operators": operator_dimensions,
            },
        }
    finally:
        connection.close()
