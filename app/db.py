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
