import sqlite3
from typing import Dict
from loguru import logger
from pathlib import Path

class LearningAgent:
    def __init__(self, config: dict, db_path: str = "data/learning.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
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
        if not scores:
            return
        with sqlite3.connect(self.db_path) as conn:
            for factor, score in scores.items():
                if abs(score) < 0.05:
                    continue
                cur = conn.execute(
                    "SELECT wins, losses FROM factor_performance WHERE factor = ?",
                    (factor,)
                )
                row = cur.fetchone()
                if row:
                    wins, losses = row
                    if won:
                        wins += 1
                    else:
                        losses += 1
                    total = wins + losses
                    # Softer adjustment: only move after clear under/over performance
                    adjust = (wins / total - 0.5) * 0.15 if total >= self.min_trades else 0.0
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
            conn.commit()

    def get_adjustments(self) -> Dict[str, float]:
        """Return weight_adjust for every factor that has enough trades."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT factor, weight_adjust FROM factor_performance WHERE (wins + losses) >= ?",
                (self.min_trades,)
            )
            return {row[0]: row[1] for row in cur.fetchall()}

    def get_stats(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT factor, wins, losses, weight_adjust FROM factor_performance")
            return {row[0]: {"wins": row[1], "losses": row[2], "adjust": row[3]} for row in cur.fetchall()}
