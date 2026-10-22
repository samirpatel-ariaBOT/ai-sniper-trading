"""
Learning Agent - Tracks factor performance and adjusts weights
"""
import sqlite3
from typing import Dict
from loguru import logger

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
            conn.commit()

    def record_trade(self, scores: Dict, won: bool):
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
                    conn.execute("UPDATE factor_performance SET wins=?, losses=?, weight_adjust=? WHERE factor=?", (wins, losses, adjust, factor))
                else:
                    wins = 1 if won else 0
                    losses = 0 if won else 1
                    conn.execute("INSERT INTO factor_performance (factor, wins, losses, weight_adjust) VALUES (?, ?, ?, 0.0)", (factor, wins, losses))
            conn.commit()

    def get_adjustments(self) -> Dict[str, float]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT factor, weight_adjust FROM factor_performance WHERE (wins + losses) >= ?", (self.min_trades,))
            return {row[0]: row[1] for row in cur.fetchall()}

    def get_pattern_win_rate(self, factor_combo: str) -> float:
        return 0.5
