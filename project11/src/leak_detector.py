"""Find the biggest reducible spending pattern. Essentials are never called a leak."""
from __future__ import annotations

import pandas as pd

from .cadence import span_days, span_months
from .normalizer import AVOIDABLE, DISCRETIONARY, UNKNOWN

UNCLASSIFIED_CAVEAT_PERCENT = 15


def _net(spending: dict, category: str) -> float:
    return next((c["net"] for c in spending["categories"] if c["category"] == category), 0.0)


def find_leak(df: pd.DataFrame, spending: dict, income: dict, recurring: list[dict], duplicates: list[dict]) -> dict:
    candidates = [c for c in spending["categories"] if c["spending_class"] in (AVOIDABLE, DISCRETIONARY) and c["net"] > 0]
    start, end = df["date"].min().date(), df["date"].max().date()
    months = span_months(start, end)
    days = span_days(start, end)

    monthly_rows = []
    for month in sorted(set(spending["monthly"]) | set(income["monthly"])):
        money_in = income["monthly"].get(month, 0.0)
        money_out = spending["monthly"].get(month, 0.0)
        monthly_rows.append({"month": month, "income": money_in, "spending": money_out,
                             "net": round(money_in - money_out, 2)})

    subscription_total = _net(spending, "Subscriptions")
    delivery_total = _net(spending, "Food delivery")
    grocery_total = _net(spending, "Groceries")
    comparisons = []
    if delivery_total and grocery_total:
        comparisons.append(f"Food delivery ({delivery_total:,.2f}) vs groceries ({grocery_total:,.2f}): "
                           f"{delivery_total / grocery_total:.0%} of the grocery spend.")
    if delivery_total and subscription_total:
        word = "more" if delivery_total > subscription_total else "less"
        comparisons.append(f"Food delivery ({delivery_total:,.2f}) is {word} than all subscriptions "
                           f"combined ({subscription_total:,.2f}).")
    if spending["small_count"]:
        comparisons.append(f"{spending['small_count']} small purchases (each {spending['small_limit']:,.2f} or less) "
                           f"add up to {spending['small_total']:,.2f}.")
    if spending["largest_transactions"]:
        top = spending["largest_transactions"][0]
        comparisons.append(f"Largest single expense: {top['merchant']}, {top['amount']:,.2f}.")
    short_months = [m["month"] for m in monthly_rows if m["net"] < 0]
    if short_months:
        comparisons.append(f"Spending beat income in {len(short_months)} of {len(monthly_rows)} months: "
                           f"{', '.join(short_months)}.")

    unclassified = next((c for c in spending["categories"] if c["spending_class"] == UNKNOWN), None)
    caveat = None
    if unclassified and unclassified["percent"] >= UNCLASSIFIED_CAVEAT_PERCENT:
        caveat = (f"{unclassified['percent']:.0f}% of spending ({unclassified['net']:,.2f}) could not be categorized, "
                  "so this finding could change once those merchants are identified. Check them under "
                  f"{unclassified['category']} first.")

    result = {
        "found": bool(candidates),
        "caveat": caveat,
        "unclassified_merchants": sorted(set(df[(df["transaction_type"] == "expense") & (df["spending_class"] == UNKNOWN)]["merchant"]))[:10],
        "comparisons": comparisons,
        "monthly": monthly_rows,
        "by_class": spending["by_class"],
        "short_months": short_months,
    }
    if not candidates:
        result["message"] = ("No discretionary or avoidable category has any net spending, "
                             "so there is no clear leak in this data.")
        return result

    top = candidates[0]
    category = top["category"]
    rows = df[(df["transaction_type"] == "expense") & (df["category"] == category)]
    merchants = (-rows.groupby("merchant")["amount"].sum()).sort_values(ascending=False)
    by_month = (-rows.groupby(rows["date"].dt.strftime("%Y-%m"))["amount"].sum()).round(2)
    per_week = top["count"] / (days / 7)
    flagged = sum(d["extra_amount"] for d in duplicates
                  if d["merchant"] in set(rows["merchant"]))
    monthly_cost = top["net"] / months
    why = [
        f"It is the largest reducible category, at {top['percent']:.1f}% of all spending.",
        f"It happened about {per_week:.1f} time(s) a week, so no single charge looks alarming.",
    ]
    if len(candidates) > 1:
        runner_up = candidates[1]
        why.append(f"The next reducible category, {runner_up['category']}, is {runner_up['net']:,.2f}.")
    if flagged:
        why.append(f"This total still includes {flagged:,.2f} flagged as a possible duplicate; "
                   f"if confirmed and refunded it would be {top['net'] - flagged:,.2f}.")
    result.update({
        "category": category,
        "spending_class": top["spending_class"],
        "total": top["net"],
        "count": top["count"],
        "percent": top["percent"],
        "per_week": round(per_week, 1),
        "monthly_cost": round(monthly_cost, 2),
        "halving_saves_monthly": round(monthly_cost / 2, 2),
        "merchants": [{"merchant": m, "total": round(float(v), 2)} for m, v in merchants.items()],
        "by_month": {k: float(v) for k, v in by_month.items()},
        "why": why,
        "possible_duplicate_amount": round(flagged, 2),
    })
    return result
