import math

from .payee import payee_identity

ANOMALY_SIGMA = 2.5
MIN_HISTORY = 3  # need at least this many samples before auto-approving


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
        else:
            std = _std(stats)
            deviation = abs(amount - stats["mean"])
            if std == 0:
                status = "approved" if deviation == 0 else "anomaly"
            elif deviation <= ANOMALY_SIGMA * std:
                status = "approved"
            else:
                status = "anomaly"

        result.append({**tx, "status": status})
    return result
