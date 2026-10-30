"""Flag possible duplicate charges for a human to check. Never edits or removes anything."""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

LABEL = "Possible duplicate — manual verification required"
# Buying the same thing twice in a day is ordinary here (a return bus trip, a second coffee).
OFTEN_REPEATED = {"Transport", "Cafes & snacks", "Groceries"}
REFUND_WINDOW_DAYS = 30
EVIDENCE_ORDER = {"Stronger": 0, "Moderate": 1, "Weaker": 2}


def _minutes(time_text: str) -> int | None:
    if not time_text:
        return None
    hours, minutes = time_text.split(":")
    return int(hours) * 60 + int(minutes)


def _assess(group: pd.DataFrame, refunds: pd.DataFrame) -> tuple[str, list[str]]:
    reasons = [
        f"{len(group)} charges share the same date, merchant ({group['merchant'].iloc[0]}) "
        f"and amount ({-group['amount'].iloc[0]:,.2f})."
    ]
    strength = "Moderate"
    refs = [r for r in group["reference"] if r]
    times = sorted(m for m in (_minutes(t) for t in group["time"]) if m is not None)
    if len(refs) != len(set(refs)):
        strength = "Stronger"
        reasons.append("They carry the same transaction reference.")
    elif len(times) == len(group):
        gap = min(b - a for a, b in zip(times, times[1:]))
        if gap <= 10:
            strength = "Stronger"
            reasons.append(f"They are only {gap} minute(s) apart.")
        elif gap > 60:
            strength = "Weaker"
            reasons.append(f"They are {gap // 60}h {gap % 60}m apart, which fits two separate purchases.")
        else:
            reasons.append(f"They are {gap} minutes apart.")
    else:
        reasons.append("The export has no times, so they cannot be told apart by time of day.")
    if group["category"].iloc[0] in OFTEN_REPEATED:
        if strength == "Moderate":
            strength = "Weaker"
        reasons.append(f"Repeat purchases are common in {group['category'].iloc[0]}.")

    day, merchant, amount = group["date"].iloc[0], group["merchant"].iloc[0], -group["amount"].iloc[0]
    match = refunds[
        (refunds["merchant"] == merchant) & (refunds["amount"].round(2) == round(amount, 2))
        & (refunds["date"] >= day) & (refunds["date"] <= day + timedelta(days=REFUND_WINDOW_DAYS))
    ]
    if not match.empty:
        strength = "Weaker"
        reasons.append(f"A matching refund appears on {match['date'].iloc[0]:%d %b %Y}, so it may already be reversed.")
    return strength, reasons


def _record(group: pd.DataFrame, refunds: pd.DataFrame) -> dict:
    strength, reasons = _assess(group, refunds)
    amount = round(float(-group["amount"].iloc[0]), 2)
    return {
        "label": LABEL,
        "date": group["date"].iloc[0].date(),
        "merchant": group["merchant"].iloc[0],
        "amount": amount,
        "count": len(group),
        "extra_amount": round(amount * (len(group) - 1), 2),
        "evidence_strength": strength,
        "explanation": " ".join(reasons),
        "times": [t for t in group["time"] if t],
        "rows": list(group["source"]),
    }


def detect_duplicates(df: pd.DataFrame) -> list[dict]:
    expenses = df[df["transaction_type"] == "expense"]
    refunds = df[df["transaction_type"] == "refund"]
    flagged = []
    grouped_rows: set[int] = set()
    for _, group in expenses.groupby(["date", "merchant", "amount"], sort=True):
        if len(group) >= 2:
            flagged.append(_record(group, refunds))
            grouped_rows.update(group.index)

    # The same reference on charges that differ in some other way is also worth a look.
    with_ref = expenses[expenses["reference"] != ""]
    for ref, group in with_ref.groupby("reference", sort=True):
        if len(group) >= 2 and not set(group.index) <= grouped_rows:
            rows = ", ".join(group["source"])
            flagged.append({
                "label": LABEL,
                "date": group["date"].iloc[0].date(),
                "merchant": group["merchant"].iloc[0],
                "amount": round(float(-group["amount"].iloc[0]), 2),
                "count": len(group),
                "extra_amount": round(float(-group["amount"].iloc[1:].sum()), 2),
                "evidence_strength": "Stronger",
                "explanation": f"{len(group)} charges share one transaction reference ({rows}) "
                               "though their other details differ.",
                "times": [t for t in group["time"] if t],
                "rows": list(group["source"]),
            })
    flagged.sort(key=lambda d: (EVIDENCE_ORDER[d["evidence_strength"]], -d["extra_amount"]))
    return flagged
