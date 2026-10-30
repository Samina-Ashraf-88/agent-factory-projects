"""Income investigation: what came in, from where, and how reliably."""
from __future__ import annotations

import pandas as pd

from .cadence import detect_cadence, span_months


def analyze_income(df: pd.DataFrame) -> dict:
    income = df[df["transaction_type"] == "income"]
    start, end = df["date"].min().date(), df["date"].max().date()
    months = span_months(start, end)
    total = round(float(income["amount"].sum()), 2)

    sources = []
    for source, group in income.groupby("income_source", sort=False):
        dates = [d.date() for d in group["date"]]
        cadence, hit, _ = detect_cadence(dates)
        regular = cadence is not None and len(set(dates)) >= 3 and hit >= 0.8
        sources.append({
            "source": source,
            "total": round(float(group["amount"].sum()), 2),
            "count": len(group),
            "average": round(float(group["amount"].mean()), 2),
            "dates": sorted(dates),
            "cadence": cadence if regular else None,
            "frequency": f"Regular ({cadence})" if regular else f"Irregular ({len(group)} in the period)",
            "regular": regular,
        })
    sources.sort(key=lambda s: -s["total"])

    monthly = income.groupby(income["date"].dt.strftime("%Y-%m"))["amount"].sum().round(2)
    return {
        "total": total,
        "sources": sources,
        "monthly": {k: float(v) for k, v in monthly.items()},
        "average_monthly": round(total / months, 2) if months else 0.0,
        "irregular": [s["source"] for s in sources if not s["regular"]],
    }
