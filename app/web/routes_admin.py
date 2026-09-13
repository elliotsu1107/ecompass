from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.admin.dims import DimensionStore
from app.admin.products import ProductStore
from app.admin.targets import TargetStore
from app.auth import admin_required, authenticate_admin

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _connection(request: Request):
    db = getattr(request.app.state, "db", None)
    if callable(db): return db()
    if db is not None: return db
    raise RuntimeError("数据库尚未初始化")


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
    raise HTTPException(status_code=405, detail="Method Not Allowed")


@router.get("/api/admin/{table}")
def list_dimension(table: str, request: Request, _admin: str = Depends(admin_required)):
    return DimensionStore(_connection(request)).list(table)


@router.put("/api/admin/{table}/{item_id}")
def put_dimension(table: str, item_id: str, values: dict, request: Request, _admin: str = Depends(admin_required)):
    values["id"] = item_id
    DimensionStore(_connection(request)).upsert(table, values)
    return {"ok": True}


@router.get("/api/admin/products")
def list_products(request: Request, _admin: str = Depends(admin_required)):
    return ProductStore(_connection(request)).list()


@router.put("/api/admin/products/{store_id}/{product_id}")
def put_product(store_id: str, product_id: str, values: dict, request: Request, _admin: str = Depends(admin_required)):
    ProductStore(_connection(request)).upsert({**values, "store_id": store_id, "product_id": product_id})
    return {"ok": True}


@router.put("/api/admin/targets/{scope}")
def put_target(scope: str, values: dict, request: Request, _admin: str = Depends(admin_required)):
    targets = TargetStore(_connection(request))
    if scope == "store": targets.upsert_store(values["month"], values["store_id"], values["amount"])
    elif scope == "category": targets.upsert_category(values["month"], values["store_id"], values["category_id"], values["amount"])
    elif scope == "operator": targets.upsert_operator(values["month"], values["operator_id"], values["amount"])
    else: raise ValueError("invalid target scope")
    return {"ok": True}
