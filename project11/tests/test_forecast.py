from datetime import date

from src.importer import import_wallet
from src.main import analyze


def _sample(path_kwargs=None, **kwargs):
    from .conftest import SAMPLE
    return analyze(import_wallet([SAMPLE]), **kwargs)["forecast"]


def test_conservative_never_spends_less_than_expected_when_spending_is_lumpy(make_csv):
    rows = [("2026-03-05", "", "Allowance", 8000), ("2026-04-05", "", "Allowance", 8000), ("2026-05-05", "", "Allowance", 8000),
            ("2026-03-09", "", "Burger Hut", -5000), ("2026-05-20", "", "Tea Stall", -10)]
    scenarios = {s["name"]: s for s in analyze(import_wallet([make_csv(rows)]))["forecast"]["scenarios"]}
    assert scenarios["Conservative estimate"]["spending"] >= scenarios["Expected estimate"]["spending"]
    assert scenarios["Higher-spending estimate"]["spending"] >= scenarios["Conservative estimate"]["spending"]


def test_next_date_inferred_from_regular_pocket_money(sample_results):
    fc = sample_results["forecast"]
    assert fc["next_income_date"] == date(2026, 11, 15)
    assert fc["date_source"].startswith("inferred")


def test_missing_balance_is_explained_not_invented():
    fc = _sample()
    assert fc["balance"] is None
    assert "not a verified account balance" in fc["balance_basis"]
    assert all(s["remaining"] is None for s in fc["scenarios"])


def test_opening_balance_includes_all_rows_including_transfers(sample_results):
    df = sample_results["transactions"]
    assert sample_results["forecast"]["balance"] == 6000 + df["amount"].sum()


def test_current_balance_takes_priority():
    fc = _sample(opening_balance=6000, current_balance=1000)
    assert fc["balance"] == 1000


def test_scenarios_are_ordered_and_arithmetic_adds_up(sample_results):
    fc = sample_results["forecast"]
    by_name = {s["name"]: s for s in fc["scenarios"]}
    assert by_name["Expected estimate"]["spending"] <= by_name["Conservative estimate"]["spending"] <= by_name["Higher-spending estimate"]["spending"]
    for s in fc["scenarios"]:
        assert abs(fc["balance"] + s["income"] - s["spending"] - s["remaining"]) < 0.01


def test_scheduled_charges_are_inside_the_window_and_skip_stopped_ones(sample_results):
    fc = sample_results["forecast"]
    merchants = {e["merchant"]: e for e in fc["scheduled_certain"]}
    assert merchants["PrimeVideo"]["dates"] == [date(2026, 11, 12)]
    assert merchants["Jazz Monthly Bundle"]["dates"] == [date(2026, 11, 1)]
    assert len(merchants["Metro Bus Weekly Pass"]["dates"]) == 2
    assert "Canva" not in merchants


def test_assumptions_state_tutoring_is_left_out_by_default(sample_results):
    fc = sample_results["forecast"]
    assert any("Tutoring" in a and "not counted" in a for a in fc["assumptions"])
    assert fc["upside_income"][0]["source"] == "Tutoring"
    assert all(s["income"] == 0 for s in fc["scenarios"])


def test_irregular_income_opt_in_is_stated():
    fc = _sample(include_irregular_income=True)
    assert any("continues at the observed frequency" in a for a in fc["assumptions"])
    assert fc["scenarios"][1]["income"] > 0


def test_no_regular_income_asks_for_the_date(make_csv):
    results = analyze(import_wallet([make_csv([("2026-01-05", "", "Cinema", -300), ("2026-01-09", "", "Gift from aunt", 500)])]))
    assert results["forecast"]["status"] == "needs_date"
    assert "--next-pocket-money" in results["forecast"]["message"]


def test_supplied_date_is_used_when_nothing_can_be_inferred(make_csv):
    results = analyze(import_wallet([make_csv([("2026-01-05", "", "Cinema", -300)])]), next_income_date=date(2026, 1, 20))
    assert results["forecast"]["status"] == "ok" and results["forecast"]["days"] == 14


def test_past_date_is_rejected(make_csv):
    results = analyze(import_wallet([make_csv([("2026-01-05", "", "Cinema", -300)])]), next_income_date=date(2026, 1, 1))
    assert results["forecast"]["status"] == "needs_date"
