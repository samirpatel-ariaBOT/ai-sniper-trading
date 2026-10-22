import sqlite3
from datetime import datetime

class TradeDatabase:
    def __init__(self, path: str = "data/trades.db"):
        self.path = path
        self._init()

    def _init(self):
        conn = sqlite3.connect(self.path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                direction TEXT,
                entry_price REAL,
                exit_price REAL,
                size REAL,
                pnl REAL,
                entry_time TEXT,
                exit_time TEXT
            )
        """)
        conn.commit()
        conn.close()

    def log_trade(self, symbol, direction, entry_price, exit_price, size, pnl):
        conn = sqlite3.connect(self.path)
        conn.execute(
            "INSERT INTO trades (symbol, direction, entry_price, exit_price, size, pnl, entry_time, exit_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, direction, entry_price, exit_price, size, pnl, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
