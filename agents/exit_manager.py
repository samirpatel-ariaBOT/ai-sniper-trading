"""
Exit Manager - Fast entry / fast exit logic
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class ExitSignal:
    should_exit: bool
    reason: str
    exit_price: Optional[float] = None

class ExitManager:
    def __init__(self, config: dict):
        self.quick_profit = config.get("exit", {}).get("quick_profit_pct", 0.005)
        self.trailing_activation = config.get("exit", {}).get("trailing_activation_pct", 0.003)
        self.trailing_distance = config.get("exit", {}).get("trailing_distance_pct", 0.002)
        self.time_stop_minutes = config.get("exit", {}).get("time_stop_minutes", 10)

    def check_exit(self, entry_price, current_price, direction, entry_time, highest_favorable):
        now = datetime.utcnow()
        hold_minutes = (now - entry_time).total_seconds() / 60

        if hold_minutes >= self.time_stop_minutes:
            return ExitSignal(True, f"Time stop ({self.time_stop_minutes}min)", current_price)

        if direction == "long":
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price

        if pnl_pct >= self.quick_profit:
            return ExitSignal(True, f"Quick profit +{pnl_pct*100:.2f}%", current_price)

        return ExitSignal(False, "Hold")
