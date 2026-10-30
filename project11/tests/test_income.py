from src.importer import import_wallet
from src.income_analyzer import analyze_income
from src.main import analyze


def test_total_income_is_computed_from_rows(sample_results):
    assert sample_results["income"]["total"] == 23000


def test_income_by_source(sample_results):
    sources = {s["source"]: s for s in sample_results["income"]["sources"]}
    assert sources["Pocket money"]["total"] == 20000
    assert sources["Pocket money"]["count"] == 4
    assert sources["Tutoring"]["total"] == 3000
    assert sources["Tutoring"]["count"] == 2


def test_regular_and_irregular_income_are_distinguished(sample_results):
    sources = {s["source"]: s for s in sample_results["income"]["sources"]}
    assert sources["Pocket money"]["regular"] and sources["Pocket money"]["cadence"] == "monthly"
    assert not sources["Tutoring"]["regular"]
    assert sample_results["income"]["irregular"] == ["Tutoring"]


def test_income_changes_with_the_data(frame_of):
    df = frame_of([("2026-01-05", "", "Pocket money", 700), ("2026-02-05", "", "Pocket money", 700),
                   ("2026-02-07", "", "Cinema", -50)])
    assert analyze_income(df)["total"] == 1400


def test_transfers_and_refunds_are_not_income(sample_results):
    # The wallet holds a +500 savings transfer and a +400 refund on top of the 23,000.
    positive = sample_results["transactions"].query("amount > 0")["amount"].sum()
    assert positive == 23900
    assert sample_results["income"]["total"] == 23000


def test_transfer_to_a_person_is_flagged_for_review(make_csv):
    path = make_csv([("2026-01-05", "", "Transfer to Ali", -300), ("2026-01-06", "", "Pocket money", 900)])
    results = analyze(import_wallet([path]))
    assert results["spending"]["gross_total"] == 300
    assert results["review_transfers"] == ["Transfer Ali"]
