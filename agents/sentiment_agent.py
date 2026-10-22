"""
Sentiment Agent - Lightweight score (-1 to +1)
"""
from typing import Optional
from loguru import logger

class SentimentAgent:
    def __init__(self, config: dict):
        self.enabled = config.get("sentiment", {}).get("enabled", False)

    def get_score(self, symbol: str) -> Optional[float]:
        if not self.enabled:
            return None
        return None
