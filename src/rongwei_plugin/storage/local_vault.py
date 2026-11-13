"""Passphrase-encrypted, local-only customer record vault.

The database contains ciphertext only. The passphrase is never stored. A
separate random salt is stored in the database. This is a local storage
primitive, not a complete desktop security boundary: OS account security,
device encryption, backups, and process access still matter.
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
from pathlib import Path
from typing import Any

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
except ImportError:  # pragma: no cover - exercised when optional extra absent
    AESGCM = None
    Scrypt = None


class VaultError(Exception):
    """Raised for vault configuration, authentication, or data errors."""


class LocalVault:
    """Encrypted local SQLite vault for one workspace.

    Every customer record is encrypted as a whole JSON document. This avoids
    leaking names, phone numbers, messages, and notes through SQLite columns.
    The workspace identifier is authenticated as AES-GCM associated data.
    """

    def __init__(self, database_path: str | Path, passphrase: str, workspace_id: str):
        if AESGCM is None or Scrypt is None:
            raise VaultError("Install the 'secure-storage' extra: pip install '.[secure-storage]'")
        if not isinstance(passphrase, str) or len(passphrase) < 12:
            raise VaultError("Vault passphrase must contain at least 12 characters")
        if not isinstance(workspace_id, str) or not workspace_id.strip():
            raise VaultError("workspace_id is required")
        self.path = Path(database_path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace_id = workspace_id.strip()
        self._aad = ("rongwei:v1:" + self.workspace_id).encode("utf-8")
        self._connection = sqlite3.connect(str(self.path))
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._initialize(passphrase)

    def _initialize(self, passphrase: str) -> None:
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS vault_meta (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL
            )
        """)
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS customer_records (
                record_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                record_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                nonce BLOB NOT NULL,
                ciphertext BLOB NOT NULL
            )
        """)
        row = self._connection.execute(
            "SELECT value FROM vault_meta WHERE key='salt'"
        ).fetchone()
        if row is None:
            salt = secrets.token_bytes(16)
            key = self._derive_key(passphrase, salt)
            check_nonce = secrets.token_bytes(12)
            check = AESGCM(key).encrypt(check_nonce, b"rongwei-vault-ok", self._aad)
            self._connection.executemany(
                "INSERT INTO vault_meta(key,value) VALUES(?,?)",
                [("salt", salt), ("check_nonce", check_nonce), ("check", check),
                 ("workspace_id", self.workspace_id.encode("utf-8"))],
            )
            self._connection.commit()
            self._key = key
        else:
            stored_workspace = self._connection.execute(
                "SELECT value FROM vault_meta WHERE key='workspace_id'"
            ).fetchone()
            if not stored_workspace or stored_workspace[0].decode("utf-8") != self.workspace_id:
                raise VaultError("This database belongs to a different workspace")
            salt = row[0]
            key = self._derive_key(passphrase, salt)
            nonce = self._connection.execute(
                "SELECT value FROM vault_meta WHERE key='check_nonce'"
            ).fetchone()[0]
            check = self._connection.execute(
                "SELECT value FROM vault_meta WHERE key='check'"
            ).fetchone()[0]
            try:
                plain = AESGCM(key).decrypt(nonce, check, self._aad)
            except Exception as exc:
                raise VaultError("Incorrect passphrase or damaged vault") from exc
            if plain != b"rongwei-vault-ok":
                raise VaultError("Incorrect passphrase or damaged vault")
            self._key = key

    @staticmethod
    def _derive_key(passphrase: str, salt: bytes) -> bytes:
        return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(passphrase.encode("utf-8"))

    def save_record(self, record_id: str, record_type: str, data: dict[str, Any],
                    created_at: str, updated_at: str) -> None:
        if not record_id.strip() or not record_type.strip():
            raise VaultError("record_id and record_type are required")
        if not isinstance(data, dict):
            raise VaultError("data must be a JSON object")
        nonce = secrets.token_bytes(12)
        plaintext = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext, self._aad)
        self._connection.execute("""
            INSERT INTO customer_records
              (record_id,workspace_id,record_type,created_at,updated_at,nonce,ciphertext)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(record_id) DO UPDATE SET
              record_type=excluded.record_type,
              updated_at=excluded.updated_at,
              nonce=excluded.nonce,
              ciphertext=excluded.ciphertext
            WHERE customer_records.workspace_id=excluded.workspace_id
        """, (record_id, self.workspace_id, record_type, created_at, updated_at, nonce, ciphertext))
        self._connection.commit()

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        row = self._connection.execute("""
            SELECT nonce,ciphertext FROM customer_records
            WHERE record_id=? AND workspace_id=?
        """, (record_id, self.workspace_id)).fetchone()
        if row is None:
            return None
        try:
            raw = AESGCM(self._key).decrypt(row[0], row[1], self._aad)
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise VaultError("Record authentication failed; data may be damaged") from exc

    def list_records(self, record_type: str | None = None) -> list[dict[str, Any]]:
        if record_type:
            rows = self._connection.execute("""
                SELECT record_id,record_type,created_at,updated_at,nonce,ciphertext
                FROM customer_records WHERE workspace_id=? AND record_type=?
                ORDER BY updated_at DESC
            """, (self.workspace_id, record_type)).fetchall()
        else:
            rows = self._connection.execute("""
                SELECT record_id,record_type,created_at,updated_at,nonce,ciphertext
                FROM customer_records WHERE workspace_id=? ORDER BY updated_at DESC
            """, (self.workspace_id,)).fetchall()
        result = []
        for record_id, kind, created, updated, nonce, ciphertext in rows:
            try:
                raw = AESGCM(self._key).decrypt(nonce, ciphertext, self._aad)
                result.append({"record_id": record_id, "record_type": kind,
                               "created_at": created, "updated_at": updated,
                               "data": json.loads(raw.decode("utf-8"))})
            except Exception as exc:
                raise VaultError(f"Record authentication failed: {record_id}") from exc
        return result

    def delete_record(self, record_id: str) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM customer_records WHERE record_id=? AND workspace_id=?",
            (record_id, self.workspace_id),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        if getattr(self, "_connection", None) is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "LocalVault":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
