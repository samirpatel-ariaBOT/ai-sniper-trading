class OracleAgent:
    def __init__(self, config):
        self.timeframe = config.get("oracle", {}).get("timeframe", "5m")
        self.threshold = config.get("oracle", {}).get("confidence_threshold", 0.62)

    def score(self, ohlcv):
        if not ohlcv or len(ohlcv) < 20:
            return 0.0, "no data"
        closes = [c[4] for c in ohlcv]
        roc = (closes[-1] - closes[-10]) / closes[-10] if closes[-10] else 0
        score = 0.5
        if abs(roc) > 0.01:
            score += 0.2
        return min(score, 1.0), "momentum"
