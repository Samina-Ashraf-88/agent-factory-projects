"""Optional second-opinion support. Writes local files only; nothing is ever transmitted."""
from __future__ import annotations

import csv
import json
from pathlib import Path

TOLERANCE = 0.01

PROMPT = """Below is a sanitized CSV of wallet transactions (positive = money in, negative = money out).
Rows have a transaction_type: income, expense, refund, transfer or adjustment.
Write and run code to compute these, and return ONLY a JSON object with these keys:
  total_income: sum of 'income' rows
  total_expenses: absolute sum of 'expense' rows
  recurring_merchants: merchants charged on a steady weekly/monthly rhythm with a steady amount, 3+ times
  possible_duplicates: list of "YYYY-MM-DD|merchant|amount" where 2+ expense rows match on all three
  largest_category: 'expense' category with the highest total, net of 'refund' rows in that category
  forecast_assumptions: a list of what you would need to assume to forecast the balance
Say so if you could not run code. Do not guess.
"""


def _safe_cell(value):
    """Stop spreadsheet apps from treating a merchant name as a formula."""
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def build_summary(results: dict) -> dict:
    return {
        "total_income": results["income"]["total"],
        "total_expenses": results["spending"]["gross_total"],
        "recurring_merchants": sorted({r["merchant"] for r in results["recurring"] if r["tier"].startswith("Confirmed")}),
        "possible_duplicates": sorted(f"{d['date']}|{d['merchant']}|{d['amount']:.2f}" for d in results["duplicates"]),
        "largest_category": results["spending"]["largest_category"],
        "forecast_assumptions": results["forecast"].get("assumptions", []),
    }


def export_sanitized(results: dict, directory: Path) -> list[Path]:
    """Dates, cleaned merchant, amount, type and category only: no descriptions, references or balances."""
    directory.mkdir(parents=True, exist_ok=True)
    csv_path, summary_path, prompt_path = (directory / n for n in
                                           ("sanitized_transactions.csv", "our_summary.json", "second_model_prompt.txt"))
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["date", "merchant", "amount", "transaction_type", "category"])
        for r in results["transactions"].itertuples():
            writer.writerow([r.date.date().isoformat(), _safe_cell(r.merchant), r.amount, r.transaction_type, r.category])
    summary_path.write_text(json.dumps(build_summary(results), indent=2), encoding="utf-8")
    prompt_path.write_text(PROMPT, encoding="utf-8")
    return [csv_path, summary_path, prompt_path]


def compare(ours: dict, theirs: dict) -> list[dict]:
    rows = []
    for key, mine in ours.items():
        other = theirs.get(key)
        if key == "forecast_assumptions":
            rows.append({"item": key, "ours": f"{len(mine)} listed", "theirs": f"{len(other or [])} listed",
                         "status": "COMPARE BY HAND"})
            continue
        if other is None:
            status = "MISSING"
        elif isinstance(mine, (int, float)):
            status = "AGREE" if isinstance(other, (int, float)) and abs(mine - other) <= TOLERANCE else "DISAGREE"
        elif isinstance(mine, list):
            status = "AGREE" if sorted(map(str, other)) == sorted(map(str, mine)) else "DISAGREE"
        else:
            status = "AGREE" if str(other).strip().lower() == str(mine).strip().lower() else "DISAGREE"
        rows.append({"item": key, "ours": mine, "theirs": other, "status": status})
    return rows


def format_comparison(rows: list[dict]) -> str:
    lines = ["# Second-model comparison", "",
             "Agreement between models is not proof. The transactions and calculations remain the source of truth.", ""]
    lines += [f"- **{r['status']}** `{r['item']}`: ours = {r['ours']}; theirs = {r['theirs']}" for r in rows]
    return "\n".join(lines) + "\n"
