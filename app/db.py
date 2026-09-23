import sqlite3
from pathlib import Path


_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(path: Path) -> None:
    with connect_db(path) as connection:
        connection.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        migrations = {
            "product_name": "TEXT",
            "buyers": "INTEGER NOT NULL DEFAULT 0",
        }
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(fact_product_daily)")
        }
        for column, definition in migrations.items():
            if column not in columns:
                connection.execute(
                    f"ALTER TABLE fact_product_daily ADD COLUMN {column} {definition}"
                )
