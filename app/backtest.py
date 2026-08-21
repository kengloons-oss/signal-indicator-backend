from dataclasses import dataclass
from typing import Optional


# ============================================================
# BACKTEST TRADE RESULT
# ============================================================

@dataclass
class BacktestTrade:

    direction: str

    entry_timestamp: int
    entry_price: float

    exit_timestamp: Optional[int] = None
    exit_price: Optional[float] = None

    result: Optional[str] = None

    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False

    is_open: bool = True


# ============================================================
# BACKTEST RESULT
# ============================================================

@dataclass
class BacktestResult:

    total_trades: int

    wins: int
    losses: int

    open_trades: int

    tp1_hits: int
    tp2_hits: int
    tp3_hits: int

    win_rate: float


# ============================================================
# BACKTEST ENGINE
# ============================================================

class Backtester:

    def __init__(self):

        self.trades: list[BacktestTrade] = []

        self.active_trade: Optional[BacktestTrade] = None

    # ========================================================
    # PROCESS STRATEGY EVENTS
    # ========================================================

    def process_events(
        self,
        events: list[dict],
    ):

        for event in events:

            event_type = event["type"]

            # ====================================================
            # NEW SIGNAL
            # ====================================================

            if event_type == "SIGNAL":

                trade = BacktestTrade(

                    direction=event["direction"],

                    entry_timestamp=event["timestamp"],

                    entry_price=event["entry"],
                )

                self.trades.append(
                    trade
                )

                self.active_trade = trade

            # ====================================================
            # TP1
            # ====================================================

            elif event_type == "TP1":

                if self.active_trade:

                    self.active_trade.tp1_hit = True

            # ====================================================
            # TP2
            # ====================================================

            elif event_type == "TP2":

                if self.active_trade:

                    self.active_trade.tp2_hit = True

            # ====================================================
            # TP3 = WIN
            # ====================================================

            elif event_type == "TP3":

                if self.active_trade:

                    self.active_trade.tp3_hit = True

                    self.active_trade.result = "WIN"

                    self.active_trade.exit_timestamp = (
                        event["timestamp"]
                    )

                    self.active_trade.exit_price = (
                        event["tp3"]
                    )

                    self.active_trade.is_open = False

                    self.active_trade = None

            # ====================================================
            # SL = LOSS
            # ====================================================

            elif event_type == "SL":

                if self.active_trade:

                    self.active_trade.result = "LOSS"

                    self.active_trade.exit_timestamp = (
                        event["timestamp"]
                    )

                    self.active_trade.exit_price = (
                        event["stop_loss"]
                    )

                    self.active_trade.is_open = False

                    self.active_trade = None

        return self.calculate_result()

    # ========================================================
    # CALCULATE BACKTEST RESULT
    # ========================================================

    def calculate_result(
        self,
    ) -> BacktestResult:

        total_trades = len(
            self.trades
        )

        wins = sum(
            1
            for trade in self.trades
            if trade.result == "WIN"
        )

        losses = sum(
            1
            for trade in self.trades
            if trade.result == "LOSS"
        )

        open_trades = sum(
            1
            for trade in self.trades
            if trade.is_open
        )

        tp1_hits = sum(
            1
            for trade in self.trades
            if trade.tp1_hit
        )

        tp2_hits = sum(
            1
            for trade in self.trades
            if trade.tp2_hit
        )

        tp3_hits = sum(
            1
            for trade in self.trades
            if trade.tp3_hit
        )

        closed_trades = (
            wins
            + losses
        )

        if closed_trades > 0:

            win_rate = (
                wins
                / closed_trades
                * 100
            )

        else:

            win_rate = 0.0

        return BacktestResult(

            total_trades=total_trades,

            wins=wins,

            losses=losses,

            open_trades=open_trades,

            tp1_hits=tp1_hits,

            tp2_hits=tp2_hits,

            tp3_hits=tp3_hits,

            win_rate=win_rate,
        )


# ============================================================
# PRINT BACKTEST RESULT
# ============================================================

def print_backtest_result(
    result: BacktestResult,
):

    print()

    print(
        "=" * 70
    )

    print(
        "BACKTEST RESULT"
    )

    print(
        "=" * 70
    )

    print()

    print(
        f"Total Trades: {result.total_trades}"
    )

    print(
        f"Wins:         {result.wins}"
    )

    print(
        f"Losses:       {result.losses}"
    )

    print(
        f"Open Trades:  {result.open_trades}"
    )

    print()

    print(
        "-" * 70
    )

    print(
        "TARGET STATISTICS"
    )

    print(
        "-" * 70
    )

    print()

    print(
        f"TP1 Hit:      {result.tp1_hits}"
    )

    print(
        f"TP2 Hit:      {result.tp2_hits}"
    )

    print(
        f"TP3 Hit:      {result.tp3_hits}"
    )

    print()

    print(
        "-" * 70
    )

    print(
        f"WIN RATE:     {result.win_rate:.2f}%"
    )

    print(
        "=" * 70
    )

    print()