"""Incremental product and advertising report ingestion."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

FIELDS = ("date", "store", "product_id", "product_name", "pay_amount", "refund_amount", "pay_qty", "visitors", "buyers", "cost", "ad_gmv", "ad_cost")
ALIASES = {
    "date": ("日期", "统计日期", "date"), "product_id": ("商品ID", "商品id", "主体ID", "product_id"),
    "product_name": ("商品名称", "主体名称", "宝贝名称", "product_name"), "pay_amount": ("支付金额", "支付金额(元)", "pay_amount"),
    "refund_amount": ("退款金额", "成功退款金额", "refund_amount"), "pay_qty": ("支付件数", "支付数量", "pay_qty"),
    "visitors": ("访客数", "visitors"), "buyers": ("支付买家数", "买家数", "buyers"),
    "cost": ("花费", "推广花费", "cost"), "ad_gmv": ("总成交金额", "推广成交金额", "ad_gmv"), "ad_cost": ("全站推广花费", "推广花费", "ad_cost"),
}

def _value(row: Mapping[str, Any], field: str, mapping: Mapping[str, str] | None = None) -> Any:
    if mapping and field in mapping: return row.get(mapping[field])
    for name in ALIASES.get(field, (field,)):
        if name in row: return row[name]
    return None

def _number(value: Any, integer: bool = False) -> int | float:
    if value is None or str(value).strip().lower() in ("", "--", "nan", "none"): return 0
    text = str(value).replace(",", "").replace("￥", "").replace("¥", "").strip().replace("%", "")
    try: return int(float(text)) if integer else float(text)
    except (TypeError, ValueError): return 0

def _date(value: Any) -> str:
    if isinstance(value, datetime): return value.date().isoformat()
    if isinstance(value, date): return value.isoformat()
    text = str(value or "").strip().replace("/", "-")
    return text[:10]

def _products(conn, store_id: str, row: Mapping[str, Any]) -> tuple[str, str] | None:
    product_id = str(_value(row, "product_id") or "").strip()
    if not product_id: return None
    try:
        found = conn.execute("SELECT category_id, operator_id FROM products WHERE store_id=? AND product_id=?", (store_id, product_id)).fetchone()
    except Exception:
        return (row.get("category_id"), row.get("operator_id"))
    if found: return found[0], found[1]
    return (row.get("category_id"), row.get("operator_id")) if "category_id" in row else None

def _upsert(conn, table: str, data: dict[str, Any], key: tuple[str, ...]) -> str:
    where = " AND ".join(f"{k}=?" for k in key)
    exists = conn.execute(f"SELECT 1 FROM {table} WHERE {where}", tuple(data[k] for k in key)).fetchone()
    columns = list(data)
    placeholders = ",".join("?" for _ in columns)
    conn.execute(f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({placeholders})", tuple(data[c] for c in columns))
    return "更新" if exists else "新增"

def ingest(conn, store_id: str, product_rows: Iterable[Mapping[str, Any]] = (), ad_rows: Iterable[Mapping[str, Any]] = (), store_rows: Iterable[Mapping[str, Any]] = (), *, category_id: str | None = None, operator_id: str | None = None, file_type: str | None = None) -> dict[str, int]:
    stats = {"新增": 0, "更新": 0, "跳过": 0, "未匹配": 0}
    for row in store_rows:
        day = _date(_value(row, "date"))
        if not day:
            stats["跳过"] += 1
            continue
        data = {"date": day, "store_id": store_id, "pay_amount": _number(_value(row, "pay_amount")), "refund_amount": _number(_value(row, "refund_amount")), "ad_cost": _number(_value(row, "ad_cost")), "visitors": _number(_value(row, "visitors"), True), "buyers": _number(_value(row, "buyers"), True)}
        result = _upsert(conn, "fact_store_daily", data, ("date", "store_id"))
        stats[result] += 1
    product_index = {}
    for row in product_rows:
        pid = str(_value(row, "product_id") or "").strip(); day = _date(_value(row, "date"))
        if not pid or not day: stats["跳过"] += 1; continue
        snap = _products(conn, store_id, row)
        if snap is None: stats["未匹配"] += 1; continue
        cat, op = snap
        product_index[(day, pid)] = (row, cat or category_id, op or operator_id)
        data = {"date": day, "store_id": store_id, "product_id": pid, "product_name": _value(row, "product_name"), "pay_amount": _number(_value(row, "pay_amount")), "refund_amount": _number(_value(row, "refund_amount")), "pay_qty": _number(_value(row, "pay_qty"), True), "visitors": _number(_value(row, "visitors"), True), "buyers": _number(_value(row, "buyers"), True), "category_id": cat or category_id, "operator_id": op or operator_id}
        table = "daily_metrics" if _table_exists(conn, "daily_metrics") else "fact_product_daily"
        result = _upsert(conn, table, data, ("date", "store_id", "product_id")); stats[result] += 1
    grouped = defaultdict(lambda: [0.0, 0.0, None, None])
    for row in ad_rows:
        if str(row.get("主体类型", "商品")).strip() != "商品": stats["跳过"] += 1; continue
        day, pid = _date(_value(row, "date")), str(_value(row, "product_id") or "").strip()
        info = product_index.get((day, pid))
        if not info:
            snap = _products(conn, store_id, row)
            if snap is not None:
                info = (row, snap[0], snap[1])
        if not info:
            stats["未匹配"] += 1
            continue
        _, cat, op = info
        item = grouped[(day, pid)]
        item[0] += _number(_value(row, "cost"))
        item[1] += _number(_value(row, "ad_gmv"))
        item[2:] = [cat, op]
    for (day, pid), (cost, gmv, cat, op) in grouped.items():
        table = "daily_metrics" if _table_exists(conn, "daily_metrics") else "fact_ad_daily"
        if table == "daily_metrics":
            data = {"date": day, "store_id": store_id, "product_id": pid, "product_name": None, "pay_amount": 0, "refund_amount": 0, "pay_qty": 0, "visitors": 0, "buyers": 0, "cost": cost, "ad_gmv": gmv, "ad_cost": cost, "category_id": cat, "operator_id": op}
        else: data = {"date": day, "store_id": store_id, "product_id": pid, "category_id": cat, "operator_id": op, "cost": cost, "ad_gmv": gmv}
        result = _upsert(conn, table, data, ("date", "store_id", "product_id")); stats[result] += 1
    conn.commit(); return stats

def _table_exists(conn, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None
