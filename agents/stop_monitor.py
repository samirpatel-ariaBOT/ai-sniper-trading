import asyncio
import time
from datetime import datetime
from typing import Dict, Optional
import ccxt
from loguru import logger

class StopMonitor:
    def __init__(self, paper_engine, hard_stop_pct: float = 0.008, check_interval: float = 10.0, max_quote_age: float = 15.0):
        self.paper = paper_engine
        self.hard_stop_pct = hard_stop_pct
        self.check_interval = check_interval
        self.max_quote_age = max_quote_age
        self.exchange = ccxt.mexc({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"}
        })
        self._task = None
        self._running = False
        self.last_quote_time: Dict[str, float] = {}

    def start(self):
        if self._task is None or self._task.done():
            self._running = True
            self._task = asyncio.create_task(self._monitor_loop())
            logger.info("StopMonitor started")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def check_now(self, symbol: str = None):
        await self._check_positions(symbol_filter=symbol)

    async def _monitor_loop(self):
        while self._running:
            try:
                await self._check_positions()
            except Exception as e:
                logger.error(f"StopMonitor error: {e}")
            await asyncio.sleep(self.check_interval)

    async def _check_positions(self, symbol_filter: str = None):
        if not self.paper.state.positions:
            return
        now = time.time()
        for pid, pos in list(self.paper.state.positions.items()):
            if not pos or (symbol_filter and pos.symbol != symbol_filter):
                continue
            try:
                await asyncio.sleep(0.6)
                ticker = self.exchange.fetch_ticker(pos.symbol)
                price = ticker.get("last") or ticker.get("bid") or ticker.get("ask")
                quote_ts = ticker.get("timestamp")
                if quote_ts:
                    age = (now * 1000 - quote_ts) / 1000
                    if age > self.max_quote_age:
                        logger.warning(f"Stale stop quote {pos.symbol} age={age:.1f}s")
                        continue
                self.last_quote_time[pos.symbol] = now
                if not price or price <= 0:
                    continue
                stop_price = pos.entry_price * (1 - self.hard_stop_pct) if pos.direction == "long" else pos.entry_price * (1 + self.hard_stop_pct)
                hit = (pos.direction == "long" and price <= stop_price) or (pos.direction == "short" and price >= stop_price)
                if hit:
                    logger.warning(f"HARD STOP HIT {pos.symbol} {pos.direction} entry={pos.entry_price:.6f} stop={stop_price:.6f} now={price:.6f}")
                    self.paper.close_position(pid, price, reason="hard_stop")
            except Exception as e:
                logger.error(f"Stop check failed for {pos.symbol}: {e}")
