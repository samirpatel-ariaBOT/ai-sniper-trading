import ccxt

class DataFeed:
    def __init__(self):
        self.exchange = ccxt.mexc({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"}
        })

    def fetch_ohlcv(self, symbol: str, timeframe: str = "5m", limit: int = 50):
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as e:
            print(f"OHLCV error: {e}")
            return None

    def fetch_ticker(self, symbol: str):
        try:
            t = self.exchange.fetch_ticker(symbol)
            return t.get("last") or 0
        except:
            return 0
