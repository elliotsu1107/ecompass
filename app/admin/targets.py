from __future__ import annotations

class TargetStore:
    def __init__(self, connection): self.connection = connection

    def _upsert(self, table, values):
        columns = list(values)
        keys = {"targets_store": ("month", "store_id"), "targets_category": ("month", "store_id", "category_id"), "targets_operator": ("month", "operator_id")}[table]
        updates = ", ".join(f"{c}=excluded.{c}" for c in columns if c not in keys)
        self.connection.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) ON CONFLICT({','.join(keys)}) DO UPDATE SET {updates}", [values[c] for c in columns])
        self.connection.commit()

    def upsert_store(self, month, store_id, amount): self._upsert("targets_store", {"month": month, "store_id": store_id, "amount": amount})
    def upsert_category(self, month, store_id, category_id, amount): self._upsert("targets_category", {"month": month, "store_id": store_id, "category_id": category_id, "amount": amount})
    def upsert_operator(self, month, operator_id, amount): self._upsert("targets_operator", {"month": month, "operator_id": operator_id, "amount": amount})
