"""按“店铺 + 报表类型 + 表头签名”保存源列与系统字段的对应关系。

表结构以 app/schema.sql 为准：column_map_profiles + column_maps。
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from app.imports.ingester import ALIASES

FIELD_LABELS: dict[str, str] = {
    "date": "日期",
    "product_id": "商品 ID",
    "product_name": "商品名称",
    "pay_amount": "支付金额",
    "refund_amount": "退款金额",
    "pay_qty": "支付件数",
    "visitors": "访客数",
    "buyers": "支付买家数",
    "cost": "推广花费",
    "ad_gmv": "推广成交金额",
    "ad_cost": "店铺推广花费",
}

FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "store": ("date", "pay_amount", "refund_amount", "ad_cost", "visitors", "buyers"),
    "product": (
        "date",
        "product_id",
        "product_name",
        "pay_amount",
        "refund_amount",
        "pay_qty",
        "visitors",
        "buyers",
    ),
    "ad": ("date", "product_id", "cost", "ad_gmv"),
}


def fields_for(file_type: str) -> list[dict[str, str]]:
    return [
        {"field": field, "label": FIELD_LABELS.get(field, field)}
        for field in FIELD_GROUPS.get(file_type, ())
    ]


def header_signature(headers: Sequence[str]) -> str:
    canonical = "\x1f".join(str(h).strip() for h in headers)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def suggest_mapping(headers: Sequence[str], file_type: str) -> dict[str, str]:
    """按内置别名推荐映射，未命中的字段留空由用户选择。"""
    known = [str(h).strip() for h in headers]
    suggested: dict[str, str] = {}
    for field in FIELD_GROUPS.get(file_type, ()):
        for alias in ALIASES.get(field, ()):
            if alias in known:
                suggested[field] = alias
                break
    return suggested


def _profile_id(
    connection: sqlite3.Connection, store_id: Any, file_type: str, signature: str
) -> int | None:
    row = connection.execute(
        "SELECT id FROM column_map_profiles WHERE store_id=? AND file_type=? AND header_signature=?",
        (store_id, file_type, signature),
    ).fetchone()
    return int(row[0]) if row else None


def load_mapping(
    connection: sqlite3.Connection, store_id: Any, file_type: str, headers: Sequence[str]
) -> dict[str, str]:
    """读取已保存的映射；未保存时返回空字典，由调用方回退到别名推断。"""
    profile_id = _profile_id(connection, store_id, file_type, header_signature(headers))
    if profile_id is None:
        return {}
    rows = connection.execute(
        "SELECT system_field, source_column FROM column_maps WHERE profile_id=?",
        (profile_id,),
    ).fetchall()
    return {str(row[0]): str(row[1]) for row in rows}


def save_mapping(
    connection: sqlite3.Connection,
    store_id: Any,
    file_type: str,
    headers: Sequence[str],
    mapping: Mapping[str, str],
    *,
    sheet_name: str | None = None,
    header_row: int = 1,
    data_start_row: int = 2,
    row_filter: str | None = None,
) -> str:
    if file_type not in FIELD_GROUPS:
        raise ValueError("未知报表类型，应为 store、product 或 ad")
    signature = header_signature(headers)
    known = {str(h).strip() for h in headers}
    entries = [
        (str(field), str(source))
        for field, source in mapping.items()
        if field in FIELD_LABELS and str(source or "").strip() in known
    ]
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "INSERT INTO column_map_profiles"
        " (store_id, file_type, header_signature, sheet_name, header_row, data_start_row,"
        " row_filter, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(store_id, file_type, header_signature) DO UPDATE SET"
        " sheet_name=excluded.sheet_name, header_row=excluded.header_row,"
        " data_start_row=excluded.data_start_row, row_filter=excluded.row_filter,"
        " updated_at=excluded.updated_at",
        (
            store_id,
            file_type,
            signature,
            sheet_name,
            header_row,
            data_start_row,
            row_filter,
            now,
            now,
        ),
    )
    profile_id = _profile_id(connection, store_id, file_type, signature)
    connection.execute("DELETE FROM column_maps WHERE profile_id=?", (profile_id,))
    if entries:
        connection.executemany(
            "INSERT INTO column_maps (profile_id, source_column, system_field) VALUES (?,?,?)",
            [(profile_id, source, field) for field, source in entries],
        )
    connection.commit()
    return signature
