"""Read a wallet export (CSV, TSV, Excel, JSON) into standard columns.

Nothing is silently dropped: rows that cannot be interpreted land in
`ImportResult.invalid` with a reason. Original files are only ever read.
"""
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from .normalizer import redact

ALIASES = {
    "date": ["date", "transactiondate", "txndate", "trandate", "posteddate", "postingdate",
             "valuedate", "bookingdate", "datetime", "timestamp", "createdat", "completeddate"],
    "description": ["description", "merchant", "merchantname", "details", "transactiondetails",
                    "narration", "particulars", "payee", "memo", "remarks", "name", "title",
                    "note", "notes"],
    "amount": ["amount", "amt", "transactionamount", "txnamount", "netamount", "value", "total"],
    "debit": ["debit", "debitamount", "withdrawal", "withdrawals", "moneyout", "paidout", "out", "spent"],
    "credit": ["credit", "creditamount", "deposit", "deposits", "moneyin", "paidin", "in", "received"],
    "type": ["type", "transactiontype", "txntype", "drcr", "crdr", "direction", "indicator"],
    "category": ["category", "transactioncategory"],
    "balance": ["balance", "runningbalance", "closingbalance", "availablebalance", "balanceafter"],
    "reference": ["reference", "ref", "referenceno", "referencenumber", "transactionid", "txnid",
                  "id", "utr", "receiptno"],
    "currency": ["currency", "ccy"],
    "time": ["time", "transactiontime", "txntime"],
}
NEGATIVE_HINTS = {"dr", "debit", "out", "expense", "withdrawal", "payment", "purchase", "sent"}
POSITIVE_HINTS = {"cr", "credit", "in", "income", "deposit", "received"}
TEXT_DATE_FORMATS = ["%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%d-%b-%Y", "%d-%b-%y",
                     "%b %d %Y", "%B %d %Y", "%a, %d %b %Y"]
EXCEL_EPOCH = date(1899, 12, 30)


@dataclass
class ImportResult:
    frame: pd.DataFrame
    invalid: list[dict] = field(default_factory=list)
    repeated: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    column_maps: dict[str, dict] = field(default_factory=dict)
    date_orders: dict[str, str] = field(default_factory=dict)
    rows_read: int = 0
    currencies: list[str] = field(default_factory=list)


