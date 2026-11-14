import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from rongwei_plugin.local_store import LocalStore


def test_customer_memory_and_interaction_are_persistent(tmp_path):
    path = tmp_path / "customer.sqlite3"
    store = LocalStore(path)
    customer_id = store.create_customer(name="Buyer A", country="Germany", facts={"model": "SUV"})
    interaction_id = store.append_interaction(customer_id, "Interested in two vehicles", source="chat")
    reopened = LocalStore(path)
    customer = reopened.get_customer(customer_id)
    assert customer["facts"] == {"model": "SUV"}
    assert reopened.list_interactions(customer_id)[0]["id"] == interaction_id


def test_port_recommendations_preserve_evidence_status(tmp_path):
    store = LocalStore(tmp_path / "customer.sqlite3")
    store.add_port("Germany", "Hamburg", status="historical_reference", source_note="Past customer")
    store.add_port("Germany", "Confirmed Port", status="confirmed")
    result = store.recommend_ports("Germany")
    assert [item["name"] for item in result] == ["Confirmed Port", "Hamburg"]
    assert result[1]["status"] == "historical_reference"


def test_followup_is_due_and_can_be_completed(tmp_path):
    store = LocalStore(tmp_path / "customer.sqlite3")
    customer_id = store.create_customer(name="Buyer B")
    due = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    followup_id = store.add_followup(customer_id, due, "Send requested vehicle details")
    assert store.list_due_followups()
    store.complete_followup(followup_id, "Details sent manually")
    assert store.list_due_followups() == []


def test_backup_restore_rejects_corrupt_backup_without_destroying_data(tmp_path):
    store = LocalStore(tmp_path / "customer.sqlite3")
    customer_id = store.create_customer(name="Original")
    backup = store.backup(tmp_path / "backup.sqlite3")
    store.create_customer(name="Later")
    store.restore(backup)
    assert store.get_customer(customer_id)["name"] == "Original"
    corrupt = tmp_path / "bad.sqlite3"
    corrupt.write_text("not a sqlite database")
    with pytest.raises(sqlite3.DatabaseError):
        store.restore(corrupt)
    assert store.get_customer(customer_id)["name"] == "Original"
