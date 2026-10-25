"""
Oracle Agent - Multi-factor scoring with signed direction
"""
import pandas as pd
import numpy as np
from loguru import logger

class OracleAgent:
    def __init__(self, config: dict):
        self.min_confidence = config.get("oracle", {}).get("confidence_threshold", 0.62)

    def score(self, candles):
        """
        Returns (signed_score, label)
        signed_score: positive = bullish, negative = bearish
        Range roughly -1.0 to +1.0
        """
        if not candles or len(candles) < 30:
            return 0.0, "insufficient"

        df = pd.DataFrame(candles, columns=["t", "o", "h", "l", "c", "v"])
        for col in ["o", "h", "l", "c", "v"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna()
        if len(df) < 20:
            return 0.0, "insufficient"

        close = df["c"]
        high = df["h"]
        low = df["l"]
        volume = df["v"]

        # Signed momentum (ROC + EMA slope)
        roc = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10]
        ema_fast = close.ewm(span=8, adjust=False).mean()
        ema_slow = close.ewm(span=21, adjust=False).mean()
        ema_slope = (ema_fast.iloc[-1] - ema_fast.iloc[-3]) / ema_fast.iloc[-3] if ema_fast.iloc[-3] != 0 else 0

        momentum = 0.0
        if roc > 0.006 and ema_slope > 0:
            momentum = min(roc * 12 + ema_slope * 25, 1.0)
        elif roc < -0.006 and ema_slope < 0:
            momentum = max(roc * 12 + ema_slope * 25, -1.0)

        # RSI (mean reversion bias)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50

        rsi_bias = 0.0
        if rsi_val < 30:
            rsi_bias = 0.3
        elif rsi_val > 70:
            rsi_bias = -0.3

        # Volume confirmation
        vol_sma = volume.rolling(20).mean()
        vol_ratio = volume.iloc[-1] / vol_sma.iloc[-1] if vol_sma.iloc[-1] > 0 else 1.0
        vol_boost = min((vol_ratio - 1) * 0.2, 0.2) if vol_ratio > 1 else 0

        # Final signed score
        raw = momentum * 0.6 + rsi_bias * 0.3 + (0.1 if vol_boost > 0 else 0)
        signed_score = max(min(raw, 1.0), -1.0)

        label = "bullish" if signed_score > 0.15 else "bearish" if signed_score < -0.15 else "neutral"
        return round(signed_score, 3), label
