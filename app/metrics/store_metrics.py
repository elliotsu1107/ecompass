from __future__ import annotations

import sqlite3

from app.metrics.common import period_expr, q, ratio, settlement


def store_metrics(connection: sqlite3.Connection, store_id: str, start: str, end: str, granularity: str) -> dict:
    period = period_expr(granularity=granularity)
    rows = q(
        connection,
        f"""
        SELECT {period} AS period, SUM(pay_amount) AS pay_amount,
               SUM(refund_amount) AS refund_amount, SUM(ad_cost) AS ad_cost
        FROM fact_store_daily
        WHERE store_id = ? AND date BETWEEN ? AND ?
        GROUP BY {period} ORDER BY period
        """,
        (store_id, start, end),
    )
    timeline = [_metric_row(row) | {"period": row["period"]} for row in rows]
    totals = _total(timeline)
    target = q(
        connection,
        "SELECT SUM(target_amount) AS target_amount FROM targets_store WHERE store_id = ? AND month BETWEEN ? AND ?",
        (store_id, start[:7], end[:7]),
    )[0]["target_amount"]
    totals["target_amount"] = float(target or 0)
    product = q(
        connection,
        """SELECT SUM(pay_amount) AS pay_amount, SUM(refund_amount) AS refund_amount
           FROM fact_product_daily WHERE store_id = ? AND date BETWEEN ? AND ?""",
        (store_id, start, end),
    )[0]
    store_settlement = totals["settlement_amount"]
    product_settlement = settlement(product["pay_amount"], product["refund_amount"])
    difference = abs(store_settlement - product_settlement)
    difference_ratio = ratio(difference, store_settlement)
    return {
        "store_id": store_id,
        "summary": totals,
        "timeline": timeline,
        "reconciliation": {
            "store_settlement_amount": store_settlement,
            "product_settlement_amount": product_settlement,
            "difference_amount": difference,
            "difference_ratio": difference_ratio,
            "alert": difference > 100 or (difference_ratio is not None and difference_ratio > 0.01),
        },
    }


def _metric_row(row: dict) -> dict:
    pay = float(row["pay_amount"] or 0)
    refund = float(row["refund_amount"] or 0)
    ad_cost = float(row["ad_cost"] or 0)
    net = settlement(pay, refund)
    return {"pay_amount": pay, "refund_amount": refund, "settlement_amount": net, "ad_cost": ad_cost, "cost_ratio": ratio(ad_cost, net)}


def _total(rows: list[dict]) -> dict:
    pay = sum(row["pay_amount"] for row in rows)
    refund = sum(row["refund_amount"] for row in rows)
    ad_cost = sum(row["ad_cost"] for row in rows)
    net = settlement(pay, refund)
    return {"pay_amount": pay, "refund_amount": refund, "settlement_amount": net, "ad_cost": ad_cost, "cost_ratio": ratio(ad_cost, net)}
