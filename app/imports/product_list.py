"""Import the product list that maps product IDs to category and operator."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

ALIASES = {
    "store": ("店铺名称", "店铺", "店铺名", "store"),
    "product_id": ("商品ID", "商品id", "商品 ID", "宝贝ID", "product_id"),
    "name": ("商品名称", "商品名", "宝贝名称", "标题", "name"),
    "category": ("类目", "类目名称", "分类", "商品类目", "category"),
    "operator": ("运营负责人", "运营", "负责人", "运营人员", "operator"),
}


def _pick(row: Mapping[str, Any], field: str) -> Any:
    for alias in ALIASES[field]:
        if alias in row:
            return row[alias]
    return None


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def import_products(connection, rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "新增": 0,
        "更新": 0,
        "跳过": 0,
        "新建运营": 0,
        "新建类目": 0,
        "未匹配店铺": 0,
        "未匹配店铺名称": [],
    }
    stores = {
        str(row[1]).strip(): row[0]
        for row in connection.execute("SELECT id, name FROM stores")
    }
    operators = {
        str(row[1]).strip(): row[0]
        for row in connection.execute("SELECT id, name FROM operators")
    }
    categories = {
        str(row[1]).strip(): row[0]
        for row in connection.execute("SELECT id, name FROM categories")
    }
    seen: set[tuple[Any, str]] = set()

    for row in rows:
        store_name = _text(_pick(row, "store"))
        product_id = _text(_pick(row, "product_id"))
        name = _text(_pick(row, "name"))
        category_name = _text(_pick(row, "category"))
        operator_name = _text(_pick(row, "operator"))
        if not (store_name and product_id and category_name and operator_name):
            stats["跳过"] += 1
            continue

        store_id = stores.get(store_name)
        if store_id is None:
            stats["未匹配店铺"] += 1
            if store_name not in stats["未匹配店铺名称"]:
                stats["未匹配店铺名称"].append(store_name)
            continue

        operator_id = operators.get(operator_name)
        if operator_id is None:
            cursor = connection.execute(
                "INSERT INTO operators (name) VALUES (?)", (operator_name,)
            )
            operator_id = int(cursor.lastrowid)
            operators[operator_name] = operator_id
            stats["新建运营"] += 1

        category_id = categories.get(category_name)
        if category_id is None:
            cursor = connection.execute(
                "INSERT INTO categories (name, operator_id) VALUES (?, ?)",
                (category_name, operator_id),
            )
            category_id = int(cursor.lastrowid)
            categories[category_name] = category_id
            stats["新建类目"] += 1

        key = (store_id, product_id)
        exists = key in seen or connection.execute(
            "SELECT 1 FROM products WHERE store_id=? AND product_id=?", key
        ).fetchone() is not None
        connection.execute(
            "INSERT INTO products (store_id, product_id, name, category_id, operator_id)"
            " VALUES (?,?,?,?,?)"
            " ON CONFLICT(store_id, product_id) DO UPDATE SET"
            " name=excluded.name, category_id=excluded.category_id,"
            " operator_id=excluded.operator_id",
            (store_id, product_id, name or product_id, category_id, operator_id),
        )
        seen.add(key)
        stats["更新" if exists else "新增"] += 1

    connection.commit()
    return stats
