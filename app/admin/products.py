from __future__ import annotations

import sqlite3


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

    def delete(self, store_id, product_id):
        try:
            cursor = self.connection.execute("DELETE FROM products WHERE store_id=? AND product_id=?", (store_id, product_id))
        except Exception as exc:
            self.connection.rollback()
            raise RuntimeError("商品正在被报表引用，无法删除") from exc
        if cursor.rowcount == 0:
            raise LookupError("商品不存在")
        self.connection.commit()
