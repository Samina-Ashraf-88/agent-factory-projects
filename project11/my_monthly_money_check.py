#!/usr/bin/env python3
"""
MY MONTHLY MONEY CHECK
======================

WHAT IT DOES
  Reads your wallet or bank export and works out where the money went, what keeps
  charging you, which charges may have been billed twice, your biggest reducible
  spending, and roughly what will be left by your next pocket money. It then writes a
  private HTML report. Everything runs on this computer and nothing is uploaded.

WHAT IT EXPECTS
  A .csv, .tsv, .txt, .xlsx or .json export with a date column and either an amount
  column or separate debit/credit columns. Column names can vary, and header lines
  above the table are fine. Your original file is only read, never changed.

PLUS AND MINUS
  Positive = money received. Negative = money spent. Refunds and reversals are tracked
  apart and reduce their spending category. Moves between your own accounts, such as
  to savings, count as neither income nor spending.

REPEAT CHARGES
  The merchant, the amounts and the days between charges are judged together; the same
  amount twice is never enough. 3+ on-rhythm charges of a steady amount are "confirmed";
  weaker patterns are "probable" or "possible - manual review". A repeat charge is not
  assumed to be unwanted.

POSSIBLE DUPLICATES
  2+ charges with the same date, merchant and amount are labelled "Possible duplicate -
  manual verification required", with times, references and refunds noted as evidence.
  Nothing is deleted or called fraud.

HOW TO RUN IT NEXT MONTH
  python my_monthly_money_check.py --input wallet_export.csv

  Useful extras:
    --next-pocket-money 2026-12-15   when your next pocket money arrives
    --current-balance 3200           what is in the wallet now (or --opening-balance)
    --output-dir private_reports     where the report goes (default: reports/)
    --currency PKR                   a label for amounts; nothing is converted
    --date-format mdy                if 03/04/2026 means March 4
    --inspect                        show how the file was understood, then stop
  Add several files after --input to combine overlapping exports without double counting.

LIMITATIONS
  Categories come from keyword rules and can be wrong. Merchants it does not recognize go
  to "Other expenses". An annual charge needs over a year of history to be seen. Without
  a balance the forecast is only an estimate of cash flow. A forecast is never a guarantee.

TRUST CHECK
  Each run first reproduces known answers on the fictional data/sample_wallet.csv. If any
  check fails it stops and writes no report. This script needs the src/ and data/ folders
  beside it, and uses this project's .venv automatically when it exists.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _ensure_dependencies() -> None:
    try:
        import openpyxl  # noqa: F401
        import pandas  # noqa: F401
    except ImportError:
        venv_python = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
            raise SystemExit(subprocess.call([str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]]))
        raise SystemExit("Missing packages. Run: python -m pip install -r requirements.txt")


if __name__ == "__main__":
    _ensure_dependencies()
    sys.path.insert(0, str(ROOT))
    from src.main import main

    raise SystemExit(main())
