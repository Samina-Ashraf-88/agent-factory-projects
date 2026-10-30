"""Spending investigation: categories, merchants, trends. Refunds offset their category."""
from __future__ import annotations

import pandas as pd

from .cadence import span_months
from .normalizer import CATEGORY_CLASS


def analyze_spending(df: pd.DataFrame, income_monthly_average: float = 0.0) -> dict:
    expenses = df[df["transaction_type"] == "expense"]
    refunds = df[df["transaction_type"] == "refund"]
    start, end = df["date"].min().date(), df["date"].max().date()
    months = span_months(start, end)

    gross_total = round(float(-expenses["amount"].sum()), 2)
    refund_total = round(float(refunds["amount"].sum()), 2)
    gross = -expenses.groupby("category")["amount"].sum()
    refunded = refunds.groupby("category")["amount"].sum()
    counts = expenses.groupby("category")["amount"].count()

    categories = []
    for category in gross.index.union(refunded.index):
        net = float(gross.get(category, 0.0) - refunded.get(category, 0.0))
        categories.append({
            "category": category,
            "spending_class": CATEGORY_CLASS.get(category, "Unknown"),
            "gross": round(float(gross.get(category, 0.0)), 2),
            "refunds": round(float(refunded.get(category, 0.0)), 2),
            "net": round(net, 2),
            "count": int(counts.get(category, 0)),
        })
    net_total = sum(max(c["net"], 0) for c in categories)
    for c in categories:
        c["percent"] = round(100 * max(c["net"], 0) / net_total, 1) if net_total else 0.0
    categories.sort(key=lambda c: -c["net"])

    largest = expenses.nsmallest(10, "amount")
    merchants = (-expenses.groupby("merchant")["amount"].sum()).sort_values(ascending=False)
    merchant_counts = expenses.groupby("merchant")["amount"].count()
    month_key = expenses["date"].dt.strftime("%Y-%m")
    monthly = (-expenses.groupby(month_key)["amount"].sum()).round(2)
    by_class = (-expenses.groupby("spending_class")["amount"].sum()).round(2)

    # "Small" scales with the wallet so it works in any currency: 5% of a month's income.
    small_limit = income_monthly_average * 0.05 or float(-expenses["amount"].median() if len(expenses) else 0)
    small = expenses[-expenses["amount"] <= small_limit]
    small_groups = [
        {"merchant": m, "count": len(g), "total": round(float(-g["amount"].sum()), 2),
         "average": round(float(-g["amount"].mean()), 2)}
        for m, g in small.groupby("merchant") if len(g) >= 4
    ]
    small_groups.sort(key=lambda s: -s["total"])

    return {
        "gross_total": gross_total,
        "refund_total": refund_total,
        "net_total": round(gross_total - refund_total, 2),
        "average_monthly": round(gross_total / months, 2) if months else 0.0,
        "categories": categories,
        "largest_category": categories[0]["category"] if categories else None,
        "largest_transactions": [
            {"date": r.date.date(), "merchant": r.merchant, "amount": round(-r.amount, 2), "category": r.category}
            for r in largest.itertuples()
        ],
        "merchants": [
            {"merchant": m, "total": round(float(v), 2), "count": int(merchant_counts[m])}
            for m, v in merchants.head(10).items()
        ],
        "monthly": {k: float(v) for k, v in monthly.items()},
        "by_class": {k: float(v) for k, v in by_class.items()},
        "small_limit": round(small_limit, 2),
        "small_purchases": small_groups,
        "small_total": round(float(-small["amount"].sum()), 2),
        "small_count": len(small),
    }
