from .payee import payee_identity


def suggest_category(tx: dict, payee_categories: dict[str, str]) -> str:
    """Learned category for this payee, or purpose/description on first encounter."""
    learned = payee_categories.get(payee_identity(tx), "")
    return learned or tx["description"]


def apply_categories(transactions: list[dict], payee_categories: dict[str, str]) -> list[dict]:
    """Pre-fill category from learned mappings, else purpose/description text."""
    result = []
    for tx in transactions:
        category = suggest_category(tx, payee_categories)
        result.append({**tx, "category": category})
    return result
