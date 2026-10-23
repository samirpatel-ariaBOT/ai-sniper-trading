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
        pos = Position(pid, symbol, direction, size, price, datetime.utcnow(), stop_distance)
        self.state.positions[pid] = pos
        self.state.cash -= size * price
        return pid

    def close_position(self, pos_id, price):
        if pos_id not in self.state.positions:
            return None
        pos = self.state.positions.pop(pos_id)
        if pos.direction == "long":
            pnl = (price - pos.entry_price) * pos.size
        else:
            pnl = (pos.entry_price - price) * pos.size

        # Fee deduction (0.04% round-trip estimate)
        notional = pos.size * pos.entry_price
        fee = notional * 0.0004
        pnl -= fee

        self.state.cash += pos.size * price
        self.state.equity += pnl
        return pnl

    def update_favorable(self, pos_id, price):
        if pos_id in self.state.positions:
            pos = self.state.positions[pos_id]
            if pos.direction == "long":
                fav = price - pos.entry_price
            else:
                fav = pos.entry_price - price
            if fav > pos.highest_favorable:
                pos.highest_favorable = fav

