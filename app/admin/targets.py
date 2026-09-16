from __future__ import annotations

_KEYS = {
    "targets_store": ("month", "store_id"),
    "targets_category": ("month", "store_id", "category_id"),
    "targets_operator": ("month", "operator_id"),
}


class TargetStore:
    def __init__(self, connection):
        self.connection = connection

    def _upsert(self, table, values):
        keys = _KEYS[table]
        columns = list(values)
        updates = ", ".join(f"{c}=excluded.{c}" for c in columns if c not in keys)
        self.connection.execute(
            f"INSERT INTO {table} ({','.join(columns)})"
            f" VALUES ({','.join('?' for _ in columns)})"
            f" ON CONFLICT({','.join(keys)}) DO UPDATE SET {updates}",
            [values[c] for c in columns],
        )
        self.connection.commit()

    def upsert_store(self, month, store_id, amount):
        self._upsert(
            "targets_store",
            {"month": month, "store_id": store_id, "target_amount": amount},
        )

    def upsert_category(self, month, store_id, category_id, amount):
        self._upsert(
            "targets_category",
            {
                "month": month,
                "store_id": store_id,
                "category_id": category_id,
                "target_amount": amount,
            },
        )

    def upsert_operator(self, month, operator_id, amount):
        self._upsert(
            "targets_operator",
            {"month": month, "operator_id": operator_id, "target_amount": amount},
        )

    def list_month(self, month: str) -> dict[str, dict[str, float]]:
        def collect(sql: str, key_columns: tuple[str, ...]) -> dict[str, float]:
            cursor = self.connection.execute(sql, (month,))
            values: dict[str, float] = {}
            for row in cursor.fetchall():
                record = dict(row) if hasattr(row, "keys") else row
                key = ":".join(str(record[column]) for column in key_columns)
                values[key] = float(record["target_amount"] or 0)
            return values

        return {
            "store": collect(
                "SELECT store_id, target_amount FROM targets_store WHERE month = ?",
                ("store_id",),
            ),
            "category": collect(
                "SELECT store_id, category_id, target_amount FROM targets_category"
                " WHERE month = ?",
                ("store_id", "category_id"),
            ),
            "operator": collect(
                "SELECT operator_id, target_amount FROM targets_operator WHERE month = ?",
                ("operator_id",),
            ),
        }
