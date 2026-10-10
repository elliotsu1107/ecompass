from __future__ import annotations

import re
import sqlite3

PRODUCT_PATCH_FIELDS = ("category_id", "operator_id", "status")
_MONTH = re.compile(r"^\d{4}-\d{2}$")
_BATCH_LIMIT = 500


class ProductStore:
    def __init__(self, connection): self.connection = connection

    def upsert(self, value):
        cols = ["store_id", "product_id", "name", "category_id", "operator_id"]
        self.connection.execute("INSERT INTO products (store_id,product_id,name,category_id,operator_id) VALUES (?,?,?,?,?) ON CONFLICT(store_id,product_id) DO UPDATE SET name=excluded.name,category_id=excluded.category_id,operator_id=excluded.operator_id", [value.get(c) for c in cols])
        self.connection.commit()

    def list(self):
        rows = self.connection.execute("SELECT store_id,product_id,name,category_id,operator_id FROM products ORDER BY store_id,product_id").fetchall()
        return [dict(row) if hasattr(row, "keys") else dict(zip(("store_id","product_id","name","category_id","operator_id"), row)) for row in rows]

    def update(self, store_id, product_id, value):
        required = ("product_id", "name", "category_id", "operator_id")
        if any(value.get(field) in (None, "") for field in required):
            raise ValueError("缺少必填项：商品 ID、名称、类目、运营")
        new_product_id = str(value["product_id"]).strip()
        if not new_product_id:
            raise ValueError("商品 ID 不能为空")
        cursor = self.connection.execute(
            "SELECT 1 FROM products WHERE store_id=? AND product_id=?",
            (store_id, product_id),
        )
        if cursor.fetchone() is None:
            raise LookupError("商品不存在")
        try:
            self.connection.execute("BEGIN")
            if new_product_id != product_id:
                self.connection.execute(
                    "INSERT INTO products (store_id, product_id, name, category_id, operator_id)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (store_id, new_product_id, value["name"], value["category_id"], value["operator_id"]),
                )
                self.connection.execute(
                    "UPDATE fact_product_daily SET product_id=?"
                    " WHERE store_id=? AND product_id=?",
                    (new_product_id, store_id, product_id),
                )
                self.connection.execute(
                    "UPDATE fact_ad_daily SET product_id=?"
                    " WHERE store_id=? AND product_id=?",
                    (new_product_id, store_id, product_id),
                )
                self.connection.execute(
                    "DELETE FROM products WHERE store_id=? AND product_id=?",
                    (store_id, product_id),
                )
            else:
                self.connection.execute(
                    "UPDATE products SET name=?, category_id=?, operator_id=?"
                    " WHERE store_id=? AND product_id=?",
                    (value["name"], value["category_id"], value["operator_id"], store_id, product_id),
                )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            if "UNIQUE" in str(exc).upper():
                raise ValueError("该店铺下已存在相同商品 ID") from exc
            raise
        except Exception:
            self.connection.rollback()
            raise

    def batch_update(self, items, patch, *, sync_daily: bool = False, months=()):
        """批量更新商品档案，可选同步指定月份的日报归属。

        items: [{store_id, product_id}]；patch: category_id / operator_id / status。
        sync_daily=True 时把指定月份的 fact_product_daily 与 fact_ad_daily
        的 category_id、operator_id 覆盖为新值。
        """
        if not items:
            raise ValueError("请先选择要修改的商品")
        if len(items) > _BATCH_LIMIT:
            raise ValueError(f"单次最多修改 {_BATCH_LIMIT} 条")
        changes = {
            field: value
            for field, value in patch.items()
            if field in PRODUCT_PATCH_FIELDS and value not in (None, "")
        }
        if not changes:
            raise ValueError("没有需要更新的字段，请选择类目、运营或状态")
        months = [str(month) for month in months if _MONTH.match(str(month))]
        if sync_daily and not months:
            raise ValueError("同步日报时必须选择要覆盖的月份")

        updated = []
        failed = []
        daily_rows = 0
        assignments = ", ".join(f"{field}=?" for field in changes)
        try:
            self.connection.execute("BEGIN")
            for item in items:
                store_id = item.get("store_id")
                product_id = str(item.get("product_id") or "").strip()
                if store_id in (None, "") or not product_id:
                    failed.append({"item": item, "reason": "缺少店铺或商品 ID"})
                    continue
                cursor = self.connection.execute(
                    f"UPDATE products SET {assignments} WHERE store_id=? AND product_id=?",
                    (*(changes[field] for field in changes), store_id, product_id),
                )
                if cursor.rowcount == 0:
                    failed.append({"item": item, "reason": "商品不存在"})
                    continue
                updated.append({"store_id": store_id, "product_id": product_id})
                if sync_daily:
                    daily_rows += self._sync_daily(store_id, product_id, changes, months)
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError(f"类目或运营不存在：{exc}") from exc
        except Exception:
            self.connection.rollback()
            raise
        return {
            "updated": len(updated),
            "failed": failed,
            "daily_rows": daily_rows,
            "months": months,
        }

    def _sync_daily(self, store_id, product_id, changes, months) -> int:
        """把商品在指定月份的日报归属覆盖为档案当前值。"""
        row = self.connection.execute(
            "SELECT category_id, operator_id FROM products WHERE store_id=? AND product_id=?",
            (store_id, product_id),
        ).fetchone()
        if row is None:
            return 0
        placeholders = ",".join("?" for _ in months)
        params = [row["category_id"], row["operator_id"], store_id, product_id, *months]
        changed = 0
        for table in ("fact_product_daily", "fact_ad_daily"):
            cursor = self.connection.execute(
                f"UPDATE {table} SET category_id=?, operator_id=?"
                f" WHERE store_id=? AND product_id=? AND substr(date, 1, 7) IN ({placeholders})",
                params,
            )
            changed += cursor.rowcount or 0
        return changed

    def delete(self, store_id, product_id):
        try:
            cursor = self.connection.execute("DELETE FROM products WHERE store_id=? AND product_id=?", (store_id, product_id))
        except Exception as exc:
            self.connection.rollback()
            raise RuntimeError("商品正在被报表引用，无法删除") from exc
        if cursor.rowcount == 0:
            raise LookupError("商品不存在")
        self.connection.commit()
