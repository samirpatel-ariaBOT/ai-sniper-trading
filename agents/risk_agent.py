class RiskAgent:
    def __init__(self, config):
        self.risk_pct = config.get("risk", {}).get("risk_per_trade", 0.055)
        self.daily_limit = config.get("risk", {}).get("daily_loss_limit", 0.12)
        self.min_equity = config.get("risk", {}).get("min_equity_floor", 5000.0)
        self.max_notional_pct = config.get("risk", {}).get("max_notional_pct", 0.18)

    def check(self, equity, daily_pnl, open_positions):
        if equity < self.min_equity:
            return False, "equity floor"
        if daily_pnl < -self.daily_limit * equity:
            return False, "daily loss limit"
        return True, "ok"

    def position_size(self, equity, price, stop_distance):
        if price <= 0 or stop_distance <= 0:
            return 0
        risk_amount = equity * self.risk_pct
        size = risk_amount / stop_distance
        max_notional = equity * self.max_notional_pct
        max_size = max_notional / price
        return min(size, max_size)

