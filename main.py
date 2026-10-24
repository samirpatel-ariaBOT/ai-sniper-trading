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
from agents.stop_monitor import StopMonitor
from core.paper_engine import PaperEngine
from core.database import TradeDatabase
from core.data_feed import DataFeed
from core.scanner import TopMoversScanner

def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)

async def restore_positions(paper, db):
    saved = db.load_open_positions()
    for p in saved:
        from core.paper_engine import Position
        paper.state.positions[p["id"]] = Position(
            id=p["id"], symbol=p["symbol"], direction=p["direction"],
            size=p["size"], entry_price=p["entry_price"],
            entry_time=datetime.fromisoformat(p["entry_time"]),
            stop_distance=p["stop_distance"], stop_price=p["stop_price"],
            highest_favorable=p["highest_favorable"]
        )
    if saved:
        logger.info(f"Restored {len(saved)} open positions")

async def main():
    config = load_config()
    risk = RiskAgent(config)
    exit_mgr = ExitManager(config)
    oracle = OracleAgent(config)
    decision = DecisionAgent(config)
    news = NewsAgent(config)
    sentiment = SentimentAgent(config)
    orderbook = OrderBookAgent(config)
    learning = LearningAgent(config, config.get("learning", {}).get("db_path", "data/learning.db"))
    paper = PaperEngine(config["paper"]["initial_equity"], config["paper"].get("fee_rate", 0.0004))
    db = TradeDatabase(config["database"]["path"])
    data = DataFeed()
    scanner = TopMoversScanner(
        min_volume_usdt=config.get("scanner", {}).get("min_volume_usdt", 500000),
        top_n=config.get("scanner", {}).get("top_n", 5),
    )
    stop_monitor = StopMonitor(
        paper,
        hard_stop_pct=config.get("stop_monitor", {}).get("hard_stop_pct", 0.008),
        check_interval=config.get("stop_monitor", {}).get("check_interval", 10.0),
        max_quote_age=config.get("stop_monitor", {}).get("max_quote_age", 15.0)
    )
    stop_monitor.start()
    await restore_positions(paper, db)
    logger.info(f"Started | Equity: ${paper.state.equity:.2f}")
    last_scan = 0
    scan_interval = config.get("scanner", {}).get("rescan_interval_minutes", 15) * 60
    active_symbols = []
    max_entry_age = config.get("quote", {}).get("max_entry_age", 3.0)

    while True:
        try:
            now = time.time()
            has_pos = len(paper.state.positions) > 0
            if has_pos:
                for pid, pos in list(paper.state.positions.items()):
                    price = await data.fetch_ticker(pos.symbol)
                    if price <= 0:
                        continue
                    paper.update_favorable(pid, price)
                    exit_sig = exit_mgr.check_exit(pos.entry_price, price, pos.direction, pos.entry_time, pos.highest_favorable)
                    if exit_sig.should_exit:
                        result = paper.close_position(pid, price, reason=exit_sig.reason)
                        if result:
                            db.log_trade(result)
                            learning.record_trade({}, result["net_pnl"] > 0)
                            logger.info(f"EXIT {pos.symbol} {result['reason']} PnL={result['net_pnl']:.2f}")
                db.save_open_positions(paper.get_positions_snapshot())
            if (now - last_scan) >= scan_interval:
                last_scan = now
                active_symbols = scanner.get_trading_symbols()
                logger.info(f"Scan: {active_symbols}")
            for sym in active_symbols:
                if any(p.symbol == sym for p in paper.state.positions.values()):
                    continue
                ticker = await data.fetch_ticker_full(sym)
                if not ticker:
                    continue
                quote_age = (time.time() * 1000 - ticker.get("timestamp", 0)) / 1000
                if quote_age > max_entry_age:
                    continue
                price = ticker.get("last") or ticker.get("bid") or 0
                if price <= 0:
                    continue
                candles = await data.fetch_candles(sym, "5m", 50)
                if not candles:
                    continue
                score, label = oracle.score(candles)
                signal = {
                    "side": "long" if score > 0.65 else "short" if score < 0.35 else None,
                    "confidence": score,
                    "atr": price * 0.008
                }
                if not signal.get("side"):
                    continue
                stop_dist = signal.get("atr", price * 0.008) * 1.2
                risk_ok, msg = risk.check(paper.state.equity, paper.state.daily_pnl, len(paper.state.positions))
                if not risk_ok:
                    continue
                size = risk.position_size(paper.state.equity, price, stop_dist)
                if size <= 0:
                    continue
                pid = paper.open_position(sym, signal["side"], size, price, stop_dist, quote_age=quote_age)
                if pid:
                    await stop_monitor.check_now(sym)
                    logger.info(f"ENTRY {sym} size={size:.4f} price={price}")
                    break
            await asyncio.sleep(15 if has_pos else 25)
        except Exception as e:
            logger.error(f"Loop error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