def _squash(text: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def read_table(path: Path) -> list[list]:
    """Return every row of the file as a list of raw cell values."""
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        import openpyxl
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            return [list(row) for row in book.worksheets[0].iter_rows(values_only=True)]
        finally:
            book.close()
    if suffix == ".json":
        return _read_json(path)
    if suffix in (".csv", ".tsv", ".txt"):
        return _read_delimited(path)
    raise ValueError(f"Unsupported file type '{suffix}'. Use .csv, .tsv, .txt, .xlsx or .json.")


def _read_delimited(path: Path) -> list[list]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    sample = "\n".join(text.splitlines()[:30])
    counts = {sep: sample.count(sep) for sep in ",;\t|"}
    delimiter = max(counts, key=counts.get) if any(counts.values()) else ","
    return [row for row in csv.reader(text.splitlines(), delimiter=delimiter)]


def _read_json(path: Path) -> list[list]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        if not lists:
            raise ValueError("JSON file has no list of transactions.")
        data = max(lists, key=len)
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("JSON must be a list of transaction objects, or an object containing one.")
    flat = pd.json_normalize(data, sep="_")
    header = [str(c) for c in flat.columns]
    return [header] + [[None if _is_nan(v) else v for v in row] for row in flat.itertuples(index=False)]


def _is_nan(value) -> bool:
    return isinstance(value, float) and math.isnan(value)


def find_header(rows: list[list]) -> tuple[int, dict[str, int]]:
    """Find the header row (exports often start with a few lines of preamble)."""
    for index, row in enumerate(rows[:30]):
        mapping = map_columns(row)
        if "date" in mapping and ("amount" in mapping or "debit" in mapping or "credit" in mapping):
            return index, mapping
    raise ValueError(
        "Could not find a header row with a date column and an amount column "
        "(or debit/credit columns) in the first 30 rows."
    )


def map_columns(header: list) -> dict[str, int]:
    cells = [_squash(c) if c is not None else "" for c in header]
    mapping: dict[str, int] = {}
    for field_name, names in ALIASES.items():
        for name in names:  # alias order is preference order
            if name in cells:
                mapping[field_name] = cells.index(name)
                break
    if "amount" not in mapping:  # "Amount (PKR)", "Amount in CR"
        for i, cell in enumerate(cells):
            if cell.startswith("amount"):
                mapping["amount"] = i
                break
    return mapping


def parse_amount(value) -> float | None:
    """Parse '1,234.50', '(450)', '-450', 'Rs. 450', '450 DR'. None when unreadable."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return None if not math.isfinite(value) else round(float(value), 2)
    text = str(value).strip().replace("−", "-").replace(" ", " ")
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    match = re.search(r"\b(dr|cr)\.?\s*$", text, re.I)
    if match:
        negative = negative or match.group(1).lower() == "dr"
        text = text[: match.start()]
    text = re.sub(r"(?i)\b(rs|pkr|inr|usd|eur|gbp|aed|sar)\b\.?", "", text)
    if re.search(r"[A-Za-z]", text):
        return None
    if "-" in text:
        negative = True
    text = re.sub(r"[^\d.,]", "", text)
    if not re.search(r"\d", text):
        return None
    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text:
        text = text.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{2,3})*,\d{3}", text) else text.replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        number = float(text)
    except ValueError:
        return None
    return round(-number if negative else number, 2)


def infer_date_order(values: list) -> str:
    """Return 'dmy', 'mdy', or 'ambiguous' by looking for parts that cannot be a month."""
    first_big = second_big = False
    for value in values:
        match = re.match(r"\s*(\d{1,2})[/\-.](\d{1,2})[/\-.]\d{2,4}", str(value)) if value is not None else None
        if match:
            first_big = first_big or int(match.group(1)) > 12
            second_big = second_big or int(match.group(2)) > 12
    if first_big and not second_big:
        return "dmy"
    if second_big and not first_big:
        return "mdy"
    return "ambiguous"


def parse_date(value, order: str = "dmy") -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 20000 < value < 80000:  # Excel serial number
            return EXCEL_EPOCH + timedelta(days=int(value))
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        match = re.match(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", text)
        if match:
            return date(int(match[1]), int(match[2]), int(match[3]))
        match = re.match(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})(?!\d)", text)
        if match:
            a, b, year = int(match[1]), int(match[2]), int(match[3])
            year = year + 2000 if year < 100 else year
            return date(year, b, a) if order == "dmy" else date(year, a, b)
    except ValueError:
        return None
    cleaned = re.sub(r"\s+\d{1,2}:\d{2}.*$", "", text)
    for fmt in TEXT_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(*values) -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, datetime):
            return value.strftime("%H:%M") if (value.hour or value.minute) else ""
        if hasattr(value, "hour"):
            return f"{value.hour:02d}:{value.minute:02d}"
        match = re.search(r"\b(\d{1,2}):(\d{2})(?::\d{2})?\s*([ap]m)?", str(value), re.I)
        if match:
            hour = int(match[1]) % 12 + (12 if match[3].lower() == "pm" else 0) if match[3] else int(match[1])
            return f"{hour:02d}:{match[2]}"
    return ""


def _cell(row: list, mapping: dict[str, int], name: str):
    index = mapping.get(name)
    if index is None or index >= len(row):
        return None
    value = row[index]
    return None if isinstance(value, str) and not value.strip() else value


def _row_amount(row, mapping) -> tuple[float | None, str | None]:
    """Return (signed amount, reason it failed)."""
    if "amount" in mapping:
        raw = _cell(row, mapping, "amount")
        if raw is None:
            if "debit" not in mapping and "credit" not in mapping:
                return None, "missing amount"
        else:
            amount = parse_amount(raw)
            if amount is None:
                return None, "unreadable amount"
            hint = str(_cell(row, mapping, "type") or "").strip().lower().rstrip(".")
            if amount > 0 and hint in NEGATIVE_HINTS:
                amount = -amount
            elif amount < 0 and hint in POSITIVE_HINTS:
                amount = -amount
            return amount, None
    debit_raw, credit_raw = _cell(row, mapping, "debit"), _cell(row, mapping, "credit")
    if debit_raw is None and credit_raw is None:
        return None, "missing amount"
    debit = parse_amount(debit_raw) if debit_raw is not None else 0.0
    credit = parse_amount(credit_raw) if credit_raw is not None else 0.0
    if debit is None or credit is None:
        return None, "unreadable amount"
    return round(abs(credit) - abs(debit), 2), None


def _import_file(path: Path, result: ImportResult, forced_order: str | None) -> list[dict]:
    rows = read_table(path)
    header_index, mapping = find_header(rows)
    header = rows[header_index]
    result.column_maps[path.name] = {k: str(header[v]) for k, v in mapping.items()}
    body = rows[header_index + 1:]

    date_values = [_cell(r, mapping, "date") for r in body]
    order = forced_order or infer_date_order(date_values)
    if order == "ambiguous":
        if any(isinstance(v, str) and re.match(r"\s*\d{1,2}[/\-.]\d{1,2}[/\-.]", v) for v in date_values):
            result.warnings.append(
                f"{path.name}: dates could be day/month or month/day. Read as day/month; "
                "pass --date-format mdy if that is wrong."
            )
            result.date_orders[path.name] = "ambiguous - read as day/month"
        else:
            result.date_orders[path.name] = "unambiguous (ISO, text month, or spreadsheet date)"
        order = "dmy"
    else:
        result.date_orders[path.name] = {"dmy": "day/month/year", "mdy": "month/day/year"}[order]

    records: list[dict] = []
    for offset, row in enumerate(body):
        line = header_index + offset + 2  # 1-based, counting the header
        if all(c is None or (isinstance(c, str) and not c.strip()) for c in row):
            continue
        result.rows_read += 1
        description = _cell(row, mapping, "description")
        preview = redact(str(description if description is not None else row))[:80]
        date_raw = _cell(row, mapping, "date")
        when = parse_date(date_raw, order)
        problem = None
        if date_raw is None:
            problem = "missing date"
        elif when is None:
            problem = f"unreadable date ({redact(str(date_raw))[:30]})"
        amount, amount_problem = _row_amount(row, mapping)
        problem = problem or amount_problem
        if not problem and amount == 0:
            problem = "zero amount"
        if problem:
            result.invalid.append({"file": path.name, "row": line, "reason": problem, "preview": preview})
            continue
        balance_raw = _cell(row, mapping, "balance")
        records.append({
            "date": pd.Timestamp(when),
            "time": _parse_time(_cell(row, mapping, "time"), date_raw),
            "original_description": str(description).strip() if description is not None else "",
            "amount": amount,
            "reference": str(_cell(row, mapping, "reference") or "").strip(),
            "category_hint": str(_cell(row, mapping, "category") or "").strip(),
            "type_hint": str(_cell(row, mapping, "type") or "").strip().lower(),
            "balance": parse_amount(balance_raw) if balance_raw is not None else None,
            "currency": str(_cell(row, mapping, "currency") or "").strip().upper(),
            "source_file": path.name,
            "source_row": line,
        })
    return records


def _drop_repeats(per_file: list[list[dict]], result: ImportResult) -> list[dict]:
    """Remove records that are the *same record exported twice*, never real look-alikes.

    Two identical rows inside one file with no reference are kept: that is exactly
    what a double charge looks like. A row is only removed when it carries a repeated
    reference within a file, or when overlapping files both contain it (a row is
    kept as many times as the most any single file contains it).
    """
    kept: list[dict] = []
    kept_counts: Counter = Counter()
    for records in per_file:
        in_file: Counter = Counter()
        for rec in records:
            key = (rec["date"], rec["time"], rec["original_description"], rec["amount"], rec["reference"])
            in_file[key] += 1
            same_ref_repeat = bool(rec["reference"]) and in_file[key] > 1
            if same_ref_repeat or in_file[key] <= kept_counts[key]:
                result.repeated.append({
                    "file": rec["source_file"], "row": rec["source_row"],
                    "reason": "same reference repeated" if same_ref_repeat else "already in an earlier file",
                    "preview": redact(rec["original_description"])[:80],
                })
                continue
            kept_counts[key] += 1
            kept.append(rec)
    return kept


def import_wallet(paths: list[Path | str], date_order: str | None = None) -> ImportResult:
    result = ImportResult(frame=pd.DataFrame())
    per_file = [_import_file(Path(p), result, date_order) for p in paths]
    records = _drop_repeats(per_file, result)
    if not records:
        return result
    frame = pd.DataFrame(records)
    frame = frame.sort_values(["date", "time"], kind="stable").reset_index(drop=True)
    result.frame = frame

    result.currencies = sorted({c for c in frame["currency"] if c})
    if len(result.currencies) > 1:
        result.warnings.append(
            f"More than one currency in this export ({', '.join(result.currencies)}). "
            "Amounts are added as-is with no conversion, so totals are unreliable."
        )
    if (frame["amount"] > 0).all():
        result.warnings.append(
            "Every amount is positive, so spending cannot be told apart from money received. "
            "Check that this export has signs, a debit/credit column, or a Dr/Cr column."
        )
    blank = int((frame["original_description"] == "").sum())
    if blank:
        result.warnings.append(f"{blank} row(s) have no description; they are kept as unclassified.")
    gaps = frame["date"].drop_duplicates().diff().dt.days
    if not gaps.empty and gaps.max() > 31:
        result.warnings.append(
            f"There is a gap of {int(gaps.max())} days with no transactions. "
            "The export may be incomplete, which would make averages too low."
        )
    if result.invalid:
        result.warnings.append(f"{len(result.invalid)} row(s) could not be interpreted; see the import notes.")
    if result.repeated:
        result.warnings.append(f"{len(result.repeated)} repeated record(s) were counted once; see the import notes.")
    return result
