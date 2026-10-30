import hashlib
import json
from datetime import date

import openpyxl
import pytest

from src.importer import import_wallet, infer_date_order, parse_amount, parse_date
from src.normalizer import classify_type, redact


@pytest.mark.parametrize("text,expected", [
    ("-450", -450), ("450", 450), ("1,234.50", 1234.5), ("(450)", -450), ("Rs. 450", 450), ("450 DR", -450),
    ("450 CR", 450), ("−450", -450), ("1.234,50", 1234.5), ("1,00,000", 100000), ("$12.50", 12.5),
    ("abc", None), ("", None), ("-", None), (None, None),
])
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


def test_date_formats():
    assert parse_date("2026-07-08") == date(2026, 7, 8)
    assert parse_date("08/07/2026", "dmy") == date(2026, 7, 8)
    assert parse_date("07/08/2026", "mdy") == date(2026, 7, 8)
    assert parse_date("8 Jul 2026") == date(2026, 7, 8)
    assert parse_date("Jul 8, 2026") == date(2026, 7, 8)
    assert parse_date("2026-13-45") is None
    assert parse_date("soon") is None
    assert infer_date_order(["25/07/2026"]) == "dmy"
    assert infer_date_order(["07/25/2026"]) == "mdy"
    assert infer_date_order(["03/04/2026"]) == "ambiguous"


def test_ambiguous_dates_warn_and_can_be_overridden(make_csv):
    path = make_csv([("03/04/2026", "", "Cinema", -100)])
    result = import_wallet([path])
    assert any("--date-format" in w for w in result.warnings)
    assert result.frame["date"].iloc[0].month == 4
    assert import_wallet([path], "mdy").frame["date"].iloc[0].month == 3


def test_invalid_rows_are_reported_not_discarded(make_csv):
    result = import_wallet([make_csv([
        ("2026-01-05", "", "Good", -100), ("", "", "No date", -50), ("not a date", "", "Bad date", -50),
        ("2026-01-06", "", "No amount", ""), ("2026-01-06", "", "Bad amount", "lots"), ("2026-01-06", "", "Zero", 0),
    ])])
    assert len(result.frame) == 1
    reasons = [r["reason"] for r in result.invalid]
    assert len(reasons) == 5
    assert "missing date" in reasons and "missing amount" in reasons and "unreadable amount" in reasons and "zero amount" in reasons
    assert result.rows_read == 6


def test_identical_rows_in_one_file_stay_because_they_may_be_a_double_charge(make_csv):
    result = import_wallet([make_csv([("2026-07-08", "", "Foodpanda", -450), ("2026-07-08", "", "Foodpanda", -450)])])
    assert len(result.frame) == 2 and result.repeated == []


def test_overlapping_exports_are_not_double_counted(make_csv):
    rows = [("2026-07-08", "", "Foodpanda", -450), ("2026-07-08", "", "Foodpanda", -450), ("2026-07-09", "", "Cinema", -100)]
    first = make_csv(rows, "a.csv")
    second = make_csv(rows + [("2026-07-10", "", "Bus", -60)], "b.csv")
    result = import_wallet([first, second])
    assert len(result.frame) == 4
    assert len(result.repeated) == 3


def test_same_reference_row_exported_twice_counts_once(make_csv):
    result = import_wallet([make_csv([("2026-07-08", "Foodpanda", -450, "R1"), ("2026-07-08", "Foodpanda", -450, "R1")],
                                     header=("Date", "Description", "Amount", "Reference"))])
    assert len(result.frame) == 1 and len(result.repeated) == 1


def test_varied_columns_preamble_and_debit_credit(tmp_path):
    path = tmp_path / "bank.csv"
    path.write_text(
        "Statement for account\nGenerated 2026\n\n"
        "Txn Date;Narration;Withdrawal;Deposit;Closing Balance\n"
        '25/07/2026;CINEMA;350;;"1,650"\n26/07/2026;Pocket money;;5000;6650\n', encoding="utf-8")
    frame = import_wallet([path]).frame
    assert list(frame["amount"]) == [-350, 5000]
    assert frame["balance"].iloc[-1] == 6650


