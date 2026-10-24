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
    highest_favorable: float = 0.0


@dataclass
class PaperState:
    equity: float
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)


class PaperEngine:
    def __init__(self, initial_equity: float = 10000.0):
        self.state = PaperState(equity=initial_equity, cash=initial_equity)

    def open_position(self, symbol, direction, size, price, stop_distance):
        pid = str(uuid.uuid4())[:8]
        pos = Position(
            id=pid,
            symbol=symbol,
            direction=direction,
            size=size,
            entry_price=price,
            entry_time=datetime.utcnow(),
            stop_distance=stop_distance
        )
        self.state.positions[pid] = pos
        notional = size * price
        self.state.cash -= notional
        return pid

    def update_favorable(self, pid, price):
        pos = self.state.positions.get(pid)
        if not pos:
            return
        if pos.direction == "long":
            fav = price - pos.entry_price
        else:
            fav = pos.entry_price - price
        if fav > pos.highest_favorable:
            pos.highest_favorable = fav

    def close_position(self, pid, exit_price, reason="exit"):
        pos = self.state.positions.pop(pid, None)
        if not pos:
            return None
        if pos.direction == "long":
            pnl = (exit_price - pos.entry_price) * pos.size
        else:
            pnl = (pos.entry_price - exit_price) * pos.size
        fee = pos.size * pos.entry_price * 0.0004
        net_pnl = pnl - fee
        notional = pos.size * pos.entry_price
        self.state.cash += notional + net_pnl
        self.state.equity = self.state.cash
        return net_pnl
