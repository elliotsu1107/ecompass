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


class ClearConfirmationError(ValueError):
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


def clear_business_data(
    conn: sqlite3.Connection, data_dir: Path, confirmation: str
) -> dict:
    if confirmation != "CLEAR":
        raise ClearConfirmationError("请输入 CLEAR 确认清空")

    backup_dir = data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / (
        f"clear-{datetime.now().strftime('%Y%m%d%H%M%S%f')}.db"
    )
    backup_database(conn, backup_path)
    before = counts(conn, CLEAR_TABLES)

    try:
        conn.execute("BEGIN")
        for table in CLEAR_TABLES:
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return {
        "backup_path": str(backup_path),
        "before": before,
        "after": counts(conn, CLEAR_TABLES),
    }
