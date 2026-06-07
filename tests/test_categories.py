from accounting_anomaly.core.categories import (
    apply_categories,
    is_saved_category,
    suggest_category,
)


def test_is_saved_category_rejects_purpose_autofill():
    assert not is_saved_category("AMAZON MARKETPLACE", "AMAZON MARKETPLACE")
    assert is_saved_category("AMAZON MARKETPLACE", "Shopping")


def test_suggest_category_uses_learned_mapping():
    tx = {"payee": "Coffee Shop", "description": "Morning coffee"}
    assert suggest_category(tx, {"Coffee Shop": "Food"}) == "Food"


def test_suggest_category_defaults_to_purpose():
    tx = {"payee": "", "description": "AMAZON MARKETPLACE"}
    assert suggest_category(tx, {}) == "AMAZON MARKETPLACE"


def test_apply_categories_only_learned():
    txs = [
        {"payee": "Coffee Shop", "description": "Latte", "amount": -3.5, "status": "pending"},
        {"payee": "", "description": "New Payee", "amount": -10.0, "status": "pending"},
    ]
    payee_categories = {"Coffee Shop": "Food"}
    result = apply_categories(txs, payee_categories)
    assert result[0]["category"] == "Food"
    assert result[1]["category"] == ""


def test_apply_categories_preserves_other_fields():
    txs = [
        {
            "payee": "",
            "description": "Rent",
            "amount": -900.0,
            "status": "approved",
            "month": "2024-01",
        }
    ]
    result = apply_categories(txs, {"Rent": "Housing"})
    assert result[0]["status"] == "approved"
    assert result[0]["month"] == "2024-01"
    assert result[0]["category"] == "Housing"
