from src.importer import import_wallet
from src.main import analyze
from src.normalizer import merge_similar_merchants, normalize_merchant
import pandas as pd


def _category(results, name):
    return next(c for c in results["spending"]["categories"] if c["category"] == name)


def test_expense_total_equals_raw_negative_non_transfer_rows(sample_results):
    df = sample_results["transactions"]
    raw = -df[(df["amount"] < 0) & (df["transaction_type"] != "transfer")]["amount"].sum()
    assert sample_results["spending"]["gross_total"] == raw


def test_food_delivery_total(sample_results):
    assert _category(sample_results, "Food delivery")["net"] == 4050


def test_food_delivery_beats_all_subscriptions_and_is_the_leak(sample_results):
    assert _category(sample_results, "Food delivery")["net"] > _category(sample_results, "Subscriptions")["net"]
    assert sample_results["leak"]["category"] == "Food delivery"


def test_categories_ranked_high_to_low_and_percentages_sum(sample_results):
    categories = sample_results["spending"]["categories"]
    nets = [c["net"] for c in categories]
    assert nets == sorted(nets, reverse=True)
    assert abs(sum(c["percent"] for c in categories) - 100) < 0.5


def test_refund_reduces_category_and_is_not_income(sample_results):
    shopping = _category(sample_results, "Shopping")
    assert shopping["refunds"] == 400
    assert shopping["net"] == shopping["gross"] - 400


def test_transfers_are_not_spending(sample_results):
    df = sample_results["transactions"]
    assert set(df[df["description"].str.contains("Savings")]["transaction_type"]) == {"transfer"}
    assert sample_results["overview"]["transfers_out"] == 1500
    assert sample_results["overview"]["transfers_in"] == 500


def test_essentials_are_never_the_leak(make_csv):
    path = make_csv([("2026-01-05", "", "Green Pharmacy", -9000), ("2026-01-06", "", "Cinema Tickets", -100),
                     ("2026-01-07", "", "Pocket money", 9500)])
    results = analyze(import_wallet([path]))
    assert results["spending"]["largest_category"] == "Healthcare"
    assert results["leak"]["category"] == "Entertainment"


def test_no_reducible_spending_reports_no_leak(make_csv):
    path = make_csv([("2026-01-05", "", "Green Pharmacy", -900), ("2026-01-07", "", "Pocket money", 9500)])
    assert analyze(import_wallet([path]))["leak"]["found"] is False


def test_leak_warns_when_much_spending_is_unclassified(make_csv):
    path = make_csv([("2026-01-05", "", "Zed Unknown", -900), ("2026-01-06", "", "Cinema Tickets", -100), ("2026-01-07", "", "Pocket money", 9500)])
    leak = analyze(import_wallet([path]))["leak"]
    assert "could not be categorized" in leak["caveat"]
    assert leak["unclassified_merchants"] == ["Zed Unknown"]


def test_sample_needs_no_unclassified_caveat(sample_results):
    assert sample_results["leak"]["caveat"] is None


def test_merchant_normalization():
    for variant in ("FOODPANDA*ORDER 88213", "Food Panda", "foodpanda"):
        assert normalize_merchant(variant) == "Foodpanda"
    for variant in ("PRIMEVIDEO*MEMBERSHIP", "Prime Video", "AMZN PRIME VIDEO"):
        assert normalize_merchant(variant) == "PrimeVideo"
    assert normalize_merchant("Uber Eats") != normalize_merchant("Uber Ride")
    merged = merge_similar_merchants(pd.Series(["Daily Mart", "Daily Mart", "Dailymart"]))
    assert set(merged) == {"Daily Mart"}
