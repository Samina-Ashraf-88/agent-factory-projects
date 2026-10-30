"""Find charges that repeat on a rhythm, using merchant, dates and amounts together.

Same amount twice is never enough. Tiers:
  confirmed - 3+ dates, at least 80% of gaps on rhythm, amounts steady
  probable  - a subscription-type merchant on rhythm with a changing price or only
              2 charges so far, or 2 charges about a year apart
  possible  - a rhythm that is only partly there; needs a human to look
"""
from __future__ import annotations

from datetime import date
from statistics import mean, pstdev

import pandas as pd

from .cadence import BANDS, add_cadence, detect_cadence

CONFIRMED = "Confirmed recurring pattern"
PROBABLE = "Probable subscription"
POSSIBLE = "Possible recurring - manual review"
SUBSCRIPTION_LIKE = {"Subscriptions", "Mobile & internet", "Bills & rent"}
AMOUNT_TOLERANCE = 0.02


def _variation(amounts: list[float]) -> float:
    return pstdev(amounts) / mean(amounts) if len(amounts) > 1 and mean(amounts) else 0.0


def _tier(n_dates: int, cadence: str | None, hit: float, variation: float, sub_like: bool) -> str | None:
    if cadence is None:
        return None
    if n_dates >= 3:
        if hit >= 0.8 and variation <= 0.05:
            return CONFIRMED
        if hit >= 0.8 and variation <= 0.25 and sub_like:
            return PROBABLE
        if 0.5 <= hit and variation <= 0.05:
            return POSSIBLE
        return None
    if n_dates == 2 and variation <= 0.05:
        if cadence == "annual":
            return PROBABLE
        if cadence == "monthly":
            return PROBABLE if sub_like else POSSIBLE
    return None


def _clusters(group: pd.DataFrame) -> list[pd.DataFrame]:
    """Split a merchant's charges into groups of near-identical amounts."""
    clusters: list[list[int]] = []
    centres: list[float] = []
    for index, value in zip(group.index, -group["amount"]):
        for i, centre in enumerate(centres):
            if abs(value - centre) <= centre * AMOUNT_TOLERANCE:
                clusters[i].append(index)
                break
        else:
            clusters.append([index])
            centres.append(value)
    return [group.loc[ids] for ids in clusters]


def _record(merchant: str, group: pd.DataFrame, cadence: str, hit: float, tier: str, as_of: date) -> dict:
    dates = sorted(d.date() for d in group["date"])
    unique = sorted(set(dates))
    amounts = [round(float(-a), 2) for a in group["amount"]]
    category = group["category"].iloc[0]
    next_expected = add_cadence(unique[-1], cadence)
    grace = BANDS[cadence][1] - BANDS[cadence][0]
    active = (as_of - next_expected).days <= grace
    gaps = [(b - a).days for a, b in zip(unique, unique[1:])]
    amount_text = (
        f"same amount ({amounts[0]:,.2f}) every time" if max(amounts) - min(amounts) < 0.01
        else f"amounts between {min(amounts):,.2f} and {max(amounts):,.2f}"
    )
    if len(gaps) <= 6:
        gap_text = ", ".join(map(str, gaps))
    else:
        gap_text = f"always {gaps[0]}" if min(gaps) == max(gaps) else f"{min(gaps)} to {max(gaps)}"
    evidence = (
        f"{len(unique)} charges from one merchant, {amount_text}; "
        f"days between charges: {gap_text} ({hit:.0%} fit a {cadence} rhythm)."
    )
    if not active:
        evidence += f" The charge expected around {next_expected:%d %b %Y} did not appear, so it may have stopped."
    return {
        "merchant": merchant,
        "category": category,
        "kind": "Subscription" if category == "Subscriptions" else "Recurring bill or habit",
        "tier": tier,
        "cadence": cadence,
        "amount": round(float(pd.Series(amounts).median()), 2),
        "occurrences": len(unique),
        "charges": len(amounts),
        "total": round(sum(amounts), 2),
        "dates": unique,
        "first": unique[0],
        "last": unique[-1],
        "hit_ratio": round(hit, 2),
        "active": active,
        "next_expected": next_expected,
        "evidence": evidence,
        "row_ids": list(group.index),
    }


def detect_recurring(df: pd.DataFrame, as_of: date | None = None) -> list[dict]:
    expenses = df[df["transaction_type"] == "expense"]
    as_of = as_of or df["date"].max().date()
    found: list[dict] = []
    for merchant, group in expenses.groupby("merchant", sort=False):
        amounts = [float(-a) for a in group["amount"]]
        dates = [d.date() for d in group["date"]]
        sub_like = group["category"].iloc[0] in SUBSCRIPTION_LIKE
        cadence, hit, _ = detect_cadence(dates)
        tier = _tier(len(set(dates)), cadence, hit, _variation(amounts), sub_like)
        if tier:
            found.append(_record(merchant, group, cadence, hit, tier, as_of))
            continue
        # A merchant can mix one steady plan with one-off purchases.
        for cluster in _clusters(group):
            cluster_dates = [d.date() for d in cluster["date"]]
            if len(set(cluster_dates)) < 2:
                continue
            cadence, hit, _ = detect_cadence(cluster_dates)
            tier = _tier(len(set(cluster_dates)), cadence, hit, 0.0, sub_like)
            if tier:
                found.append(_record(merchant, cluster, cadence, hit, tier, as_of))
    rank = {CONFIRMED: 0, PROBABLE: 1, POSSIBLE: 2}
    found.sort(key=lambda r: (rank[r["tier"]], r["kind"] != "Subscription", -r["total"]))
    return found
