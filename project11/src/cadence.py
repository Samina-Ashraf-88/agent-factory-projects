"""Shared date-rhythm helpers for income and recurring-charge detection."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from statistics import median

BANDS = {  # allowed days between charges
    "weekly": (6, 8),
    "fortnightly": (13, 15),
    "monthly": (27, 33),
    "quarterly": (85, 95),
    "annual": (350, 380),
}


def detect_cadence(dates: list[date]) -> tuple[str | None, float, float]:
    """Return (cadence name, share of gaps inside its band, median gap in days)."""
    unique = sorted(set(dates))
    if len(unique) < 2:
        return None, 0.0, 0.0
    gaps = [(b - a).days for a, b in zip(unique, unique[1:])]
    typical = median(gaps)
    for name, (low, high) in BANDS.items():
        if low <= typical <= high:
            return name, sum(low <= g <= high for g in gaps) / len(gaps), typical
    return None, 0.0, typical


def add_cadence(when: date, cadence: str) -> date:
    if cadence == "weekly":
        return when + timedelta(days=7)
    if cadence == "fortnightly":
        return when + timedelta(days=14)
    months = {"monthly": 1, "quarterly": 3, "annual": 12}[cadence]
    index = when.month - 1 + months
    year, month = when.year + index // 12, index % 12 + 1
    return date(year, month, min(when.day, monthrange(year, month)[1]))


def span_days(start: date, end: date) -> int:
    return (end - start).days + 1


def span_months(start: date, end: date) -> float:
    return span_days(start, end) / 30.4375
