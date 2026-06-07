from .payee import payee_identity


def is_saved_category(purpose: str, category: str) -> bool:
    """True when category is a user label, not just the auto-filled purpose text."""
    category = category.strip()
    if not category:
        return False
    return category != purpose.strip()


def suggest_category(tx: dict, payee_categories: dict[str, str]) -> str:
    """UI autofill: learned category, else purpose/description (not stored unless saved)."""
    learned = payee_categories.get(payee_identity(tx), "")
    return learned or tx["description"]


def apply_categories(transactions: list[dict], payee_categories: dict[str, str]) -> list[dict]:
    """Persist only learned categories on import; purpose autofill happens in review UI."""
    result = []
    for tx in transactions:
        category = payee_categories.get(payee_identity(tx), "")
        result.append({**tx, "category": category})
    return result
