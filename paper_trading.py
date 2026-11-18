
import sqlite3
from pathlib import Path
from datetime import datetime


class PaperTrading:
    def __init__(self, database_path="data/paper_trades.db"):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instrument_key TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    target1 REAL NOT NULL,
                    target2 REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    exit_price REAL,
                    pnl REAL,
                    created_at TEXT NOT NULL,
                    closed_at TEXT
                )
            """)

    def open_trade(self, signal):
        if signal.get("status") != "PAPER_CANDIDATE":
            raise ValueError("Only validated paper candidates are accepted.")

        option = signal.get("option", {})
        instrument_key = option.get("instrument_key")

        if not instrument_key:
            raise ValueError("Instrument key is required.")

        entry = float(signal["entry"])
        stop = float(signal["stop_loss"])
        target1 = float(signal["target1"])
        target2 = float(signal["target2"])
        quantity = int(signal["quantity"])

        if not (0 < stop < entry < target1 < target2):
            raise ValueError("Invalid trade price levels.")

        if quantity <= 0:
            raise ValueError("Trade quantity must be positive.")

        with self.connect() as connection:
            cursor = connection.execute("""
                INSERT INTO paper_trades (
                    instrument_key, direction, entry, stop_loss,
                    target1, target2, quantity, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
            """, (
                instrument_key,
                signal["signal"],
                entry,
                stop,
                target1,
                target2,
                quantity,
                datetime.now().astimezone().isoformat(),
            ))

            return cursor.lastrowid

    def update_trade(self, trade_id, current_price):
        current_price = float(current_price)

        if current_price <= 0:
            raise ValueError("Current price must be positive.")

        with self.connect() as connection:
            trade = connection.execute(
                "SELECT * FROM paper_trades WHERE id = ?",
                (trade_id,),
            ).fetchone()

            if trade is None:
                raise ValueError("Paper trade not found.")

            if trade["status"] != "OPEN":
                return dict(trade)

            status = None

            if current_price <= trade["stop_loss"]:
                status = "STOP_LOSS"
            elif current_price >= trade["target2"]:
                status = "TARGET2"
            elif current_price >= trade["target1"]:
                status = "TARGET1"

            if status is None:
                return dict(trade)

            pnl = (
                current_price - trade["entry"]
            ) * trade["quantity"]

            connection.execute("""
                UPDATE paper_trades
                SET status = ?, exit_price = ?, pnl = ?, closed_at = ?
                WHERE id = ?
            """, (
                status,
                current_price,
                pnl,
                datetime.now().astimezone().isoformat(),
                trade_id,
            ))

            return {
                **dict(trade),
                "status": status,
                "exit_price": current_price,
                "pnl": pnl,
            }

    def get_open_trades(self):
        with self.connect() as connection:
            rows = connection.execute("""
                SELECT * FROM paper_trades
                WHERE status = 'OPEN'
                ORDER BY id DESC
            """).fetchall()

        return [dict(row) for row in rows]
