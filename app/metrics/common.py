from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from typing import Any


def q(connection: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(sql, tuple(params)).fetchall()]


def settlement(pay: float | None, refund: float | None) -> float:
    return float(pay or 0) - float(refund or 0)


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    denominator = float(denominator or 0)
    return float(numerator or 0) / denominator if denominator else None


def period_expr(column: str = "date", granularity: str = "day") -> str:
    if granularity == "month":
        return f"substr({column}, 1, 7)"
    if granularity != "day":
        raise ValueError("granularity must be day or month")
    return column


def validate_granularity(value: str) -> str:
    if value not in {"day", "month"}:
        raise ValueError("granularity must be day or month")
    return value
