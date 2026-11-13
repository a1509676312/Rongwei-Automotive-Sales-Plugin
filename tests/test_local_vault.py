import sqlite3
import pytest

from rongwei_plugin.storage.local_vault import LocalVault, VaultError


def test_local_vault_encrypts_and_round_trips(tmp_path):
    pytest.importorskip("cryptography")
    path = tmp_path / "private" / "customers.sqlite3"
    record = {"name": "Demo Buyer", "phone": "+254700000000",
              "messages": [{"speaker": "buyer", "text": "Need two SUVs"}]}
    with LocalVault(path, "correct horse battery staple", "company-demo") as vault:
        vault.save_record("customer-1", "customer", record, "2026-01-01T00:00:00Z",
                          "2026-01-01T00:00:00Z")
        assert vault.get_record("customer-1") == record
    raw = path.read_bytes()
    assert b"Demo Buyer" not in raw
    assert b"+254700000000" not in raw
    assert b"Need two SUVs" not in raw


def test_wrong_passphrase_is_rejected(tmp_path):
    pytest.importorskip("cryptography")
    path = tmp_path / "customers.sqlite3"
    with LocalVault(path, "correct horse battery staple", "company-demo"):
        pass
    with pytest.raises(VaultError, match="Incorrect passphrase"):
        LocalVault(path, "incorrect passphrase", "company-demo")


def test_workspace_mismatch_is_rejected(tmp_path):
    pytest.importorskip("cryptography")
    path = tmp_path / "customers.sqlite3"
    with LocalVault(path, "correct horse battery staple", "company-one"):
        pass
    with pytest.raises(VaultError, match="different workspace"):
        LocalVault(path, "correct horse battery staple", "company-two")


def test_delete_only_removes_workspace_record(tmp_path):
    pytest.importorskip("cryptography")
    path = tmp_path / "customers.sqlite3"
    with LocalVault(path, "correct horse battery staple", "company-demo") as vault:
        vault.save_record("customer-1", "customer", {"name": "A"},
                          "2026-01-01", "2026-01-01")
        assert vault.delete_record("customer-1") is True
        assert vault.get_record("customer-1") is None
        assert vault.delete_record("customer-1") is False
