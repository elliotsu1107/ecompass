from datetime import datetime
from pathlib import Path
import sqlite3


CLEAR_TABLES = (
    "column_maps",
    "column_map_profiles",
    "import_logs",
    "fact_ad_daily",
    "fact_product_daily",
    "fact_store_daily",
    "targets_operator",
    "targets_category",
    "targets_store",
    "products",
    "categories",
    "operators",
    "stores",
)

SCOPE_TABLES = {
    "store_reports": ("fact_store_daily",),
    "product_reports": ("fact_product_daily",),
    "ad_reports": ("fact_ad_daily",),
    "operator_targets": ("targets_operator", "targets_category", "targets_store"),
    "product_list": ("products",),
    "products": ("products",),
    "import_logs": ("column_maps", "column_map_profiles", "import_logs"),
    "stores": ("stores",),
    "categories": ("categories",),
    "operators": ("operators",),
}


class ClearConfirmationError(ValueError):
    pass


class ClearScopeError(ValueError):
    pass


def backup_database(conn: sqlite3.Connection, backup_path: Path) -> None:
    backup_conn = sqlite3.connect(backup_path)
    try:
        conn.backup(backup_conn)
    finally:
        backup_conn.close()


def counts(conn: sqlite3.Connection, tables: tuple[str, ...]) -> dict[str, int]:
    existing_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    return {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in tables
        if table in existing_tables
    }


def _backup(conn: sqlite3.Connection, data_dir: Path) -> Path:
    backup_dir = data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / f"clear-{datetime.now().strftime('%Y%m%d%H%M%S%f')}.db"
    backup_database(conn, path)
    return path


def _ensure_confirmation(confirmation: str) -> None:
    if confirmation != "CLEAR":
        raise ClearConfirmationError("请输入 CLEAR 确认清空")


def _references(conn: sqlite3.Connection, scope: str) -> str | None:
    checks = {
        "stores": (("products", "store_id"), ("fact_store_daily", "store_id"), ("fact_product_daily", "store_id"), ("fact_ad_daily", "store_id"), ("targets_store", "store_id"), ("targets_category", "store_id")),
        "categories": (("products", "category_id"), ("fact_product_daily", "category_id"), ("fact_ad_daily", "category_id"), ("targets_category", "category_id")),
        "operators": (("categories", "operator_id"), ("products", "operator_id"), ("fact_product_daily", "operator_id"), ("fact_ad_daily", "operator_id"), ("targets_operator", "operator_id")),
        "product_list": (("fact_product_daily", "product_id"), ("fact_ad_daily", "product_id")),
    }
    for table, column in checks.get(scope, ()):
        if conn.execute(f"SELECT 1 FROM {table} WHERE {column} IS NOT NULL LIMIT 1").fetchone():
            return table
    return None


def _delete_archives(rows: list[sqlite3.Row | tuple]) -> int:
    deleted = 0
    for row in rows:
        archive_path = row[0]
        if archive_path:
            path = Path(str(archive_path))
            if path.exists() and path.is_file():
                path.unlink()
                deleted += 1
    return deleted


def clear_scope(conn: sqlite3.Connection, data_dir: Path, scope: str, confirmation: str) -> dict:
    _ensure_confirmation(confirmation)
    if scope not in SCOPE_TABLES:
        raise ClearScopeError(f"不支持的清空范围：{scope}")
    reference_scope = "product_list" if scope == "products" else scope
    reference = _references(conn, reference_scope)
    if reference:
        labels = {
            "stores": "店铺正在被商品、报表或目标引用",
            "categories": "类目正在被商品、报表或目标引用",
            "operators": "运营人员正在被类目、商品、报表或目标引用",
            "product_list": "商品正在被报表或目标引用",
        }
        raise ClearScopeError(labels[reference_scope])

    backup_path = _backup(conn, data_dir)
    tables = SCOPE_TABLES[scope]
    before = counts(conn, tables)
    archive_rows = []
    if scope == "import_logs":
        archive_rows = conn.execute("SELECT archive_path FROM import_logs WHERE archive_path IS NOT NULL").fetchall()
    elif scope in {"store_reports", "product_reports", "ad_reports"}:
        file_type = {"store_reports": "store", "product_reports": "product", "ad_reports": "ad"}[scope]
        archive_rows = conn.execute("SELECT archive_path FROM import_logs WHERE file_type=? AND archive_path IS NOT NULL", (file_type,)).fetchall()
    try:
        conn.execute("BEGIN")
        for table in tables:
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    archives_deleted = _delete_archives(archive_rows)
    return {"scope": scope, "backup_path": str(backup_path), "before": before, "after": counts(conn, tables), "archives_deleted": archives_deleted}


def clear_business_data(conn: sqlite3.Connection, data_dir: Path, confirmation: str) -> dict:
    _ensure_confirmation(confirmation)
    backup_path = _backup(conn, data_dir)
    before = counts(conn, CLEAR_TABLES)
    try:
        conn.execute("BEGIN")
        for table in CLEAR_TABLES:
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"backup_path": str(backup_path), "before": before, "after": counts(conn, CLEAR_TABLES)}
