from datetime import datetime, timedelta
from typing import Optional

class RiskAgent:
    def __init__(self, config: dict):
        self.risk_pct = config.get("risk", {}).get("risk_per_trade", 0.055)
        self.daily_limit = config.get("risk", {}).get("daily_loss_limit", 0.12)
        self.min_equity = config.get("risk", {}).get("min_equity_floor", 5000.0)
        self.max_notional_pct = 0.18

        # Cooldown
        self.big_loss_pct = 0.025          # 2.5%
        self.big_loss_minutes = 15
        self.streak_count = 3
        self.streak_minutes = 30

        self.cooldown_until: Optional[datetime] = None
        self.consecutive_losses = 0

    def is_cooldown_active(self) -> bool:
        if self.cooldown_until is None:
            return False
        return datetime.utcnow() < self.cooldown_until

    def check(self, equity: float, daily_pnl: float, open_positions: int) -> tuple:
        if equity < self.min_equity:
            return False, "equity floor"
        if daily_pnl < -self.daily_limit * equity:
            return False, "daily loss limit"
        if self.is_cooldown_active():
            remaining = (self.cooldown_until - datetime.utcnow()).total_seconds() / 60
            return False, f"cooldown ({remaining:.0f} min left)"
        return True, "ok"

    def record_trade_result(self, equity: float, pnl: float):
        if pnl < 0:
            self.consecutive_losses += 1
            loss_pct = abs(pnl) / equity if equity > 0 else 0
            if loss_pct >= self.big_loss_pct:
                self.cooldown_until = datetime.utcnow() + timedelta(minutes=self.big_loss_minutes)
                self.consecutive_losses = 0
                return
            if self.consecutive_losses >= self.streak_count:
                self.cooldown_until = datetime.utcnow() + timedelta(minutes=self.streak_minutes)
                self.consecutive_losses = 0
                return
        else:
            self.consecutive_losses = 0

    def position_size(self, equity: float, price: float, stop_distance: float) -> float:
        if price <= 0 or stop_distance <= 0:
            return 0
        risk_amount = equity * self.risk_pct
        size = risk_amount / stop_distance
        max_notional = equity * self.max_notional_pct
        max_size = max_notional / price
        return min(size, max_size)
