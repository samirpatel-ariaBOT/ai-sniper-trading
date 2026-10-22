"""
Order Book Agent - Liquidity and wall detection
"""
import ccxt
from typing import Dict
from loguru import logger

class OrderBookAgent:
    def __init__(self, config: dict):
        self.exchange = ccxt.mexc({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
        })
        self.depth_levels = config.get("orderbook", {}).get("depth_levels", 20)

    def analyze(self, symbol: str, current_price: float) -> Dict:
        try:
            book = self.exchange.fetch_order_book(symbol, limit=self.depth_levels)
        except Exception as e:
            logger.warning(f"OrderBook fetch failed for {symbol}: {e}")
            return {"imbalance": 0.0, "near_wall": False, "wall_side": None}

        bids = book.get("bids", [])
        asks = book.get("asks", [])
        if not bids or not asks:
            return {"imbalance": 0.0, "near_wall": False, "wall_side": None}

        bid_vol = sum(b[1] for b in bids[:10])
        ask_vol = sum(a[1] for a in asks[:10])
        total = bid_vol + ask_vol
        imbalance = (bid_vol - ask_vol) / total if total > 0 else 0.0

        near_wall = False
        wall_side = None
        for price, vol in bids[:5]:
            if abs(price - current_price) / current_price < 0.003 and vol > bid_vol / 3:
                near_wall = True
                wall_side = "bid"
                break
        for price, vol in asks[:5]:
            if abs(price - current_price) / current_price < 0.003 and vol > ask_vol / 3:
                near_wall = True
                wall_side = "ask"
                break

        return {
            "imbalance": round(imbalance, 3),
            "near_wall": near_wall,
            "wall_side": wall_side,
        }
