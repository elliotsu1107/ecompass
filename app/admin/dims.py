from __future__ import annotations

from typing import Any

_ALLOWED = {"stores", "operators", "categories"}


class DimensionStore:
    def __init__(self, connection):
        self.connection = connection

    def upsert(self, table: str, values: dict[str, Any]) -> None:
        if table not in _ALLOWED or not values:
            raise ValueError("invalid dimension")
        columns = list(values)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(f"{column}=excluded.{column}" for column in columns if column != "id")
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}"
        self.connection.execute(sql, [values[column] for column in columns])
        self.connection.commit()

    def list(self, table: str) -> list[dict[str, Any]]:
        if table not in _ALLOWED:
            raise ValueError("invalid dimension")
        cursor = self.connection.execute(f"SELECT * FROM {table} ORDER BY id")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(row) if hasattr(row, "keys") else dict(zip(columns, row)) for row in rows]
