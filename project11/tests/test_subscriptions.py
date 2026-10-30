from src.subscription_detector import CONFIRMED, POSSIBLE, PROBABLE, detect_recurring


def _find(results, merchant):
    return next((r for r in results if r["merchant"] == merchant), None)


def test_primevideo_is_confirmed_monthly_with_total_796(sample_results):
    prime = _find(sample_results["recurring"], "PrimeVideo")
    assert prime["tier"] == CONFIRMED
    assert prime["cadence"] == "monthly"
    assert prime["amount"] == 199
    assert prime["occurrences"] == 4
    assert prime["total"] == 796


def test_weekly_pattern_found(sample_results):
    bus = _find(sample_results["recurring"], "Metro Bus Weekly Pass")
    assert bus["cadence"] == "weekly" and bus["tier"] == CONFIRMED


def test_two_charges_then_silence_is_probable_and_inactive(sample_results):
    canva = _find(sample_results["recurring"], "Canva")
    assert canva["tier"] == PROBABLE
    assert canva["active"] is False


def test_partly_regular_needs_manual_review(sample_results):
    assert _find(sample_results["recurring"], "Laundry Service")["tier"] == POSSIBLE


def test_variable_amount_food_orders_are_not_subscriptions(sample_results):
    assert _find(sample_results["recurring"], "Foodpanda") is None
    assert _find(sample_results["recurring"], "Daily Mart") is None


def test_same_amount_twice_is_not_recurring(frame_of):
    df = frame_of([("2026-01-05", "", "Cinema Tickets", -350), ("2026-01-16", "", "Cinema Tickets", -350)])
    assert detect_recurring(df) == []


def test_same_amount_at_different_merchants_is_not_recurring(frame_of):
    df = frame_of([("2026-01-05", "", "Shop Alpha", -199), ("2026-02-05", "", "Shop Bravo", -199),
                   ("2026-03-05", "", "Shop Charlie", -199)])
    assert detect_recurring(df) == []


def test_price_change_is_probable_not_confirmed(frame_of):
    df = frame_of([("2026-01-05", "", "Netflix", -100), ("2026-02-05", "", "Netflix", -100),
                   ("2026-03-05", "", "Netflix", -130), ("2026-04-05", "", "Netflix", -130)])
    assert detect_recurring(df)[0]["tier"] == PROBABLE


def test_annual_charge_needs_a_year_of_history(frame_of):
    df = frame_of([("2025-02-10", "", "Adobe Plan", -5000), ("2026-02-10", "", "Adobe Plan", -5000)])
    found = detect_recurring(df)
    assert found[0]["cadence"] == "annual" and found[0]["tier"] == PROBABLE
    assert detect_recurring(frame_of([("2026-02-10", "", "Adobe Plan", -5000)])) == []


def test_steady_plan_found_among_one_off_purchases(frame_of):
    df = frame_of([("2026-01-05", "", "Amazon Plan", -99), ("2026-01-20", "", "Amazon Plan", -4500),
                   ("2026-02-05", "", "Amazon Plan", -99), ("2026-03-05", "", "Amazon Plan", -99)])
    found = detect_recurring(df)
    assert found[0]["amount"] == 99 and found[0]["total"] == 297
