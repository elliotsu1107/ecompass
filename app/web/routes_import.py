from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import admin_required, require_admin

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _db(request):
    db = getattr(request.app.state, "db", None)
    return db() if callable(db) else db


def _is_admin(request: Request, admin_session: str | None) -> bool:
    return require_admin(
        admin_session, getattr(request.app.state, "admins", {"admin": "admin"})
    )


@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request, admin_session: str | None = Cookie(default=None)):
    if not _is_admin(request, admin_session):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "import.html")


@router.get("/api/import/logs")
def import_logs(request: Request, limit: int = 20, _admin: str = Depends(admin_required)):
    connection = _db(request)
    cursor = connection.execute(
        "SELECT created_at, file_type, file_name, data_date, inserted_rows, updated_rows,"
        " skipped_rows, unmatched_rows, archive_path FROM import_logs"
        " ORDER BY created_at DESC, id DESC LIMIT ?",
        (max(1, min(limit, 200)),),
    )
    rows = cursor.fetchall()
    connection.close()
    columns = [description[0] for description in cursor.description]
    return {
        "items": [
            dict(row) if hasattr(row, "keys") else dict(zip(columns, row))
            for row in rows
        ]
    }


@router.post("/api/import/upload")
async def upload(request: Request, file: UploadFile = File(...), store_id: str = Form(...), file_type: str = Form(...), _admin: str = Depends(admin_required)):
    try:
        data = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"报表读取失败：{exc}") from exc
    root = Path(getattr(request.app.state, "data_dir", Path("data"))) / "imports" / store_id
    root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()
    stamped_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{digest[:12]}_{file.filename}"
    path = root / stamped_name
    path.write_bytes(data)
    from app.imports.ingester import ingest
    from app.imports.parsers import read_table
    try:
        table = read_table(path)
        connection = _db(request)
        try:
            if file_type == "store":
                stats = ingest(connection, store_id, store_rows=table.rows)
            elif file_type == "product":
                stats = ingest(connection, store_id, product_rows=table.rows)
            elif file_type == "ad":
                stats = ingest(connection, store_id, ad_rows=table.rows)
            else:
                raise HTTPException(status_code=400, detail="未知报表类型，应为 store、product 或 ad")
            connection.execute("INSERT INTO import_logs (created_at,file_type,file_name,file_sha256,data_date,inserted_rows,updated_rows,skipped_rows,unmatched_rows,archive_path) VALUES (?,?,?,?,?,?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), file_type, file.filename, digest, table.rows[0].get("日期", table.rows[0].get("统计日期", "")) if table.rows else "", stats["新增"], stats["更新"], stats["跳过"], stats["未匹配"], str(path)))
            connection.commit()
        finally:
            connection.close()
        return {"file_name": file.filename, "file_sha256": digest, "store_id": store_id, "file_type": file_type, "path": str(path), "header_row": table.header_row + 1, "rows": len(table.rows), "stats": stats}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"报表导入失败：{exc}") from exc


@router.post("/api/import/products-list")
async def upload_product_list(
    request: Request,
    file: UploadFile = File(...),
    _admin: str = Depends(admin_required),
):
    from app.imports.parsers import read_table
    from app.imports.product_list import import_products

    data = await file.read()
    root = Path(getattr(request.app.state, "data_dir", Path("data"))) / "imports" / "products"
    root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()
    stamped_name = (
        f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{digest[:12]}_{file.filename}"
    )
    path = root / stamped_name
    path.write_bytes(data)
    try:
        table = read_table(path)
        connection = _db(request)
        try:
            stats = import_products(connection, table.rows)
            connection.execute(
                "INSERT INTO import_logs (created_at,file_type,file_name,file_sha256,data_date,"
                "inserted_rows,updated_rows,skipped_rows,unmatched_rows,archive_path)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    "product_list",
                    file.filename,
                    digest,
                    "",
                    stats["新增"],
                    stats["更新"],
                    stats["跳过"],
                    stats["未匹配店铺"],
                    str(path),
                ),
            )
            connection.commit()
        finally:
            connection.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"商品清单导入失败：{exc}") from exc
    return {
        "file_name": file.filename,
        "header_row": table.header_row + 1,
        "rows": len(table.rows),
        "stats": stats,
    }


@router.put("/api/import/mappings")
def save_mapping(request: Request, payload: dict, _admin: str = Depends(admin_required)):
    connection = _db(request)
    if connection is None: return {"ok": True}
    now = datetime.now(timezone.utc).isoformat()
    fields = {"store_id": payload["store_id"], "file_type": payload["file_type"], "header_signature": payload.get("header_signature", ""), "sheet_name": payload.get("sheet_name"), "header_row": payload.get("header_row", 1), "data_start_row": payload.get("data_start_row", 2), "row_filter": payload.get("row_filter"), "created_at": now, "updated_at": now}
    cols = ",".join(fields)
    connection.execute(f"INSERT INTO column_map_profiles ({cols}) VALUES ({','.join('?' for _ in fields)})", list(fields.values()))
    connection.commit()
    return {"ok": True}


@router.post("/api/import/archive")
def archive(request: Request, payload: dict, _admin: str = Depends(admin_required)):
    connection = _db(request)
    if connection is not None:
        connection.execute("INSERT INTO import_logs (created_at,file_type,file_name,file_sha256,data_date,inserted_rows,updated_rows,skipped_rows,unmatched_rows,archive_path) VALUES (?,?,?,?,?,?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), payload.get("file_type"), payload.get("file_name"), payload.get("file_sha256"), payload.get("data_date"), payload.get("inserted_rows", 0), payload.get("updated_rows", 0), payload.get("skipped_rows", 0), payload.get("unmatched_rows", 0), payload.get("archive_path")))
        connection.commit()
    return {"ok": True}


@router.post("/api/import/products")
def add_product(request: Request, payload: dict, _admin: str = Depends(admin_required)):
    from app.admin.products import ProductStore
    ProductStore(_db(request)).upsert(payload)
    return {"ok": True}
