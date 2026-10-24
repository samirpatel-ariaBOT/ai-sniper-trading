import ccxt
from typing import Optional, List, Dict
import asyncio

class DataFeed:
    def __init__(self):
        self.exchange = ccxt.mexc({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"}
        })

    async def fetch_ohlcv(self, symbol: str, timeframe: str = "5m", limit: int = 50):
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as e:
            print(f"OHLCV error: {e}")
            return None

    async def fetch_candles(self, symbol: str, timeframe: str = "5m", limit: int = 50):
        return await self.fetch_ohlcv(symbol, timeframe, limit)

    async def fetch_ticker(self, symbol: str) -> float:
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker.get("last") or ticker.get("bid") or 0.0
        except Exception as e:
            print(f"Ticker error: {e}")
            return 0.0

    async def fetch_ticker_full(self, symbol: str):
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            print(f"Ticker full error: {e}")
            return None

    def close(self):
        pass
