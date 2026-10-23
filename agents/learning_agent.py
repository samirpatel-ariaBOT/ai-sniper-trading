import sqlite3
from typing import Dict

class LearningAgent:
    def __init__(self, config: dict, db_path: str = "data/trades.db"):
        self.db_path = db_path
        self.min_trades = config.get("learning", {}).get("min_trades", 10)
        self._init_table()

    def _init_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS factor_performance (
                    factor TEXT PRIMARY KEY,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    weight_adjust REAL DEFAULT 0.0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS symbol_performance (
                    symbol TEXT PRIMARY KEY,
                    recent_pnl REAL DEFAULT 0.0,
                    trades INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def record_trade(self, scores: Dict, won: bool, symbol: str = None, pnl: float = 0.0):
        with sqlite3.connect(self.db_path) as conn:
            for factor, score in scores.items():
                if abs(score) < 0.05:
                    continue
                cur = conn.execute("SELECT wins, losses FROM factor_performance WHERE factor = ?", (factor,))
                row = cur.fetchone()
                if row:
                    wins, losses = row
                    if won:
                        wins += 1
                    else:
                        losses += 1
                    total = wins + losses
                    adjust = (wins / total - 0.5) * 0.2 if total >= self.min_trades else 0.0
                    conn.execute(
                        "UPDATE factor_performance SET wins=?, losses=?, weight_adjust=? WHERE factor=?",
                        (wins, losses, adjust, factor)
                    )
                else:
                    wins = 1 if won else 0
                    losses = 0 if won else 1
                    conn.execute(
                        "INSERT INTO factor_performance (factor, wins, losses, weight_adjust) VALUES (?, ?, ?, 0.0)",
                        (factor, wins, losses)
                    )

            if symbol:
                cur = conn.execute("SELECT recent_pnl, trades FROM symbol_performance WHERE symbol = ?", (symbol,))
                row = cur.fetchone()
                if row:
                    recent, trades = row
                    recent = (recent * 0.7) + (pnl * 0.3)
                    trades += 1
                    conn.execute(
                        "UPDATE symbol_performance SET recent_pnl=?, trades=? WHERE symbol=?",
                        (recent, trades, symbol)
                    )
                else:
                    conn.execute(
                        "INSERT INTO symbol_performance (symbol, recent_pnl, trades) VALUES (?, ?, 1)",
                        (symbol, pnl)
                    )
            conn.commit()

    def get_adjustments(self, symbol: str = None) -> Dict[str, float]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT factor, weight_adjust FROM factor_performance WHERE (wins + losses) >= ?",
                (self.min_trades,)
            )
            adj = {row[0]: row[1] for row in cur.fetchall()}

            if symbol:
                cur = conn.execute("SELECT recent_pnl FROM symbol_performance WHERE symbol = ?", (symbol,))
                row = cur.fetchone()
                if row and row[0] is not None:
                    if row[0] < -20:
                        adj["symbol"] = -0.12
                    elif row[0] > 10:
                        adj["symbol"] = 0.08
            return adj

