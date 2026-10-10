from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.admin.dims import DimensionStore, DuplicateNameError
from app.admin.products import ProductStore
from app.admin.targets import TargetStore
from app.auth import admin_required, current_admin, credentials, secret_key
from app.security import SESSION_TTL_SECONDS, PasswordError, issue_session

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
    store = credentials(request)
    if store is None or not store.verify(username, password):
        return templates.TemplateResponse(request, "login.html", {"error": "账号或密码错误"}, status_code=401)
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(
        "admin_session",
        issue_session(username, secret_key(request)),
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("admin_session")
    return response


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, admin_session: str | None = Cookie(default=None)):
    if not current_admin(request, admin_session):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "admin.html")


@router.post("/api/admin/password")
def change_password(request: Request, payload: dict, admin: str = Depends(admin_required)):
    current = str(payload.get("current_password") or "")
    new_password = str(payload.get("new_password") or "")
    confirm_password = str(payload.get("confirm_password") or "")
    if not current or not new_password or not confirm_password:
        raise HTTPException(status_code=400, detail="缺少必填项：原密码、新密码、确认新密码")
    store = credentials(request)
    if store is None:
        raise HTTPException(status_code=500, detail="凭据存储未初始化")
    if not store.verify(admin, current):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的新密码不一致")
    if new_password == current:
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    try:
        store.set_password(admin, new_password)
    except PasswordError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/api/admin/clear/{scope}")
def clear_scope(scope: str, request: Request, payload: dict, _admin: str = Depends(admin_required)):
    from app.admin.reset import ClearConfirmationError, ClearScopeError, clear_scope as clear_scope_data

    connection = _connection(request)
    try:
        return clear_scope_data(
            connection,
            Path(getattr(request.app.state, "data_dir", Path("data"))),
            scope,
            payload.get("confirmation"),
        )
    except ClearConfirmationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ClearScopeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        connection.close()


@router.post("/api/admin/bulk-delete")
def bulk_delete(request: Request, payload: dict, _admin: str = Depends(admin_required)):
    table = payload.get("table")
    if table not in (*DIMENSION_TABLES, "products"):
        raise HTTPException(status_code=400, detail="不支持的批量删除类型")
    connection = _connection(request)
    deleted = []
    failed = []
    try:
        for item in payload.get("items", []):
            try:
                if table == "products":
                    ProductStore(connection).delete(item.get("store_id"), item.get("product_id"))
                    deleted.append(item)
                else:
                    DimensionStore(connection).delete(table, item.get("id"))
                    deleted.append(item.get("id"))
            except (LookupError, RuntimeError, ValueError) as exc:
                failed.append({"item": item, "reason": str(exc)})
        return {"table": table, "deleted": deleted, "failed": failed}
    finally:
        connection.close()


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

@router.put("/api/admin/products/{store_id}/{product_id}")
def update_product(store_id: int, product_id: str, values: dict, request: Request, _admin: str = Depends(admin_required)):
    connection = _connection(request)
    try:
        ProductStore(connection).update(store_id, product_id, values)
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=400 if isinstance(exc, ValueError) else 404, detail=str(exc)) from exc
    finally:
        connection.close()
    return {"ok": True}

@router.post("/api/admin/products/batch-update")
def batch_update_products(request: Request, payload: dict, _admin: str = Depends(admin_required)):
    items = payload.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="请先选择要修改的商品")
    months = [str(month) for month in (payload.get("months") or []) if _MONTH.match(str(month))]
    connection = _connection(request)
    try:
        return ProductStore(connection).batch_update(
            items,
            payload.get("patch") or {},
            sync_daily=bool(payload.get("sync_daily")),
            months=months,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        connection.close()


@router.delete("/api/admin/products/{store_id}/{product_id}")
def delete_product(store_id: int, product_id: str, request: Request, _admin: str = Depends(admin_required)):
    connection = _connection(request)
    try:
        ProductStore(connection).delete(store_id, product_id)
    except (LookupError, RuntimeError) as exc:
        raise HTTPException(status_code=404 if isinstance(exc, LookupError) else 409, detail=str(exc)) from exc
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

@router.put("/api/admin/{table}/{item_id}")
def update_dimension(table: str, item_id: int, values: dict, request: Request, _admin: str = Depends(admin_required)):
    if table not in DIMENSION_TABLES:
        raise HTTPException(status_code=404, detail="不支持的资料类型")
    connection = _connection(request)
    try:
        DimensionStore(connection).update(table, item_id, values)
    except (DuplicateNameError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        connection.close()
    return {"ok": True}

@router.delete("/api/admin/{table}/{item_id}")
def delete_dimension(table: str, item_id: int, request: Request, _admin: str = Depends(admin_required)):
    if table not in DIMENSION_TABLES:
        raise HTTPException(status_code=404, detail="不支持的资料类型")
    connection = _connection(request)
    try:
        DimensionStore(connection).delete(table, item_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        connection.close()
    return {"ok": True}
