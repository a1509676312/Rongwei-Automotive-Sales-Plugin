"""Local-first SQLite storage for customer memory and sales workflow.

All records stay on this computer by default. This module makes no network calls.
The database contains customer business data and must never be committed to source control.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_data_dir() -> Path:
    override = os.getenv("RONGWEI_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".rongwei-automotive-sales"


class LocalStore:
    """A small, per-user SQLite store with explicit backup and restore operations."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.data_dir = (Path(database_path).expanduser().parent if database_path else default_data_dir())
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.database_path = Path(database_path).expanduser() if database_path else self.data_dir / "rongwei.sqlite3"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 15000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY, name TEXT, company TEXT, phone TEXT,
                whatsapp TEXT, telegram TEXT, email TEXT, country TEXT, city TEXT,
                buyer_type TEXT, facts_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
            CREATE INDEX IF NOT EXISTS idx_customers_country ON customers(country);
            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(id),
                occurred_at TEXT NOT NULL, source TEXT NOT NULL, content TEXT NOT NULL,
                language TEXT, evidence_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_interactions_customer_time ON interactions(customer_id, occurred_at);
            CREATE TABLE IF NOT EXISTS ports (
                id TEXT PRIMARY KEY, country TEXT NOT NULL, name TEXT NOT NULL,
                city TEXT, transport_type TEXT NOT NULL DEFAULT 'seaport',
                status TEXT NOT NULL DEFAULT 'historical_reference',
                source_customer_id TEXT, source_note TEXT, confirmed_at TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ports_country ON ports(country);
            CREATE TABLE IF NOT EXISTS quotes (
                id TEXT PRIMARY KEY, customer_id TEXT REFERENCES customers(id),
                created_at TEXT NOT NULL, version INTEGER NOT NULL,
                terms TEXT NOT NULL, currency TEXT NOT NULL, payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_quotes_customer ON quotes(customer_id, created_at);
            CREATE TABLE IF NOT EXISTS followups (
                id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(id),
                due_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open',
                objective TEXT NOT NULL, result TEXT, created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_followups_due ON followups(status, due_at);
            CREATE TABLE IF NOT EXISTS commitments (
                id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(id),
                owner TEXT NOT NULL, description TEXT NOT NULL, due_at TEXT,
                status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_commitments_due ON commitments(status, due_at);
            CREATE TABLE IF NOT EXISTS sales_experiences (
                id TEXT PRIMARY KEY, country TEXT, buyer_type TEXT, context TEXT NOT NULL,
                selected_strategy TEXT, outcome TEXT NOT NULL, confidence TEXT NOT NULL,
                source_customer_id TEXT, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_experiences_country ON sales_experiences(country);
            CREATE TABLE IF NOT EXISTS advertisements (
                id TEXT PRIMARY KEY, source TEXT, vehicle_label TEXT, content TEXT,
                image_path TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS customer_ad_links (
                customer_id TEXT NOT NULL REFERENCES customers(id),
                advertisement_id TEXT NOT NULL REFERENCES advertisements(id),
                PRIMARY KEY(customer_id, advertisement_id)
            );
            """)
        try:
            os.chmod(self.data_dir, 0o700)
            if self.database_path.exists():
                os.chmod(self.database_path, 0o600)
        except OSError:
            # Windows ACLs are managed by the operating system; POSIX mode bits may not apply.
            pass

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    def create_customer(self, *, name: str | None = None, company: str | None = None,
                        phone: str | None = None, country: str | None = None,
                        city: str | None = None, buyer_type: str | None = None,
                        facts: dict[str, Any] | None = None, **contacts: Any) -> str:
        customer_id, now = str(uuid.uuid4()), _now()
        with self._connect() as db:
            db.execute("""INSERT INTO customers
                (id,name,company,phone,whatsapp,telegram,email,country,city,buyer_type,facts_json,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (customer_id, name, company, phone, contacts.get("whatsapp"),
                 contacts.get("telegram"), contacts.get("email"), country, city,
                 buyer_type, json.dumps(facts or {}, ensure_ascii=False), now, now))
        return customer_id

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
        result = self._row(row)
        if result:
            result["facts"] = json.loads(result.pop("facts_json"))
        return result

    def search_customers(self, *, country: str | None = None, query: str | None = None,
                         limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        clauses, params = [], []
        if country:
            clauses.append("country = ?")
            params.append(country)
        if query:
            clauses.append("(name LIKE ? OR company LIKE ? OR phone LIKE ? OR city LIKE ?)")
            term = f"%{query}%"
            params.extend([term, term, term, term])
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._connect() as db:
            rows = db.execute(f"SELECT * FROM customers{where} ORDER BY updated_at DESC LIMIT ?",
                              (*params, limit)).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["facts"] = json.loads(item.pop("facts_json"))
            output.append(item)
        return output

    def append_interaction(self, customer_id: str, content: str, *, source: str = "user_input",
                           language: str | None = None, occurred_at: str | None = None,
                           evidence: dict[str, Any] | None = None) -> str:
        interaction_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("""INSERT INTO interactions
                (id,customer_id,occurred_at,source,content,language,evidence_json)
                VALUES (?,?,?,?,?,?,?)""",
                (interaction_id, customer_id, occurred_at or _now(), source, content,
                 language, json.dumps(evidence or {}, ensure_ascii=False)))
            db.execute("UPDATE customers SET updated_at=? WHERE id=?", (_now(), customer_id))
        return interaction_id

    def list_interactions(self, customer_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("""SELECT * FROM interactions WHERE customer_id=?
                ORDER BY occurred_at DESC LIMIT ?""", (customer_id, max(1, min(limit, 500)))).fetchall()
        return [dict(row) for row in rows]

    def add_port(self, country: str, name: str, *, city: str | None = None,
                 transport_type: str = "seaport", status: str = "historical_reference",
                 source_customer_id: str | None = None, source_note: str | None = None,
                 confirmed_at: str | None = None) -> str:
        allowed_status = {"confirmed", "historical_reference", "ai_candidate", "expired"}
        allowed_transport = {"seaport", "rail_terminal", "border_crossing", "inland_terminal", "airport"}
        if status not in allowed_status or transport_type not in allowed_transport:
            raise ValueError("Unsupported port status or transport type.")
        port_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("""INSERT INTO ports
                (id,country,name,city,transport_type,status,source_customer_id,source_note,confirmed_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (port_id,country,name,city,transport_type,status,source_customer_id,
                 source_note,confirmed_at,_now()))
        return port_id

    def recommend_ports(self, country: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("""SELECT * FROM ports WHERE country=?
                AND status IN ('confirmed','historical_reference','ai_candidate')
                ORDER BY CASE status WHEN 'confirmed' THEN 0 WHEN 'historical_reference' THEN 1 ELSE 2 END,
                updated_at DESC LIMIT ?""", (country, max(1, min(limit, 100)))).fetchall()
        return [dict(row) for row in rows]

    def add_followup(self, customer_id: str, due_at: str, objective: str) -> str:
        followup_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("""INSERT INTO followups(id,customer_id,due_at,objective,created_at)
                VALUES(?,?,?,?,?)""", (followup_id,customer_id,due_at,objective,_now()))
        return followup_id

    def list_due_followups(self, as_of: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("""SELECT f.*, c.name, c.company, c.country FROM followups f
                JOIN customers c ON c.id=f.customer_id
                WHERE f.status='open' AND f.due_at<=?
                ORDER BY f.due_at LIMIT ?""", (as_of or _now(), max(1,min(limit,500)))).fetchall()
        return [dict(row) for row in rows]

    def complete_followup(self, followup_id: str, result: str) -> None:
        with self._connect() as db:
            cursor = db.execute("""UPDATE followups SET status='completed',result=?,completed_at=?
                WHERE id=? AND status='open'""", (result,_now(),followup_id))
            if cursor.rowcount != 1:
                raise ValueError("Open follow-up not found.")

    def add_commitment(self, customer_id: str, owner: str, description: str,
                       due_at: str | None = None) -> str:
        commitment_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("""INSERT INTO commitments(id,customer_id,owner,description,due_at,created_at)
                VALUES(?,?,?,?,?,?)""", (commitment_id,customer_id,owner,description,due_at,_now()))
        return commitment_id

    def add_experience(self, *, context: str, outcome: str, confidence: str,
                       country: str | None = None, buyer_type: str | None = None,
                       selected_strategy: str | None = None,
                       source_customer_id: str | None = None) -> str:
        if confidence not in {"verified", "repeated_pattern", "single_case", "inference"}:
            raise ValueError("Invalid experience confidence.")
        experience_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("""INSERT INTO sales_experiences
                (id,country,buyer_type,context,selected_strategy,outcome,confidence,source_customer_id,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (experience_id,country,buyer_type,context,selected_strategy,outcome,confidence,
                 source_customer_id,_now()))
        return experience_id

    def find_experiences(self, country: str | None = None, buyer_type: str | None = None,
                         limit: int = 20) -> list[dict[str, Any]]:
        clauses, params = [], []
        if country:
            clauses.append("country=?")
            params.append(country)
        if buyer_type:
            clauses.append("buyer_type=?")
            params.append(buyer_type)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as db:
            rows = db.execute(f"SELECT * FROM sales_experiences{where} ORDER BY created_at DESC LIMIT ?",
                              (*params,max(1,min(limit,100)))).fetchall()
        return [dict(row) for row in rows]

    def backup(self, destination: str | Path | None = None) -> Path:
        target = Path(destination) if destination else self.data_dir / "backups" / f"rongwei-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sqlite3"
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._connect() as source, sqlite3.connect(target) as dest:
            source.backup(dest)
            check = dest.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                target.unlink(missing_ok=True)
                raise RuntimeError("Backup integrity check failed.")
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
        return target

    def restore(self, source: str | Path) -> None:
        backup_path = Path(source).expanduser()
        if not backup_path.is_file():
            raise FileNotFoundError("Backup file does not exist.")
        with sqlite3.connect(backup_path) as candidate:
            check = candidate.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                raise ValueError("Backup is corrupt; original data was not changed.")
        self.backup()
        temp_path = self.database_path.with_suffix(".restore.tmp")
        shutil.copy2(backup_path, temp_path)
        os.replace(temp_path, self.database_path)
        self._initialize()
