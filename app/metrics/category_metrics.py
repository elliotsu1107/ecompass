from __future__ import annotations

import sqlite3

from app.metrics.common import period_expr, q, ratio, settlement


def category_metrics(connection: sqlite3.Connection, store_id: str, start: str, end: str, granularity: str) -> dict:
    period = period_expr(granularity=granularity)
    rows = q(connection, f"""
        SELECT category_id, SUM(pay_amount) pay_amount, SUM(refund_amount) refund_amount,
               SUM(pay_amount - COALESCE(refund_amount, 0)) settlement_amount,
               (SELECT COALESCE(SUM(a.cost),0) FROM fact_ad_daily a
                WHERE a.store_id=p.store_id AND a.category_id=p.category_id AND a.date BETWEEN ? AND ?) ad_cost
        FROM fact_product_daily p
        WHERE store_id=? AND date BETWEEN ? AND ? GROUP BY category_id ORDER BY category_id
    """, (start, end, store_id, start, end))
    target_rows = q(connection, "SELECT category_id, SUM(target_amount) target_amount FROM targets_category WHERE store_id=? AND month BETWEEN ? AND ? GROUP BY category_id", (store_id, start[:7], end[:7]))
    targets = {r["category_id"]: float(r["target_amount"] or 0) for r in target_rows}
    result = []
    for row in rows:
        pay, refund, cost = float(row["pay_amount"] or 0), float(row["refund_amount"] or 0), float(row["ad_cost"] or 0)
        net = settlement(pay, refund)
        result.append({"category_id": row["category_id"], "pay_amount": pay, "refund_amount": refund, "settlement_amount": net, "ad_cost": cost, "cost_ratio": ratio(cost, net), "target_amount": targets.get(row["category_id"], 0.0)})
    return {"store_id": store_id, "rows": result}
