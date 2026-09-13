import sqlite3
from pathlib import Path

import pytest

from app.admin import reset
from app.admin.reset import ClearConfirmationError, clear_business_data
from app.db import init_db


def seeded_connection(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "data" / "ecompass.db"
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO stores (id, name, platform) VALUES (1, '旗舰店', '平台')")
    conn.commit()
    return conn


def test_clear_requires_confirmation_and_creates_backup(tmp_path):
    conn = seeded_connection(tmp_path)

    result = clear_business_data(conn, tmp_path / "data", "CLEAR")

    backup_path = Path(result["backup_path"])
    assert backup_path.suffix == ".db"
    assert backup_path.exists()
    assert result["before"]["stores"] == 1
    assert result["after"]["stores"] == 0
    assert (tmp_path / "data" / "backups").exists()
    backup_conn = sqlite3.connect(backup_path)
    assert backup_conn.execute("SELECT COUNT(*) FROM stores").fetchone()[0] == 1
    backup_conn.close()
    conn.close()


def test_clear_wrong_confirmation_does_not_change_data(tmp_path):
    conn = seeded_connection(tmp_path)

    with pytest.raises(ClearConfirmationError):
        clear_business_data(conn, tmp_path / "data", "clear")

    assert conn.execute("SELECT COUNT(*) FROM stores").fetchone()[0] == 1
    assert not (tmp_path / "data" / "backups").exists()
    conn.close()


def test_clear_rolls_back_when_delete_fails(tmp_path, monkeypatch):
    conn = seeded_connection(tmp_path)
    monkeypatch.setattr(reset, "CLEAR_TABLES", ("stores", "missing_table"))

    with pytest.raises(sqlite3.Error):
        clear_business_data(conn, tmp_path / "data", "CLEAR")

    assert conn.execute("SELECT COUNT(*) FROM stores").fetchone()[0] == 1
    conn.close()


def test_clear_table_whitelist_contains_only_business_tables():
    assert reset.CLEAR_TABLES == (
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
