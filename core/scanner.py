from typing import List, Dict
import ccxt

class TopMoversScanner:
    def __init__(self, min_volume_usdt: float = 500000, top_n: int = 5):
        self.exchange = ccxt.mexc({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"}
        })
        self.min_volume = min_volume_usdt
        self.top_n = top_n

    def get_candidates(self) -> Dict[str, List[Dict]]:
        try:
            tickers = self.exchange.fetch_tickers()
            candidates = []
            for symbol, ticker in tickers.items():
                if not symbol.endswith(":USDT"):
                    continue
                quote_volume = ticker.get("quoteVolume") or 0
                percentage = ticker.get("percentage") or 0
                last = ticker.get("last") or 0
                if quote_volume < self.min_volume or last <= 0:
                    continue
                candidates.append({"symbol": symbol, "percentage": percentage, "volume": quote_volume, "last": last})
            gainers = sorted([c for c in candidates if c["percentage"] > 0], key=lambda x: x["percentage"], reverse=True)[:self.top_n]
            losers = sorted([c for c in candidates if c["percentage"] < 0], key=lambda x: x["percentage"])[:self.top_n]
            return {"gainers": gainers, "losers": losers}
        except Exception as e:
            print(f"Scanner error: {e}")
            return {"gainers": [], "losers": []}

    def get_trading_symbols(self) -> List[str]:
        data = self.get_candidates()
        symbols = [g["symbol"] for g in data["gainers"]] + [l["symbol"] for l in data["losers"]]
        seen = set()
        unique = []
        for s in symbols:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        return unique[:8]
