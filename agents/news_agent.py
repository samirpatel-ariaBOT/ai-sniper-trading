"""
News Agent - Lightweight catalyst flag
Returns: "bullish", "bearish", "neutral", or None
"""
from typing import Optional
from loguru import logger

class NewsAgent:
    def __init__(self, config: dict):
        self.enabled = config.get("news", {}).get("enabled", False)

    def get_flag(self, symbol: str) -> Optional[str]:
        if not self.enabled:
            return None
        return None
