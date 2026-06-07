def payee_identity(tx: dict) -> str:
    """Counterparty key for stats/categories: payee column if set, else description."""
    payee = (tx.get("payee") or "").strip()
    return payee or tx["description"]
