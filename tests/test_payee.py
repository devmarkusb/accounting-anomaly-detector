from accounting_anomaly.core.payee import payee_identity


def test_payee_identity_uses_payee_when_set():
    assert payee_identity({"payee": "ACME GmbH", "description": "Invoice 42"}) == "ACME GmbH"


def test_payee_identity_falls_back_to_description():
    assert payee_identity({"payee": "", "description": "Coffee Shop"}) == "Coffee Shop"
