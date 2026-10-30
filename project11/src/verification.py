"""Trust gate: the engine must reproduce known answers on the synthetic wallet.

The expected numbers live only here, never in the analysis code. They are compared
against what the engine computes from the raw rows, and two of them are also recounted
without the engine (plain csv module, no normalization) to catch engine-wide mistakes.
"""
from __future__ import annotations

import csv
from pathlib import Path

SAMPLE_WALLET = Path(__file__).resolve().parent.parent / "data" / "sample_wallet.csv"
TOLERANCE = 0.005


def _recount_raw(path: Path) -> tuple[float, float]:
    income = prime = 0.0
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            text, amount = row["Description"].lower(), float(row["Amount"])
            if "pocket money" in text or "tutoring" in text:
                income += amount
            if "prime" in text and "video" in text:
                prime += -amount
    return income, prime


def _check(name: str, expected, actual) -> dict:
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        passed = actual is not None and abs(float(actual) - expected) < TOLERANCE
    else:
        passed = expected == actual
    return {"name": name, "expected": expected, "actual": actual, "passed": bool(passed)}


def run_checks(results: dict, sample_path: Path = SAMPLE_WALLET) -> list[dict]:
    prime = next((r for r in results["recurring"] if r["merchant"] == "PrimeVideo"), None)
    delivery = next((c for c in results["spending"]["categories"] if c["category"] == "Food delivery"), None)
    july8 = [d for d in results["duplicates"]
             if d["merchant"] == "Foodpanda" and (d["date"].month, d["date"].day) == (7, 8)]
    raw_income, raw_prime = _recount_raw(sample_path)
    return [
        _check("Total income", 23000, results["income"]["total"]),
        _check("PrimeVideo total", 796, prime["total"] if prime else None),
        _check("PrimeVideo monthly charges found", 4, prime["occurrences"] if prime and prime["cadence"] == "monthly" else None),
        _check("Foodpanda 8 July pairs flagged", 1, len(july8)),
        _check("Food delivery total", 4050, delivery["net"] if delivery else None),
        _check("Biggest leak is food delivery", "Food delivery", results["leak"].get("category")),
        _check("Raw-row recount: total income", raw_income, results["income"]["total"]),
        _check("Raw-row recount: PrimeVideo", raw_prime, prime["total"] if prime else None),
    ]


def passed(checks: list[dict]) -> bool:
    return all(c["passed"] for c in checks)


def format_table(checks: list[dict]) -> str:
    lines = [f"{'Verification':<36}{'Expected':>16}{'Actual':>16}  Result", "-" * 78]
    for c in checks:
        def show(v):
            return f"{v:,.2f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)
        lines.append(f"{c['name']:<36}{show(c['expected']):>16}{show(c['actual']):>16}  {'PASS' if c['passed'] else 'FAIL'}")
    return "\n".join(lines)
