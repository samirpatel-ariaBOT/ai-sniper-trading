"""
Decision Agent - Meeting room style final call
"""
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class Decision:
    action: str
    side: Optional[str]
    confidence: float
    reason: str
    scores: Dict

class DecisionAgent:
    def __init__(self, config: dict):
        self.min_confidence = config.get("decision", {}).get("min_confidence", 0.62)
        self.require_volume_confirm = config.get("decision", {}).get("require_volume_confirm", True)

    def decide(self, oracle_signal, risk_approved, risk_reason, scanner_change_pct=0.0, news_flag=None, sentiment_score=None, orderbook=None, learning_adjustments=None):
        scores = {
            "oracle": oracle_signal.get("raw_score", 0.0),
            "confidence": oracle_signal.get("confidence", 0.0),
            "scanner_change": scanner_change_pct,
            "news": 0.0,
            "sentiment": sentiment_score or 0.0,
        }

        side = oracle_signal.get("side")
        confidence = oracle_signal.get("confidence", 0.0)

        if not risk_approved:
            return Decision("SKIP", None, 0.0, f"Risk rejected: {risk_reason}", scores)

        if not side or confidence < self.min_confidence:
            return Decision("WAIT", None, confidence, "Oracle confidence too low", scores)

        if orderbook and orderbook.get("near_wall"):
            wall_side = orderbook.get("wall_side")
            if (side == "long" and wall_side == "ask") or (side == "short" and wall_side == "bid"):
                return Decision("WAIT", side, confidence, f"Near {wall_side} wall", scores)

        if learning_adjustments:
            for factor, adj in learning_adjustments.items():
                confidence = min(max(confidence + adj * 0.5, 0.4), 0.95)

        if confidence >= self.min_confidence:
            return Decision("BUY", side, round(confidence, 3), "All agents aligned", scores)

        return Decision("WAIT", side, confidence, "Marginal confidence", scores)