def test_type_column_signs_unsigned_amounts(make_csv):
    frame = import_wallet([make_csv([("2026-01-05", "Cinema", 100, "Debit"), ("2026-01-06", "Pay", 900, "Credit")],
                                    header=("Date", "Description", "Amount", "Type"))]).frame
    assert list(frame["amount"]) == [-100, 900]


def test_excel_import_matches_csv(tmp_path, make_csv):
    rows = [("2026-07-08", "13:02", "Foodpanda", -450), ("2026-07-15", "09:00", "Pocket money", 5000)]
    csv_frame = import_wallet([make_csv(rows)]).frame
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(["Date", "Time", "Description", "Amount"])
    for row in rows:
        sheet.append(list(row))
    xlsx = tmp_path / "wallet.xlsx"
    book.save(xlsx)
    frame = import_wallet([xlsx]).frame
    assert list(frame["amount"]) == list(csv_frame["amount"])
    assert list(frame["date"]) == list(csv_frame["date"])


def test_excel_real_date_cells(tmp_path):
    from datetime import datetime
    book = openpyxl.Workbook()
    book.active.append(["Date", "Details", "Amount"])
    book.active.append([datetime(2026, 7, 8, 13, 2), "Foodpanda", -450])
    xlsx = tmp_path / "w.xlsx"
    book.save(xlsx)
    frame = import_wallet([xlsx]).frame
    assert frame["date"].iloc[0].date() == date(2026, 7, 8) and frame["time"].iloc[0] == "13:02"


@pytest.mark.parametrize("wrap", [False, True])
def test_json_import(tmp_path, wrap):
    records = [{"date": "2026-07-08", "merchant": "Foodpanda", "amount": -450}]
    path = tmp_path / "w.json"
    path.write_text(json.dumps({"transactions": records} if wrap else records), encoding="utf-8")
    assert import_wallet([path]).frame["amount"].iloc[0] == -450


def test_unsupported_and_unrecognizable_files_raise_clearly(tmp_path):
    bad = tmp_path / "w.pdf"
    bad.write_text("x")
    with pytest.raises(ValueError, match="Unsupported"):
        import_wallet([bad])
    no_header = tmp_path / "w.csv"
    no_header.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="header"):
        import_wallet([no_header])


def test_original_file_is_never_modified(make_csv):
    path = make_csv([("2026-07-08", "", "Foodpanda", -450)])
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    import_wallet([path])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_all_positive_amounts_warn(make_csv):
    assert any("positive" in w for w in import_wallet([make_csv([("2026-07-08", "", "Foodpanda", 450)])]).warnings)


def test_coverage_gap_warns(make_csv):
    result = import_wallet([make_csv([("2026-01-05", "", "Bus", -10), ("2026-04-05", "", "Bus", -10)])])
    assert any("gap" in w for w in result.warnings)


@pytest.mark.parametrize("text,amount,expected", [
    ("Transfer to Savings", -500, "transfer"), ("Transfer from Savings", 500, "transfer"),
    ("Wallet top-up", 500, "transfer"), ("Refund - Daraz", 400, "refund"), ("Payment reversal", 300, "refund"),
    ("Refund clawback", -300, "adjustment"), ("Balance adjustment", 50, "adjustment"),
    ("Pocket money", 500, "income"), ("Foodpanda", -300, "expense"), ("Mobile top-up", -300, "expense"),
])
def test_type_classification(text, amount, expected):
    assert classify_type(text, amount) == expected


def test_redaction():
    assert redact("Card 4111 1111 1111 1234 paid") == "Card ****1234 paid"
    assert redact("PK36SCBL0000001123456702") == "****6702"
    assert redact("me@example.com") == "[email]"
    assert redact("FOODPANDA*ORDER 88213") == "FOODPANDA*ORDER 88213"
