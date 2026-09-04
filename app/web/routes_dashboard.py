from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.metrics.category_metrics import category_metrics
from app.metrics.operator_metrics import operator_metrics
from app.metrics.store_metrics import store_metrics

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "web" / "templates"))


def _connection(request: Request):
    connection = getattr(request.app.state, "connection", None)
    if connection is not None:
        return connection
    db_path = getattr(getattr(request.app.state, "config", None), "db_path", None)
    if db_path:
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        return connection
    return sqlite3.connect(":memory:")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return _templates.TemplateResponse(request=request, name="dashboard.html", context={"title": "运营数据看板"})


@router.get("/api/dashboard")
def dashboard_api(request: Request, start: str = Query("2026-01-01"), end: str = Query("2026-01-31"), granularity: str = Query("day"), store_id: str | None = None):
    if granularity not in {"day", "month"}:
        raise HTTPException(422, "granularity must be day or month")
    connection = _connection(request)
    try:
        stores = []
        if store_id:
            stores = [store_metrics(connection, store_id, start, end, granularity)]
        else:
            try:
                ids = [r["store_id"] for r in connection.execute("SELECT store_id FROM stores ORDER BY store_id")]
            except sqlite3.Error:
                ids = []
            stores = [store_metrics(connection, item, start, end, granularity) for item in ids]
        return {"filters": {"start": start, "end": end, "granularity": granularity}, "stores": stores, "categories": [], "operators": operator_metrics(connection, start, end, granularity)["rows"]}
    finally:
        if getattr(request.app.state, "connection", None) is not connection:
            connection.close()
