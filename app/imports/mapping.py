"""Column mapping profiles keyed by store, file type and header signature."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Mapping


def header_signature(headers: list[str] | tuple[str, ...]) -> str:
    canonical = "\x1f".join(str(h).strip() for h in headers)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ensure_mapping_table(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS column_map_profiles (
      store_id TEXT NOT NULL, file_type TEXT NOT NULL, header_signature TEXT NOT NULL,
      mapping_json TEXT NOT NULL, PRIMARY KEY(store_id, file_type, header_signature)
    )""")
    conn.commit()


def save_mapping(conn: sqlite3.Connection, store_id: str, file_type: str,
                 headers: list[str], mapping: Mapping[str, str]) -> str:
    ensure_mapping_table(conn)
    signature = header_signature(headers)
    conn.execute("INSERT OR REPLACE INTO column_map_profiles VALUES (?, ?, ?, ?)",
                 (store_id, file_type, signature, json.dumps(dict(mapping), ensure_ascii=False)))
    conn.commit()
    return signature


def load_mapping(conn: sqlite3.Connection, store_id: str, file_type: str,
                 headers: list[str]) -> dict[str, str] | None:
    ensure_mapping_table(conn)
    row = conn.execute("SELECT mapping_json FROM column_map_profiles WHERE store_id=? AND file_type=? AND header_signature=?",
                       (store_id, file_type, header_signature(headers))).fetchone()
    return json.loads(row[0]) if row else None
