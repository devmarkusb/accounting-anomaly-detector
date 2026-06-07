from accounting_anomaly.core.categories import apply_categories


def test_apply_categories_prefills_known_payee():
    txs = [
        {"description": "Coffee Shop", "amount": -3.5, "status": "pending"},
        {"description": "New Payee", "amount": -10.0, "status": "pending"},
    ]
    payee_categories = {"Coffee Shop": "Food"}
    result = apply_categories(txs, payee_categories)
    assert result[0]["category"] == "Food"
    assert result[1]["category"] == ""


def test_apply_categories_preserves_other_fields():
    txs = [{"description": "Rent", "amount": -900.0, "status": "approved", "month": "2024-01"}]
    result = apply_categories(txs, {"Rent": "Housing"})
    assert result[0]["status"] == "approved"
    assert result[0]["month"] == "2024-01"
    assert result[0]["category"] == "Housing"
