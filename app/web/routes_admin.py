from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.admin.dims import DimensionStore, DuplicateNameError
from app.admin.products import ProductStore
from app.admin.targets import TargetStore
from app.auth import admin_required, authenticate_admin

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

DIMENSION_TABLES = ("stores", "operators", "categories")
TARGET_SCOPES = ("store", "category", "operator")
_MONTH = re.compile(r"^\d{4}-\d{2}$")


def _connection(request: Request):
    db = getattr(request.app.state, "db", None)
    if callable(db):
        return db()
    if db is not None:
        return db
    raise RuntimeError("数据库尚未初始化")


def _require(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    missing = [key for key in keys if payload.get(key) in (None, "")]
    if missing:
        raise HTTPException(status_code=400, detail=f"缺少必填项：{'、'.join(missing)}")
    return payload


def _amount(payload: dict[str, Any]) -> float:
    try:
        return float(payload.get("amount"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="目标金额必须是数字") from None


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = authenticate_admin(username, password, getattr(request.app.state, "admins", {"admin": "admin"}))
    if not user: return templates.TemplateResponse(request, "login.html", {"error": "账号或密码错误"}, status_code=401)
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie("admin_session", user, httponly=True, samesite="lax")
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("admin_session")
    return response


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, _admin: str = Depends(admin_required)):
    return templates.TemplateResponse(request, "admin.html")


@router.post("/api/admin/reset")
def reset_business_data(request: Request, payload: dict, _admin: str = Depends(admin_required)):
    from app.admin.reset import ClearConfirmationError, clear_business_data

    connection = _connection(request)
    try:
        return clear_business_data(
            connection,
            Path(getattr(request.app.state, "data_dir", Path("data"))),
            payload.get("confirmation"),
        )
    except ClearConfirmationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        connection.close()


@router.get("/api/admin/reset")
def reset_business_data_get(_admin: str = Depends(admin_required)):
    raise HTTPException(status_code=405, detail="请使用 POST 清空业务数据")


@router.get("/api/admin/targets")
def list_targets(request: Request, month: str, _admin: str = Depends(admin_required)):
    if not _MONTH.match(month or ""):
        raise HTTPException(status_code=400, detail="月份格式应为 YYYY-MM")
    connection = _connection(request)
    try:
        return TargetStore(connection).list_month(month)
    finally:
        connection.close()


@router.put("/api/admin/targets/{scope}")
def put_target(scope: str, values: dict, request: Request, _admin: str = Depends(admin_required)):
    if scope not in TARGET_SCOPES:
        raise HTTPException(status_code=400, detail="不支持的目标类型")
    month = values.get("month") or ""
    if not _MONTH.match(month):
        raise HTTPException(status_code=400, detail="月份格式应为 YYYY-MM")
    amount = _amount(values)
    connection = _connection(request)
    try:
        targets = TargetStore(connection)
        if scope == "store":
            _require(values, "store_id")
            targets.upsert_store(month, values["store_id"], amount)
        elif scope == "category":
            _require(values, "store_id", "category_id")
            targets.upsert_category(month, values["store_id"], values["category_id"], amount)
        else:
            _require(values, "operator_id")
            targets.upsert_operator(month, values["operator_id"], amount)
    finally:
        connection.close()
    return {"ok": True}


@router.get("/api/admin/products")
def list_products(request: Request, _admin: str = Depends(admin_required)):
    connection = _connection(request)
    try:
        return {"items": ProductStore(connection).list()}
    finally:
        connection.close()


@router.post("/api/admin/products")
def create_product(values: dict, request: Request, _admin: str = Depends(admin_required)):
    _require(values, "store_id", "product_id", "name", "category_id", "operator_id")
    connection = _connection(request)
    try:
        ProductStore(connection).upsert(values)
    finally:
        connection.close()
    return {"ok": True}


@router.get("/api/admin/{table}")
def list_dimension(table: str, request: Request, _admin: str = Depends(admin_required)):
    if table not in DIMENSION_TABLES:
        raise HTTPException(status_code=404, detail="不支持的资料类型")
    connection = _connection(request)
    try:
        return {"items": DimensionStore(connection).list(table)}
    finally:
        connection.close()


@router.post("/api/admin/{table}")
def create_dimension(table: str, values: dict, request: Request, _admin: str = Depends(admin_required)):
    if table not in DIMENSION_TABLES:
        raise HTTPException(status_code=404, detail="不支持的资料类型")
    connection = _connection(request)
    try:
        item_id = DimensionStore(connection).create(table, values)
    except (DuplicateNameError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        connection.close()
    return {"ok": True, "id": item_id}
