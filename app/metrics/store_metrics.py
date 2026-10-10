from __future__ import annotations

import sqlite3

from app.metrics.common import period_expr, q, ratio, settlement


def store_metrics(connection: sqlite3.Connection, store_id: str, start: str, end: str, granularity: str) -> dict:
    """店铺指标：结算额取店铺日报，推广花费统一取推广报表按日期求和。"""
    period = period_expr(granularity=granularity)
    rows = q(
        connection,
        f"""
        SELECT {period} AS period, SUM(pay_amount) AS pay_amount,
               SUM(refund_amount) AS refund_amount
        FROM fact_store_daily
        WHERE store_id = ? AND date BETWEEN ? AND ?
        GROUP BY {period} ORDER BY period
        """,
        (store_id, start, end),
    )
    ad_rows = q(
        connection,
        f"""
        SELECT {period} AS period, SUM(cost) AS ad_cost
        FROM fact_ad_daily
        WHERE store_id = ? AND date BETWEEN ? AND ?
        GROUP BY {period}
        """,
        (store_id, start, end),
    )
    ad_by_period = {row["period"]: float(row["ad_cost"] or 0) for row in ad_rows}
    timeline = [
        _metric_row(row, ad_by_period.get(row["period"], 0.0)) | {"period": row["period"]}
        for row in rows
    ]
    totals = _total(timeline)
    target = q(
        connection,
        "SELECT SUM(target_amount) AS target_amount FROM targets_store WHERE store_id = ? AND month BETWEEN ? AND ?",
        (store_id, start[:7], end[:7]),
    )[0]["target_amount"]
    totals["target_amount"] = float(target or 0)
    return {"store_id": store_id, "summary": totals, "timeline": timeline}


def _metric_row(row: dict, ad_cost: float) -> dict:
    pay = float(row["pay_amount"] or 0)
    refund = float(row["refund_amount"] or 0)
    net = settlement(pay, refund)
    return {"pay_amount": pay, "refund_amount": refund, "settlement_amount": net, "ad_cost": ad_cost, "cost_ratio": ratio(ad_cost, net)}


def _total(rows: list[dict]) -> dict:
    pay = sum(row["pay_amount"] for row in rows)
    refund = sum(row["refund_amount"] for row in rows)
    ad_cost = sum(row["ad_cost"] for row in rows)
    net = settlement(pay, refund)
    return {"pay_amount": pay, "refund_amount": refund, "settlement_amount": net, "ad_cost": ad_cost, "cost_ratio": ratio(ad_cost, net)}
