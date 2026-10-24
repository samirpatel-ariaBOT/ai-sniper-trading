import sqlite3
from datetime import datetime
from typing import Optional


class TradeDatabase:
    def __init__(self, path: str = "data/trades.db"):
        self.path = path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                direction TEXT,
                entry_price REAL,
                exit_price REAL,
                size REAL,
                pnl REAL,
                entry_time TEXT,
                exit_time TEXT,
                reason TEXT
            )
        """)
        conn.commit()
        conn.close()

    def log_trade(self, symbol, direction, entry_price, exit_price, size, pnl,
                  entry_time: Optional[datetime] = None, reason: str = "exit"):
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        et = entry_time.isoformat() if entry_time else datetime.utcnow().isoformat()
        xt = datetime.utcnow().isoformat()
        cur.execute("""
            INSERT INTO trades (symbol, direction, entry_price, exit_price, size, pnl, entry_time, exit_time, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, direction, entry_price, exit_price, size, pnl, et, xt, reason))
        conn.commit()
        conn.close()
