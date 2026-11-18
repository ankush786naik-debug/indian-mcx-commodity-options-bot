import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path


class SignalHistory:
    def __init__(self, database_path="data/signals.db"):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dedupe_key TEXT NOT NULL UNIQUE,
                    commodity TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    instrument_key TEXT,
                    expiry TEXT,
                    strike REAL,
                    entry REAL,
                    stop_loss REAL,
                    target1 REAL,
                    target2 REAL,
                    lots INTEGER,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
            """)

    @staticmethod
    def make_dedupe_key(signal):
        option = signal.get("option", {})

        identity = "|".join([
            str(signal.get("commodity", "")),
            str(signal.get("signal", "")),
            str(option.get("instrument_key", "")),
            str(option.get("expiry", "")),
            str(option.get("strike", "")),
            datetime.now().astimezone().date().isoformat(),
        ])

        return hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

    def save_signal(self, signal):
        if not isinstance(signal, dict):
            raise ValueError("Signal must be a dictionary.")

        if signal.get("signal") not in ("BUY_CALL", "BUY_PUT", "NO_TRADE"):
            raise ValueError("Invalid signal type.")

        option = signal.get("option", {})

        dedupe_key = self.make_dedupe_key(signal)

        created_at = signal.get(
            "timestamp",
            datetime.now().astimezone().isoformat(),
        )

        with self.connect() as connection:
            cursor = connection.execute("""
                INSERT OR IGNORE INTO signals (
                    dedupe_key,
                    commodity,
                    signal,
                    instrument_key,
                    expiry,
                    strike,
                    entry,
                    stop_loss,
                    target1,
                    target2,
                    lots,
                    status,
                    created_at,
                    payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dedupe_key,
                signal.get("commodity"),
                signal.get("signal"),
                option.get("instrument_key"),
                option.get("expiry"),
                option.get("strike"),
                signal.get("entry"),
                signal.get("stop_loss"),
                signal.get("target1"),
                signal.get("target2"),
                signal.get("lots"),
                signal.get("status", "UNKNOWN"),
                created_at,
                json.dumps(signal, default=str),
            ))

            return cursor.rowcount == 1

    def get_recent_signals(self, limit=50):
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("Limit must be a positive integer.")

        with self.connect() as connection:
            rows = connection.execute("""
                SELECT *
                FROM signals
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()

        return [dict(row) for row in rows]

    def close(self):
        # Connections are opened and closed per operation.
        pass
      
