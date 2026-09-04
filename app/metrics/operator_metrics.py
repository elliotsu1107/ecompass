from __future__ import annotations

import sqlite3

from app.metrics.common import q, ratio, settlement


def operator_metrics(connection: sqlite3.Connection, start: str, end: str, granularity: str) -> dict:
    rows = q(connection, """
        SELECT operator_id, SUM(pay_amount) pay_amount, SUM(refund_amount) refund_amount,
          SUM(pay_amount-COALESCE(refund_amount,0)) settlement_amount,
          (SELECT COALESCE(SUM(a.cost),0) FROM fact_ad_daily a WHERE a.operator_id=p.operator_id AND a.date BETWEEN ? AND ?) ad_cost
        FROM fact_product_daily p WHERE date BETWEEN ? AND ? GROUP BY operator_id ORDER BY operator_id
    """, (start, end, start, end))
    targets = {r["operator_id"]: float(r["target_amount"] or 0) for r in q(connection, "SELECT operator_id,SUM(target_amount) target_amount FROM targets_operator WHERE month BETWEEN ? AND ? GROUP BY operator_id", (start[:7], end[:7]))}
    result = []
    for row in rows:
        op = row["operator_id"]
        breakdown = q(connection, "SELECT store_id,SUM(pay_amount-COALESCE(refund_amount,0)) settlement_amount FROM fact_product_daily WHERE operator_id=? AND date BETWEEN ? AND ? GROUP BY store_id ORDER BY store_id", (op, start, end))
        net = float(row["settlement_amount"] or 0)
        stores = [{"store_id": item["store_id"], "settlement_amount": float(item["settlement_amount"] or 0), "share": ratio(item["settlement_amount"], net) or 0.0} for item in breakdown]
        result.append({"operator_id": op, "pay_amount": float(row["pay_amount"] or 0), "refund_amount": float(row["refund_amount"] or 0), "settlement_amount": net, "ad_cost": float(row["ad_cost"] or 0), "cost_ratio": ratio(row["ad_cost"], net), "target_amount": targets.get(op, 0.0), "stores": stores})
    return {"rows": result}
