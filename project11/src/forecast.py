"""Estimate what is left by the next pocket-money date, with every assumption stated.

Ends the day before that money arrives. Three estimates, differing only in spending:
  expected        - known recurring charges + average daily variable spending
  conservative    - also probable subscriptions + a 75th-percentile week (or the average, if higher)
  higher-spending - also probable subscriptions + the most expensive week seen
Income that has no regular rhythm is left out and shown separately as an upside,
unless include_irregular_income is set.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from .cadence import add_cadence
from .subscription_detector import CONFIRMED, PROBABLE


def _primary_income(income: dict) -> dict | None:
    regular = [s for s in income["sources"] if s["regular"]]
    named = [s for s in regular if s["source"] == "Pocket money"]
    if named:
        return named[0]
    return regular[0] if regular else None


def infer_next_income(income: dict, as_of: date) -> tuple[date | None, dict | None]:
    primary = _primary_income(income)
    if primary is None:
        return None, None
    upcoming = primary["dates"][-1]
    while upcoming <= as_of:
        upcoming = add_cadence(upcoming, primary["cadence"])
    return upcoming, primary


def _due(last: date, cadence: str, as_of: date, until: date) -> list[date]:
    dates, upcoming = [], add_cadence(last, cadence)
    while upcoming < until:
        if upcoming > as_of:
            dates.append(upcoming)
        upcoming = add_cadence(upcoming, cadence)
    return dates


def _resolve_balance(df, opening_balance, current_balance) -> tuple[float | None, str]:
    if current_balance is not None:
        return float(current_balance), "Current balance you supplied."
    if opening_balance is not None:
        value = round(float(opening_balance) + float(df["amount"].sum()), 2)
        return value, ("Opening balance you supplied plus every transaction in the file, transfers included. "
                       "Correct only if the export is complete.")
    with_balance = df[df["balance"].notna()]
    if not with_balance.empty:
        return float(with_balance.iloc[-1]["balance"]), "Latest balance shown in the export."
    return None, ("No balance was provided, so this is an estimate of net cash flow only, "
                  "not a verified account balance.")


def forecast_remaining(
    df: pd.DataFrame, income: dict, recurring: list[dict], *,
    as_of: date | None = None, next_income_date: date | None = None,
    opening_balance: float | None = None, current_balance: float | None = None,
    include_irregular_income: bool = False,
) -> dict:
    last_transaction = df["date"].max().date()
    as_of = as_of or last_transaction
    balance, balance_basis = _resolve_balance(df, opening_balance, current_balance)
    inferred_date, primary = infer_next_income(income, as_of)
    date_source = "you supplied it"
    if next_income_date is None:
        next_income_date = inferred_date
        date_source = "inferred from the regular payment pattern"
    if next_income_date is None:
        return {
            "status": "needs_date",
            "message": "No regular income pattern was found, so the next pocket-money date cannot be inferred. "
                       "Re-run with --next-pocket-money YYYY-MM-DD.",
            "balance": balance, "balance_basis": balance_basis,
        }
    if next_income_date <= as_of:
        return {
            "status": "needs_date",
            "message": f"The next pocket-money date ({next_income_date}) is not after the forecast start ({as_of}). "
                       "Re-run with a later --next-pocket-money date.",
            "balance": balance, "balance_basis": balance_basis,
        }
    days = (next_income_date - as_of).days - 1  # whole days after as_of, before the money arrives

    # Scheduled charges inside the window.
    certain, cautious = [], []
    recurring_rows: set = set()
    for item in recurring:
        if item["tier"] in (CONFIRMED, PROBABLE):
            recurring_rows.update(item["row_ids"])
        if not item["active"] or item["tier"] not in (CONFIRMED, PROBABLE):
            continue
        dates = _due(item["last"], item["cadence"], as_of, next_income_date)
        if dates:
            entry = {"merchant": item["merchant"], "dates": dates, "amount": item["amount"],
                     "total": round(item["amount"] * len(dates), 2), "tier": item["tier"]}
            (certain if item["tier"] == CONFIRMED else cautious).append(entry)
    certain_total = round(sum(e["total"] for e in certain), 2)
    cautious_total = round(sum(e["total"] for e in cautious), 2)

    # Variable spending: everything that is not a scheduled charge, in 7-day windows counted back.
    expenses = df[df["transaction_type"] == "expense"]
    variable = expenses[~expenses.index.isin(recurring_rows)]
    first_day = df["date"].min().date()
    history_days = (last_transaction - first_day).days + 1
    daily_mean = float(-variable["amount"].sum()) / history_days if history_days else 0.0
    weeks = []
    window_end = last_transaction
    while (window_end - first_day).days + 1 >= 7:
        window_start = window_end - timedelta(days=6)
        mask = (variable["date"].dt.date >= window_start) & (variable["date"].dt.date <= window_end)
        weeks.append(float(-variable.loc[mask, "amount"].sum()))
        window_end = window_start - timedelta(days=1)
    # Lumpy spending can put a 75th-percentile week below the average; caution must never mean less spending.
    daily_p75 = max(float(np.percentile(weeks, 75)) / 7, daily_mean) if weeks else daily_mean
    daily_max = max(max(weeks) / 7, daily_mean) if weeks else daily_mean

    # Income inside the window.
    known_income, upside = [], []
    for source in income["sources"]:
        if source is primary:
            continue
        if source["regular"]:
            dates = _due(source["dates"][-1], source["cadence"], as_of, next_income_date)
            if dates:
                known_income.append({"source": source["source"], "total": round(source["average"] * len(dates), 2),
                                     "dates": dates})
        else:
            upside.append({"source": source["source"], "amount": source["average"], "count": source["count"]})
    income_total = round(sum(i["total"] for i in known_income), 2)
    if include_irregular_income:
        months = history_days / 30.4375
        for item in upside:
            expected = round(item["amount"] * item["count"] / months * (days / 30.4375), 2)
            known_income.append({"source": item["source"], "total": expected, "dates": []})
            income_total = round(income_total + expected, 2)

    def scenario(name: str, daily: float, scheduled: float, note: str) -> dict:
        spending = round(daily * days + scheduled, 2)
        net = round(income_total - spending, 2)
        return {"name": name, "daily_variable": round(daily, 2), "scheduled": round(scheduled, 2),
                "spending": spending, "income": income_total, "net_change": net,
                "remaining": round(balance + net, 2) if balance is not None else None, "note": note}

    scenarios = [
        scenario("Conservative estimate", daily_p75, certain_total + cautious_total,
                 "Probable subscriptions charge; variable spending at a 75th-percentile week."),
        scenario("Expected estimate", daily_mean, certain_total,
                 "Confirmed recurring charges; variable spending at the historical daily average."),
        scenario("Higher-spending estimate", daily_max, certain_total + cautious_total,
                 "Probable subscriptions charge; every day runs like the most expensive week seen."),
    ]

    assumptions = [
        f"Forecast starts after {as_of:%d %b %Y} and covers {days} day(s), ending the day before "
        f"{next_income_date:%d %b %Y} ({date_source}).",
        f"Variable spending is based on {history_days} days of history, including one-off purchases "
        "and any possible duplicates, so it reflects how money actually left, not an ideal month.",
        "Confirmed recurring charges continue at their usual amount and rhythm; those that appear to have stopped are left out.",
        "No further transfers to savings or other accounts are assumed.",
    ]
    if include_irregular_income:
        assumptions.append("Forecast assumes irregular income continues at the observed frequency and amount.")
    elif upside:
        names = ", ".join(u["source"] for u in upside)
        assumptions.append(f"Irregular income ({names}) is not counted, because it has no reliable rhythm. "
                           "Any such payment would be extra.")
    uncertainties = [
        "This is an estimate from past behaviour, not a guarantee of a future balance.",
        "Possible recurring charges awaiting manual review are not included.",
    ]
    if as_of == last_transaction:
        uncertainties.append(f"Anything spent after the last transaction in the file ({last_transaction:%d %b %Y}) is not known.")
    if len(weeks) < 4:
        uncertainties.append("Less than four weeks of history, so the spending estimates are weak.")

    return {
        "status": "ok",
        "as_of": as_of,
        "next_income_date": next_income_date,
        "date_source": date_source,
        "days": days,
        "balance": balance,
        "balance_basis": balance_basis,
        "scheduled_certain": certain,
        "scheduled_probable": cautious,
        "known_income": known_income,
        "upside_income": upside if not include_irregular_income else [],
        "next_income_amount": primary["average"] if primary else None,
        "scenarios": scenarios,
        "assumptions": assumptions,
        "uncertainties": uncertainties,
    }
