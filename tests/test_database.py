import pytest

from accounting_anomaly.db import database as db


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    yield


def _tx(**overrides) -> dict:
    base = {
        "date": "2024-01-15",
        "payee": "Coffee Shop",
        "description": "Morning coffee",
        "amount": -3.5,
        "balance": None,
        "month": "2024-01",
        "account": "Checking",
        "status": "pending",
        "category": "",
    }
    base.update(overrides)
    return base


def test_insert_and_review_queue_order(isolated_db):
    db.insert_transactions(
        [
            _tx(date="2024-02-01", month="2024-02", description="Feb Payee"),
            _tx(date="2024-01-10", month="2024-01", description="Jan Payee A"),
            _tx(date="2024-01-20", month="2024-01", description="Jan Payee B", status="anomaly"),
        ]
    )
    queue = db.get_review_queue()
    assert [r["description"] for r in queue] == [
        "Jan Payee A",
        "Jan Payee B",
        "Feb Payee",
    ]


def test_update_review_learns_category_by_payee(isolated_db):
    db.insert_transactions([_tx()])
    tx_id = db.get_transactions()[0]["id"]
    db.update_review(tx_id, "approved", "Food")
    row = db.get_transactions()[0]
    assert row["status"] == "approved"
    assert row["category"] == "Food"
    assert row["payee"] == "Coffee Shop"
    assert db.get_payee_categories()["Coffee Shop"] == "Food"
    assert db.get_payee_stats()["Coffee Shop"]["count"] == 1
    assert db.get_known_categories() == ["Food"]


def test_update_review_does_not_learn_purpose_as_category(isolated_db):
    db.insert_transactions([_tx()])
    tx_id = db.get_transactions()[0]["id"]
    db.update_review(tx_id, "approved", "Morning coffee")
    assert db.get_payee_categories() == {}
    assert db.get_known_categories() == []


def test_repeat_payee_auto_approved_on_reimport(isolated_db):
    from accounting_anomaly.core.anomaly import classify
    from accounting_anomaly.core.categories import apply_categories

    db.insert_transactions([_tx(status="approved")])
    stats = db.get_payee_stats()
    feb = apply_categories(
        classify(
            [_tx(date="2024-02-01", month="2024-02", description="February coffee")],
            stats,
        ),
        db.get_payee_categories(),
    )
    assert feb[0]["status"] == "approved"
    inserted, _ = db.insert_transactions(feb)
    assert inserted == 1
    assert db.get_review_queue() == []


def test_insert_applies_category_on_known_payee(isolated_db):
    db.insert_transactions([_tx(status="approved", category="Food")])
    inserted, _ = db.insert_transactions(
        [_tx(date="2024-02-01", month="2024-02", status="pending", category="Food")]
    )
    assert inserted == 1
    feb = db.get_transactions(month="2024-02")[0]
    assert feb["category"] == "Food"


def test_conn_recreates_schema_after_db_file_removed(isolated_db, tmp_path, monkeypatch):
    db.insert_transactions([_tx()])
    db_path = tmp_path / "test.db"
    assert db_path.exists()
    db_path.unlink()
    inserted, _ = db.insert_transactions([_tx(date="2024-02-01", month="2024-02")])
    assert inserted == 1
    assert len(db.get_transactions()) == 1


def test_clear_data_removes_transactions_and_learning(isolated_db):
    db.insert_transactions([_tx(status="approved", category="Food")])
    db.clear_data()
    assert db.get_transactions() == []
    assert db.get_payee_stats() == {}
    assert db.get_payee_categories() == {}
