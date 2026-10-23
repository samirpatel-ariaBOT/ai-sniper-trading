"""
Decision Agent - Stricter multi-agent confirmation
BUY only when Oracle + Risk + OrderBook + Learning all agree
"""
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class Decision:
    action: str          # "BUY", "WAIT", "SKIP"
    side: Optional[str]
    confidence: float
    reason: str
    scores: Dict

class DecisionAgent:
    def __init__(self, config: dict):
        self.min_confidence = config.get("decision", {}).get("min_confidence", 0.68)
        self.require_volume = config.get("decision", {}).get("require_volume_confirm", True)

    def decide(
        self,
        oracle_signal: dict,
        risk_approved: bool,
        risk_reason: str,
        scanner_change_pct: float = 0.0,
        news_flag: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        orderbook: Optional[Dict] = None,
        learning_adjustments: Optional[Dict] = None,
    ) -> Decision:
        scores = {
            "oracle": oracle_signal.get("raw_score", 0.0),
            "confidence": oracle_signal.get("confidence", 0.0),
            "scanner_change": scanner_change_pct,
            "news": 0.0,
            "sentiment": sentiment_score or 0.0,
            "orderbook": 0.0,
        }

        side = oracle_signal.get("side")
        confidence = oracle_signal.get("confidence", 0.0)
        oracle_scores = oracle_signal.get("scores", {})

        # 1. Risk veto
        if not risk_approved:
            return Decision("SKIP", None, 0.0, f"Risk rejected: {risk_reason}", scores)

        # 2. Oracle must be clear and strong
        if not side or confidence < self.min_confidence:
            return Decision("WAIT", None, confidence, "Oracle confidence too low", scores)

        # 3. Volume confirmation required
        vol_score = oracle_scores.get("volume", 0.0)
        if self.require_volume and vol_score < 0.10:
            return Decision("WAIT", side, confidence, "Volume not confirming", scores)

        # 4. Order book must not strongly oppose
        if orderbook:
            imbalance = orderbook.get("imbalance", 0.0)
            scores["orderbook"] = imbalance
            near_wall = orderbook.get("near_wall", False)
            wall_side = orderbook.get("wall_side")

            if near_wall:
                if (side == "long" and wall_side == "ask") or (side == "short" and wall_side == "bid"):
                    return Decision("WAIT", side, confidence, f"Opposing {wall_side} wall", scores)

            # Require mild order book agreement
            if side == "long" and imbalance < -0.15:
                return Decision("WAIT", side, confidence, "Order book selling pressure", scores)
            if side == "short" and imbalance > 0.15:
                return Decision("WAIT", side, confidence, "Order book buying pressure", scores)

        # 5. Learning must not be strongly negative
        if learning_adjustments:
            for factor, adj in learning_adjustments.items():
                if adj < -0.15:
                    return Decision("WAIT", side, confidence, f"Learning negative on {factor}", scores)
                confidence = min(max(confidence + adj * 0.3, 0.5), 0.95)

        # 6. News / Sentiment soft veto
        if news_flag == "bearish" and side == "long":
            return Decision("WAIT", side, confidence, "News conflicts with long", scores)
        if news_flag == "bullish" and side == "short":
            return Decision("WAIT", side, confidence, "News conflicts with short", scores)

        if sentiment_score is not None:
            if (side == "long" and sentiment_score < -0.3) or (side == "short" and sentiment_score > 0.3):
                return Decision("WAIT", side, confidence, "Sentiment strongly against", scores)

        # Final
        return Decision("BUY", side, round(confidence, 3), "All agents aligned", scores)
