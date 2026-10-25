from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
import uuid

@dataclass
class Position:
    id: str
    symbol: str
    direction: str
    size: float
    entry_price: float
    entry_time: datetime
    stop_distance: float
    stop_price: float
    highest_favorable: float = 0.0
    entry_quote_age: float = 0.0
    fees_paid: float = 0.0

@dataclass
class PaperState:
    equity: float
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    daily_pnl: float = 0.0
    total_trades: int = 0
    wins: int = 0
    total_fees: float = 0.0

class PaperEngine:
    def __init__(self, initial_equity: float = 10000.0, fee_rate: float = 0.0008):
        self.state = PaperState(equity=initial_equity, cash=initial_equity)
        self.fee_rate = fee_rate

    def open_position(self, symbol: str, direction: str, size: float, price: float,
                      stop_distance: float, quote_age: float = 0.0) -> Optional[str]:
        if size <= 0 or price <= 0:
            return None
        notional = size * price
        fee = notional * (self.fee_rate / 2)
        if notional + fee > self.state.cash:
            return None
        pos_id = str(uuid.uuid4())[:8]
        stop_price = price - stop_distance if direction == "long" else price + stop_distance
        pos = Position(
            id=pos_id, symbol=symbol, direction=direction, size=size,
            entry_price=price, entry_time=datetime.utcnow(),
            stop_distance=stop_distance, stop_price=stop_price,
            highest_favorable=price, entry_quote_age=quote_age, fees_paid=fee
        )
        self.state.positions[pos_id] = pos
        self.state.cash -= (notional + fee)
        self.state.total_fees += fee
        return pos_id

    def close_position(self, pos_id: str, exit_price: float, reason: str = "") -> Optional[dict]:
        pos = self.state.positions.get(pos_id)
        if not pos:
            return None
        notional_exit = pos.size * exit_price
        fee_exit = notional_exit * (self.fee_rate / 2)
        if pos.direction == "long":
            gross_pnl = (exit_price - pos.entry_price) * pos.size
            cash_change = notional_exit - fee_exit
        else:
            gross_pnl = (pos.entry_price - exit_price) * pos.size
            cash_change = notional_exit - fee_exit
        net_pnl = gross_pnl - pos.fees_paid - fee_exit
        self.state.equity += net_pnl
        self.state.cash += cash_change
        self.state.daily_pnl += net_pnl
        self.state.total_trades += 1
        self.state.total_fees += fee_exit
        if net_pnl > 0:
            self.state.wins += 1
        result = {
            "pos_id": pos_id, "symbol": pos.symbol, "direction": pos.direction,
            "entry_price": pos.entry_price, "exit_price": exit_price,
            "size": pos.size, "gross_pnl": gross_pnl, "net_pnl": net_pnl,
            "fees": pos.fees_paid + fee_exit, "entry_time": pos.entry_time,
            "exit_time": datetime.utcnow(), "reason": reason,
            "stop_price": pos.stop_price, "entry_quote_age": pos.entry_quote_age
        }
        del self.state.positions[pos_id]
        return result

    def get_open_risk(self) -> float:
        return sum(p.size * p.stop_distance for p in self.state.positions.values())

    def update_favorable(self, pos_id: str, current_price: float):
        pos = self.state.positions.get(pos_id)
        if not pos:
            return
        if pos.direction == "long":
            pos.highest_favorable = max(pos.highest_favorable, current_price)
        else:
            pos.highest_favorable = min(pos.highest_favorable or current_price, current_price)

    def get_positions_snapshot(self) -> list:
        return [
            {
                "id": p.id, "symbol": p.symbol, "direction": p.direction,
                "size": p.size, "entry_price": p.entry_price,
                "entry_time": p.entry_time.isoformat(), "stop_price": p.stop_price,
                "stop_distance": p.stop_distance, "highest_favorable": p.highest_favorable
            }
            for p in self.state.positions.values()
        ]
