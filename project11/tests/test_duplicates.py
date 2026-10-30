from src.duplicate_detector import LABEL, detect_duplicates
from src.importer import import_wallet


def test_foodpanda_pair_on_8_july_is_flagged(sample_results):
    pair = [d for d in sample_results["duplicates"] if d["merchant"] == "Foodpanda"]
    assert len(pair) == 1
    assert (pair[0]["date"].month, pair[0]["date"].day) == (7, 8)
    assert pair[0]["amount"] == 450 and pair[0]["count"] == 2
    assert pair[0]["evidence_strength"] == "Stronger"


def test_every_flag_uses_the_manual_verification_label_and_never_says_fraud(sample_results):
    for item in sample_results["duplicates"]:
        assert item["label"] == LABEL
        assert "fraud" not in item["explanation"].lower()


def test_legitimate_same_day_purchases_are_flagged_only_weakly(sample_results):
    by_merchant = {d["merchant"]: d for d in sample_results["duplicates"]}
    assert by_merchant["Metro Bus Fare"]["evidence_strength"] == "Weaker"
    assert by_merchant["Campus Cafe"]["evidence_strength"] == "Weaker"


def test_flagged_charges_are_not_removed(sample_results):
    df = sample_results["transactions"]
    assert len(df[(df["merchant"] == "Foodpanda") & (df["amount"] == -450)]) == 2


def test_same_day_different_amount_is_not_flagged(frame_of):
    assert detect_duplicates(frame_of([("2026-01-05", "", "Foodpanda", -450), ("2026-01-05", "", "Foodpanda", -300)])) == []


def test_different_day_or_merchant_is_not_flagged(frame_of):
    assert detect_duplicates(frame_of([("2026-01-05", "", "Foodpanda", -450), ("2026-01-06", "", "Foodpanda", -450),
                                       ("2026-01-06", "", "Uber Eats", -450)])) == []


def test_spelling_variants_still_match(frame_of):
    found = detect_duplicates(frame_of([("2026-01-05", "", "FOODPANDA*ORDER 1", -450), ("2026-01-05", "", "Food Panda", -450)]))
    assert len(found) == 1


def test_matching_refund_weakens_the_evidence(frame_of):
    found = detect_duplicates(frame_of([("2026-01-05", "13:00", "Foodpanda", -450), ("2026-01-05", "13:01", "Foodpanda", -450),
                                        ("2026-01-09", "", "Refund Foodpanda", 450)]))
    assert found[0]["evidence_strength"] == "Weaker"
    assert "refund" in found[0]["explanation"].lower()


def test_repeated_reference_on_differing_rows_is_flagged(make_csv):
    path = make_csv([("2026-01-05", "Cinema Tickets", -300, "R1"), ("2026-01-06", "Cinema Tickets", -300, "R1")],
                    header=("Date", "Description", "Amount", "Reference"))
    from src.normalizer import normalize
    found = detect_duplicates(normalize(import_wallet([path]).frame))
    assert len(found) == 1 and "reference" in found[0]["explanation"]
