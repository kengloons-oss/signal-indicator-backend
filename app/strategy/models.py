from dataclasses import dataclass
from enum import Enum
from typing import Optional


#Signal Mode Enum
class SignalMode(str, Enum):
    "Enumeration of Signal Modes"
    RSI_ONLY = "RSI_ONLY"
    MACD_ONLY = "MACD_ONLY"
    BOTH = "BOTH"

#Trade Direction Enum
class TradeDirection(str, Enum):
    "Enumeration of Trade Directions"
    LONG = "LONG"
    SHORT = "SHORT"

#Trade State
class TradeState(str, Enum):
    "Enumeration of Trade States"
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"

#Signal 
@dataclass
class Signal:
    "Signal class representing a trading signal"
    direction: TradeDirection
    timestamp: int
    price: float

    rsi_value: Optional[float] = None
    macd_value: Optional[float] = None
    macd_signal: Optional[float] = None

#Trade
@dataclass
class Trade:
    "Trade class representing a trade"
    direction: TradeDirection

    entry_price: float
    stop_loss: float

    take_profit_1: float
    take_profit_2: float
    take_profit_3: float

    entry_bar_index: int

    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False

    is_active: bool = True



