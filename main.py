import asyncio
import time
import yaml
import sqlite3
from datetime import datetime
from loguru import logger

from agents.risk_agent import RiskAgent
from agents.exit_manager import ExitManager
from agents.decision_agent import DecisionAgent
from agents.orderbook_agent import OrderBookAgent
from agents.learning_agent import LearningAgent
from core.paper_engine import PaperEngine
from core.database import TradeDatabase
from core.data_feed import DataFeed
from core.scanner import TopMoversScanner
from core.telegram_reporter import TelegramReporter


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def get_today_pnl(db_path):
    try:
        conn = sqlite3.connect(db_path)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        cur = conn.cursor()
        cur.execute("SELECT SUM(pnl) FROM trades WHERE exit_time LIKE ?", (f"{today}%",))
        val = cur.fetchone()[0]
        conn.close()
        return val or 0.0
    except:
        return 0.0


def restore_equity(db_path, paper):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT SUM(pnl) FROM trades")
        total_pnl = cur.fetchone()[0] or 0
        paper.state.equity = 10000 + total_pnl
        paper.state.cash = paper.state.equity
        conn.close()
        logger.info(f"Restored equity from DB: ${paper.state.equity:.2f} (PnL ${total_pnl:.2f})")
        return total_pnl
    except Exception as e:
        logger.warning(f"Could not restore equity: {e}")
        return 0


async def main():
    config = load_config()
    risk = RiskAgent(config)
    exit_mgr = ExitManager(config)
    decision = DecisionAgent(config)
    orderbook = OrderBookAgent(config)
    learning = LearningAgent(config, config["database"]["path"])
    paper = PaperEngine(config["paper"]["initial_equity"])
    restore_equity(config["database"]["path"], paper)
    db = TradeDatabase(config["database"]["path"])
    data = DataFeed()
    scanner = TopMoversScanner(min_volume_usdt=500000, top_n=5)
    telegram = TelegramReporter()

    logger.info(f"Started | Equity: ${paper.state.equity:.2f}")
    telegram.send(f"AI Sniper started | Equity: ${paper.state.equity:.2f}")

    last_scan = 0
    symbols = []
    last_scores = {}

    while True:
        try:
            now = time.time()
            has_pos = len(paper.state.positions) > 0
            telegram.check_commands(config["database"]["path"])
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
                            learning.record_trade(last_scores.get(pos.symbol, {}), pnl > 0, pos.symbol, pnl)
                            risk.record_trade_result(paper.state.equity, pnl)
                            logger.info(f"EXIT {pos.symbol} {pos.direction} pnl={pnl:.2f} equity={paper.state.equity:.2f}")
                            telegram.send(f"EXIT {pos.symbol} {pos.direction} pnl={pnl:.2f}")

            if now - last_scan > 60 and not has_pos:
                symbols = scanner.get_trading_symbols()
                last_scan = now
                logger.info(f"Scan: {symbols[:5]}")

            if symbols and not has_pos:
                for sym in symbols[:2]:
                    ohlcv = data.fetch_ohlcv(sym, "5m", 30)
                    if not ohlcv or len(ohlcv) < 10:
                        continue
                    price = ohlcv[-1][4]
                    closes = [c[4] for c in ohlcv]
                    opens = [c[1] for c in ohlcv]
                    volumes = [c[5] for c in ohlcv]
                    last_3_red = sum(1 for i in range(-3, 0) if closes[i] < opens[i])
                    last_3_green = sum(1 for i in range(-3, 0) if closes[i] > opens[i])
                    roc = (closes[-1] - closes[-6]) / closes[-6] if closes[-6] else 0
                    avg_vol = sum(volumes[-10:]) / 10
                    recent_vol = volumes[-1]

                    direction = None
                    if roc < -0.008 and recent_vol > avg_vol * 1.1:
                        direction = "short"
                    elif roc > 0.008 and recent_vol > avg_vol * 1.1:
                        direction = "long"
                    if not direction:
                        continue

                    candle_bias = "red" if last_3_red >= 2 else "green" if last_3_green >= 2 else "mixed"
                    vol_spike = 1 if recent_vol > avg_vol * 1.2 else 0
                    last_scores[sym] = {
                        "momentum": round(roc * 10, 3),
                        "bias": candle_bias,
                        "vol_spike": vol_spike
                    }
                    oracle_sig = {
                        "side": direction,
                        "confidence": min(0.95, 0.55 + abs(roc) * 8 + (0.12 if vol_spike else 0)),
                        "raw_score": roc,
                        "momentum": last_scores[sym]["momentum"],
                        "bias": candle_bias
                    }
                    daily_pnl = get_today_pnl(config["database"]["path"])
                    r = risk.check(paper.state.equity, daily_pnl, len(paper.state.positions))
                    ok = r[0] if isinstance(r, (list, tuple)) else True
                    adj = learning.get_adjustments(sym)
                    conf = oracle_sig["confidence"] + adj.get("momentum", 0)
                    if ok and conf >= 0.62:
                        size = risk.position_size(paper.state.equity, price, price * 0.008)
                        if size > 0:
                            paper.open_position(sym, direction, size, price, price * 0.008)
                            logger.info(f"ENTRY {sym} {direction} size={size:.2f} conf={conf:.2f}")
                            telegram.send(f"ENTRY {sym} {direction} size={size:.2f} price={price}")
                            break

            await asyncio.sleep(2 if has_pos else 8)
        except Exception as e:
            logger.error(f"Error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
