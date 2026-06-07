from accounting_anomaly.core.anomaly import classify


def _stats(count: int, mean: float, m2: float) -> dict:
    return {"count": count, "mean": mean, "m2": m2}


def test_unknown_payee_is_pending():
    txs = [{"description": "NewShop", "amount": -50.0, "status": "pending"}]
    result = classify(txs, {})
    assert result[0]["status"] == "pending"


def test_one_sample_exact_amount_auto_approved():
    stats = {"Coffee": _stats(1, -3.5, 0.0)}
    txs = [{"description": "Coffee", "amount": -3.5, "status": "pending"}]
    result = classify(txs, stats)
    assert result[0]["status"] == "approved"


def test_one_sample_different_amount_anomaly():
    stats = {"Coffee": _stats(1, -3.5, 0.0)}
    txs = [{"description": "Coffee", "amount": -10.0, "status": "pending"}]
    result = classify(txs, stats)
    assert result[0]["status"] == "anomaly"


def test_payee_identity_used_for_stats_lookup():
    stats = {"ACME GmbH": _stats(1, -42.0, 0.0)}
    txs = [
        {
            "payee": "ACME GmbH",
            "description": "Invoice Jan",
            "amount": -42.0,
            "status": "pending",
        }
    ]
    result = classify(txs, stats)
    assert result[0]["status"] == "approved"


def test_known_payee_normal_amount_approved():
    # std ≈ 0.33, threshold 2.5σ ≈ 0.83 — amount matches mean exactly
    stats = {"Coffee": _stats(10, -3.5, 1.0)}
    txs = [{"description": "Coffee", "amount": -3.5, "status": "pending"}]
    result = classify(txs, stats)
    assert result[0]["status"] == "approved"


def test_known_payee_unusual_amount_anomaly():
    # std ≈ 0.33, deviation of 96.5 >> threshold
    stats = {"Coffee": _stats(10, -3.5, 1.0)}
    txs = [{"description": "Coffee", "amount": -100.0, "status": "pending"}]
    result = classify(txs, stats)
    assert result[0]["status"] == "anomaly"


def test_ignored_status_passes_through():
    txs = [{"description": "OwnAccount", "amount": -500.0, "status": "ignored"}]
    result = classify(txs, {})
    assert result[0]["status"] == "ignored"


def test_zero_variance_payee_approved():
    # Payee always charges exactly the same amount → std=0 → approved
    stats = {"Subscription": _stats(10, -9.99, 0.0)}
    txs = [{"description": "Subscription", "amount": -9.99, "status": "pending"}]
    result = classify(txs, stats)
    assert result[0]["status"] == "approved"


def test_zero_variance_different_amount_anomaly():
    stats = {"Subscription": _stats(10, -9.99, 0.0)}
    txs = [{"description": "Subscription", "amount": -19.99, "status": "pending"}]
    result = classify(txs, stats)
    assert result[0]["status"] == "anomaly"
