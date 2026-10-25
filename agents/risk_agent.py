import time
import json
import os
from loguru import logger

class RiskAgent:
    def __init__(self, config):
        self.risk_pct = config.get("risk", {}).get("risk_per_trade", 0.055)
        self.daily_limit = config.get("risk", {}).get("daily_loss_limit", 0.12)
        self.min_equity = config.get("risk", {}).get("min_equity_floor", 5000.0)
        self.max_notional_pct = config.get("risk", {}).get("max_notional_pct", 0.18)
        self.cooldown_seconds = config.get("risk", {}).get("cooldown_seconds", 300)  # 5 min
        self.cooldown_file = "data/cooldowns.json"
        self.cooldowns = self._load_cooldowns()

    def _load_cooldowns(self):
        if os.path.exists(self.cooldown_file):
            try:
                with open(self.cooldown_file) as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_cooldowns(self):
        os.makedirs("data", exist_ok=True)
        with open(self.cooldown_file, "w") as f:
            json.dump(self.cooldowns, f)

    def record_exit(self, symbol: str, pnl: float):
        """Call this after every exit so cooldown is enforced."""
        now = time.time()
        if pnl < 0:
            self.cooldowns[symbol] = now
            self._save_cooldowns()
            logger.info(f"Cooldown set for {symbol} ({self.cooldown_seconds}s)")

    def is_on_cooldown(self, symbol: str) -> bool:
        if symbol not in self.cooldowns:
            return False
        elapsed = time.time() - self.cooldowns[symbol]
        if elapsed < self.cooldown_seconds:
            return True
        # Expired
        del self.cooldowns[symbol]
        self._save_cooldowns()
        return False

    def check(self, equity, daily_pnl, open_positions, symbol=None):
        if equity < self.min_equity:
            return False, "equity floor"
        if daily_pnl < -self.daily_limit * equity:
            return False, "daily loss limit"
        if symbol and self.is_on_cooldown(symbol):
            return False, "cooldown"
        return True, "ok"

    def position_size(self, equity, price, stop_distance):
        if price <= 0 or stop_distance <= 0:
            return 0
        risk_amount = equity * self.risk_pct
        size = risk_amount / stop_distance
        max_notional = equity * self.max_notional_pct
        max_size = max_notional / price
        return min(size, max_size)
