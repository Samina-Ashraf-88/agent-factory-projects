"""Command line and pipeline: import, trust gate, analyze, report."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import crosscheck, verification
from .cadence import span_months
from .duplicate_detector import detect_duplicates
from .forecast import forecast_remaining
from .importer import ImportResult, import_wallet
from .income_analyzer import analyze_income
from .leak_detector import find_leak
from .normalizer import normalize
from .report_generator import build_html, write_report
from .spending_analyzer import analyze_spending
from .subscription_detector import detect_recurring

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "reports"


def analyze(imported: ImportResult, *, as_of=None, next_income_date=None, opening_balance=None,
            current_balance=None, include_irregular_income=False) -> dict:
    df = normalize(imported.frame)
    income = analyze_income(df)
    spending = analyze_spending(df, income["average_monthly"])
    recurring = detect_recurring(df, as_of)
    duplicates = detect_duplicates(df)
    leak = find_leak(df, spending, income, recurring, duplicates)
    forecast = forecast_remaining(
        df, income, recurring, as_of=as_of, next_income_date=next_income_date, opening_balance=opening_balance,
        current_balance=current_balance, include_irregular_income=include_irregular_income,
    )
    transfers = df[df["transaction_type"] == "transfer"]["amount"]
    adjustments = float(df[df["transaction_type"] == "adjustment"]["amount"].sum())
    start, end = df["date"].min().date(), df["date"].max().date()
    return {
        "transactions": df,
        "income": income, "spending": spending, "recurring": recurring, "duplicates": duplicates,
        "leak": leak, "forecast": forecast,
        "review_transfers": sorted(set(df.loc[df["needs_review"], "merchant"])),
        "overview": {
            "start": start, "end": end, "count": len(df), "months": span_months(start, end),
            "net_cash_flow": round(income["total"] + spending["refund_total"] - spending["gross_total"] + adjustments, 2),
            "transfers_out": round(float(-transfers[transfers < 0].sum()), 2),
            "transfers_in": round(float(transfers[transfers > 0].sum()), 2),
            "adjustments": round(adjustments, 2),
        },
        "import": {"invalid": imported.invalid, "repeated": imported.repeated, "warnings": imported.warnings,
                   "rows_read": imported.rows_read},
    }


def run_trust_gate() -> list[dict]:
    sample = verification.SAMPLE_WALLET
    if not sample.exists():
        raise FileNotFoundError(f"The synthetic test wallet is missing: {sample}")
    results = analyze(import_wallet([sample]))
    return verification.run_checks(results, sample)


def print_inspection(imported: ImportResult) -> None:
    print("\nFILE INSPECTION (no analysis run)")
    for name, mapping in imported.column_maps.items():
        print(f"  {name}: columns understood = {mapping}")
        print(f"  Date format: {imported.date_orders.get(name)}")
    print(f"  Rows read: {imported.rows_read}; usable: {len(imported.frame)}; "
          f"invalid: {len(imported.invalid)}; repeats: {len(imported.repeated)}")
    if not imported.frame.empty:
        frame = imported.frame
        print(f"  Period: {frame['date'].min():%d %b %Y} to {frame['date'].max():%d %b %Y}")
        print(f"  Currency column: {', '.join(imported.currencies) or 'none; confirm your currency and pass --currency'}")
        balances = frame["balance"].dropna()
        print(f"  Latest balance in file: {balances.iloc[-1] if not balances.empty else 'none; pass --opening-balance or --current-balance'}")
    for warning in imported.warnings:
        print(f"  WARNING: {warning}")


def print_summary(results: dict, currency: str) -> None:
    def money(v):
        return f"{v:,.2f} {currency}".strip()
    inc, sp, ov, fc, leak = (results[k] for k in ("income", "spending", "overview", "forecast", "leak"))
    print(f"\nPERIOD {ov['start']} to {ov['end']}  |  {ov['count']} transactions")
    print(f"Income {money(inc['total'])}  |  Expenses {money(sp['gross_total'])}  |  Refunds {money(sp['refund_total'])}  |  Net cash flow {money(ov['net_cash_flow'])}")
    print("\nWHERE IT GOES")
    for c in sp["categories"]:
        print(f"  {c['category']:<20}{money(c['net']):>16}{c['percent']:>7.1f}%  {c['count']:>3} charges  [{c['spending_class']}]")
    print("\nREPEAT CHARGES")
    for r in results["recurring"]:
        state = "" if r["active"] else "  (may have stopped)"
        print(f"  {r['merchant']:<22}{money(r['amount']):>12} {r['cadence']:<11} x{r['occurrences']:<3} total {money(r['total']):<14} {r['tier']}{state}")
    if not results["recurring"]:
        print("  None found.")
    print("\nPOSSIBLE DUPLICATES (manual verification required)")
    for d in results["duplicates"]:
        print(f"  {d['date']}  {d['merchant']:<18}{money(d['amount']):>12} x{d['count']}  evidence: {d['evidence_strength']}")
    if not results["duplicates"]:
        print("  None found.")
    print("\nBIGGEST LEAK")
    if leak.get("found"):
        print(f"  {leak['category']}: {money(leak['total'])} over {leak['count']} charges, about {money(leak['monthly_cost'])} a month")
    else:
        print(f"  {leak.get('message')}")
    if leak.get("caveat"):
        print(f"  CAUTION: {leak['caveat']}")
    print("\nFORECAST")
    if fc["status"] == "ok":
        print(f"  Next pocket money {fc['next_income_date']} ({fc['date_source']}); {fc['days']} days to cover")
        print(f"  Balance: {money(fc['balance']) if fc['balance'] is not None else 'unknown (net cash flow estimate only)'}")
        for s in fc["scenarios"]:
            value = s["remaining"] if fc["balance"] is not None else s["net_change"]
            print(f"  {s['name']:<26}spend {money(s['spending']):>14}   {'left' if fc['balance'] is not None else 'change'} {money(value):>14}")
    else:
        print(f"  {fc['message']}")
    for warning in results["import"]["warnings"]:
        print(f"\nNOTE: {warning}")


def _parse_date_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a date in YYYY-MM-DD form")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Investigate a wallet export for leaks, repeat charges and possible duplicates.")
    p.add_argument("--input", nargs="+", required=True, help="wallet export(s): .csv .tsv .txt .xlsx .json")
    p.add_argument("--next-pocket-money", type=_parse_date_arg, help="next pocket-money date, YYYY-MM-DD")
    p.add_argument("--opening-balance", type=float, help="balance just before the first transaction in the file")
    p.add_argument("--current-balance", type=float, help="balance right now (preferred over --opening-balance)")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT, help="where to write the report (default: reports/)")
    p.add_argument("--currency", default="", help="label shown beside amounts, e.g. PKR. No conversion happens.")
    p.add_argument("--date-format", choices=["dmy", "mdy"], help="use when dates like 03/04/2026 are ambiguous")
    p.add_argument("--as-of", type=_parse_date_arg, help="forecast start date (default: last transaction)")
    p.add_argument("--include-irregular-income", action="store_true", help="count irregular income in the forecast at its observed rate")
    p.add_argument("--inspect", action="store_true", help="only show how the file was understood; no analysis")
    p.add_argument("--export-sanitized", type=Path, metavar="DIR", help="write a sanitized dataset for an optional second-model check (local only)")
    p.add_argument("--compare", type=Path, metavar="JSON", help="compare a second model's JSON answer with this analysis")
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)

    print("TRUST GATE: reproducing known answers on the synthetic wallet")
    try:
        checks = run_trust_gate()
    except FileNotFoundError as error:
        print(f"STOPPED: {error}\nThe engine cannot be verified, so no analysis was run.", file=sys.stderr)
        return 2
    print(verification.format_table(checks))
    if not verification.passed(checks):
        print("\nSTOPPED: a known check failed, so these numbers cannot be trusted. No report was written.", file=sys.stderr)
        return 2

    paths = [Path(p) for p in args.input]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print(f"File not found: {', '.join(missing)}", file=sys.stderr)
        return 1
    try:
        imported = import_wallet(paths, args.date_format)
    except (ValueError, OSError) as error:
        print(f"Could not read the wallet: {error}", file=sys.stderr)
        return 1

    if args.inspect:
        print_inspection(imported)
        return 0
    if imported.frame.empty:
        print("No usable transactions were found in the file.", file=sys.stderr)
        print_inspection(imported)
        return 1

    results = analyze(imported, as_of=args.as_of, next_income_date=args.next_pocket_money,
                      opening_balance=args.opening_balance, current_balance=args.current_balance,
                      include_irregular_income=args.include_irregular_income)
    results["checks"] = checks
    is_sample = any(p.resolve() == verification.SAMPLE_WALLET.resolve() for p in paths)
    print_summary(results, args.currency)

    report = write_report(build_html(results, currency=args.currency, is_sample=is_sample), args.output_dir)
    print(f"\nPrivate report written to {report}")

    if args.export_sanitized:
        written = crosscheck.export_sanitized(results, args.export_sanitized)
        print("Sanitized files written locally (nothing was sent anywhere):")
        for path in written:
            print(f"  {path}")
    if args.compare:
        rows = crosscheck.compare(crosscheck.build_summary(results), json.loads(args.compare.read_text(encoding="utf-8-sig")))
        text = crosscheck.format_comparison(rows)
        (args.output_dir / "crosscheck_result.md").write_text(text, encoding="utf-8")
        print("\n" + text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
