def apply_categories(transactions: list[dict], payee_categories: dict[str, str]) -> list[dict]:
    """Pre-fill category from learned per-payee mappings (exact description match)."""
    result = []
    for tx in transactions:
        category = payee_categories.get(tx["description"], "")
        result.append({**tx, "category": category})
    return result
