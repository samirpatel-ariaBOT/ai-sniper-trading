import asyncio
import time
import yaml
from datetime import datetime
from loguru import logger

from agents.risk_agent import RiskAgent
from agents.exit_manager import ExitManager
from agents.oracle_agent import OracleAgent
from agents.decision_agent import DecisionAgent
from agents.news_agent import NewsAgent
from agents.sentiment_agent import SentimentAgent
from agents.orderbook_agent import OrderBookAgent
from agents.learning_agent import LearningAgent
from core.paper_engine import PaperEngine
from core.database import TradeDatabase
from core.data_feed import DataFeed
from core.scanner import TopMoversScanner

def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)

async def main():
    config = load_config()
    risk = RiskAgent(config)
    exit_mgr = ExitManager(config)
    oracle = OracleAgent(config)
    decision = DecisionAgent(config)
    news = NewsAgent(config)
    sentiment = SentimentAgent(config)
    orderbook = OrderBookAgent(config)
    learning = LearningAgent(config, config["database"]["path"])
    paper = PaperEngine(config["paper"]["initial_equity"])
    db = TradeDatabase(config["database"]["path"])
    data = DataFeed()
    scanner = TopMoversScanner(
        min_volume_usdt=config.get("scanner", {}).get("min_volume_usdt", 500000),
        top_n=config.get("scanner", {}).get("top_n", 5),
    )

    logger.info(f"AI Sniper Trading started | Equity: ${paper.state.equity:.2f}")
    EXIT_INTERVAL = 2
    last_scan = 0
    symbols = []

    while True:
        try:
            now = time.time()
            has_pos = len(paper.state.positions) > 0

            if has_pos:
                for pid, pos in list(paper.state.positions.items()):
                    price = data.fetch_ticker(pos.symbol)
                    if not price:
                        continue
                    paper.update_favorable(pid, price)
                    sig = exit_mgr.check_exit(pos.entry_price, price, pos.direction, pos.entry_time, pos.highest_favorable)
                    if sig.should_exit:
                        pnl = paper.close_position(pid, price)
                        if pnl is not None:
                            db.log_trade(pos.symbol, pos.direction, pos.entry_price, price, pos.size, pnl)
                            learning.record_trade({}, pnl > 0)
                            logger.info(f"EXIT {pos.symbol} pnl={pnl:.2f} equity={paper.state.equity:.2f}")

            if now - last_scan > 60 and not has_pos:
                symbols = scanner.get_trading_symbols()
                last_scan = now
                logger.info(f"Scan: {symbols[:5]}")

            if symbols and not has_pos:
                for sym in symbols[:3]:
                    ohlcv = data.fetch_ohlcv(sym, "5m", 50)
                    if not ohlcv:
                        continue
                    price = ohlcv[-1][4]
                    oracle_sig = {"side": "long", "confidence": 0.65, "raw_score": 0.5}
                    ok, msg = risk.check(paper.state.equity, 0, len(paper.state.positions))
                    ob = orderbook.analyze(sym, price) if config.get("orderbook", {}).get("enabled", True) else None
                    learn_adj = learning.get_adjustments()
                    action = decision.decide(oracle_sig, ok, msg, 0, None, None, ob, learn_adj)
                    if action.action == "BUY":
                        size = risk.position_size(paper.state.equity, price, price * 0.01)
                        if size > 0:
                            pid = paper.open_position(sym, "long", size, price, price * 0.01)
                            logger.info(f"ENTRY {sym} size={size:.4f} price={price}")
                            break

            await asyncio.sleep(EXIT_INTERVAL if has_pos else 10)
        except Exception as e:
            logger.error(f"Loop error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
