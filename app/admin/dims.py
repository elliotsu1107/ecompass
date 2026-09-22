from __future__ import annotations

import sqlite3
from typing import Any

_FIELDS: dict[str, tuple[str, ...]] = {
    "stores": ("name", "platform"),
    "operators": ("name",),
    "categories": ("name", "operator_id"),
}


class DuplicateNameError(ValueError):
    pass


class DimensionStore:
    def __init__(self, connection):
        self.connection = connection

    def create(self, table: str, values: dict[str, Any]) -> int:
        fields = _FIELDS.get(table)
        if fields is None:
            raise ValueError("不支持的资料类型")
        payload = {field: values.get(field) for field in fields}
        missing = [field for field, value in payload.items() if value in (None, "")]
        if missing:
            raise ValueError(f"缺少必填项：{'、'.join(missing)}")
        sql = (
            f"INSERT INTO {table} ({','.join(payload)})"
            f" VALUES ({','.join('?' for _ in payload)})"
        )
        try:
            cursor = self.connection.execute(sql, list(payload.values()))
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            if "UNIQUE" in str(exc).upper():
                raise DuplicateNameError(f"名称已存在：{payload['name']}") from exc
            raise ValueError("关联的资料不存在，请先创建运营人员") from exc
        self.connection.commit()
        return int(cursor.lastrowid)

    def list(self, table: str) -> list[dict[str, Any]]:
        if table not in _FIELDS:
            raise ValueError("不支持的资料类型")
        columns = ", ".join(("id",) + _FIELDS[table])
        cursor = self.connection.execute(f"SELECT {columns} FROM {table} ORDER BY id")
        names = [description[0] for description in cursor.description]
        return [
            dict(row) if hasattr(row, "keys") else dict(zip(names, row))
            for row in cursor.fetchall()
        ]

    def update(self, table: str, item_id: int, values: dict[str, Any]) -> None:
        fields = _FIELDS.get(table)
        if fields is None:
            raise ValueError("不支持的资料类型")
        payload = {field: values.get(field) for field in fields}
        missing = [field for field, value in payload.items() if value in (None, "")]
        if missing:
            raise ValueError(f"缺少必填项：{'、'.join(missing)}")
        try:
            cursor = self.connection.execute(
                f"UPDATE {table} SET {','.join(f'{field}=?' for field in fields)} WHERE id=?",
                [payload[field] for field in fields] + [item_id],
            )
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            if "UNIQUE" in str(exc).upper():
                raise DuplicateNameError(f"名称已存在：{payload['name']}") from exc
            raise ValueError("关联的资料不存在，请先创建运营人员") from exc
        if cursor.rowcount == 0:
            raise LookupError("资料不存在")
        self.connection.commit()

    def delete(self, table: str, item_id: int) -> None:
        if table not in _FIELDS:
            raise ValueError("不支持的资料类型")
        try:
            cursor = self.connection.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise RuntimeError("资料正在被商品、报表或目标引用，无法删除") from exc
        if cursor.rowcount == 0:
            raise LookupError("资料不存在")
        self.connection.commit()
