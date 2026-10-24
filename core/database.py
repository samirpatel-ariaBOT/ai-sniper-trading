import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

class TradeDatabase:
    def __init__(self, path: str = "data/trades.db"):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    symbol TEXT,
                    direction TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    size REAL,
                    gross_pnl REAL,
                    net_pnl REAL,
                    fees REAL,
                    entry_time TEXT,
                    exit_time TEXT,
                    duration_minutes REAL,
                    outcome TEXT,
                    confidence REAL,
                    reason TEXT,
                    stop_price REAL,
                    entry_quote_age REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS open_positions (
                    id TEXT PRIMARY KEY,
                    symbol TEXT,
                    direction TEXT,
                    size REAL,
                    entry_price REAL,
                    entry_time TEXT,
                    stop_price REAL,
                    stop_distance REAL,
                    highest_favorable REAL
                )
            """)
            conn.commit()

    def log_trade(self, trade: Dict):
        with sqlite3.connect(self.path) as conn:
            entry_time = trade.get("entry_time")
            exit_time = trade.get("exit_time")
            duration = 0
            if entry_time and exit_time:
                if isinstance(entry_time, str):
                    entry_time = datetime.fromisoformat(entry_time)
                if isinstance(exit_time, str):
                    exit_time = datetime.fromisoformat(exit_time)
                duration = (exit_time - entry_time).total_seconds() / 60
            conn.execute("""
                INSERT OR REPLACE INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.get("pos_id"),
                trade.get("symbol"),
                trade.get("direction"),
                trade.get("entry_price"),
                trade.get("exit_price"),
                trade.get("size"),
                trade.get("gross_pnl"),
                trade.get("net_pnl"),
                trade.get("fees"),
                entry_time.isoformat() if hasattr(entry_time, "isoformat") else str(entry_time),
                exit_time.isoformat() if hasattr(exit_time, "isoformat") else str(exit_time),
                duration,
                "win" if trade.get("net_pnl", 0) > 0 else "loss",
                0.0,
                trade.get("reason", ""),
                trade.get("stop_price"),
                trade.get("entry_quote_age", 0)
            ))
            conn.commit()

    def save_open_positions(self, positions: list):
        with sqlite3.connect(self.path) as conn:
            conn.execute("DELETE FROM open_positions")
            for p in positions:
                conn.execute("""
                    INSERT INTO open_positions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p["id"], p["symbol"], p["direction"], p["size"],
                    p["entry_price"], p["entry_time"], p["stop_price"],
                    p["stop_distance"], p["highest_favorable"]
                ))
            conn.commit()

    def load_open_positions(self) -> list:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute("SELECT * FROM open_positions")
            rows = cur.fetchall()
            return [
                {
                    "id": r[0], "symbol": r[1], "direction": r[2], "size": r[3],
                    "entry_price": r[4], "entry_time": r[5], "stop_price": r[6],
                    "stop_distance": r[7], "highest_favorable": r[8]
                } for r in rows
            ]
