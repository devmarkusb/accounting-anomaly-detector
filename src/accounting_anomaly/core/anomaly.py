import math

from .payee import payee_identity

ANOMALY_SIGMA = 2.5
MIN_HISTORY = 1  # one approved sample per payee enables auto-classify on re-import


def _std(stats: dict) -> float:
    if stats["count"] < 2:
        return float("inf")
    variance = stats["m2"] / (stats["count"] - 1)
    return math.sqrt(max(0.0, variance))


def classify(transactions: list[dict], payee_stats: dict) -> list[dict]:
    """
    Auto-classify transactions based on payee history.

    - ignored transactions pass through unchanged
    - new payees or payees with <MIN_HISTORY samples → pending
    - known payees within ANOMALY_SIGMA std of their mean → approved
    - known payees outside that range → anomaly
    """
    result = []
    for tx in transactions:
        if tx.get("status") == "ignored":
            result.append(tx)
            continue

        desc = payee_identity(tx)
        amount = tx["amount"]
        stats = payee_stats.get(desc)

        if stats is None or stats["count"] < MIN_HISTORY:
            status = "pending"
        elif stats["count"] == 1:
            deviation = abs(amount - stats["mean"])
            status = "approved" if deviation < 1e-6 else "anomaly"
        else:
            std = _std(stats)
            deviation = abs(amount - stats["mean"])
            if std == 0:
                status = "approved" if deviation < 1e-6 else "anomaly"
            elif deviation <= ANOMALY_SIGMA * std:
                status = "approved"
            else:
                status = "anomaly"

        result.append({**tx, "status": status})
    return result
