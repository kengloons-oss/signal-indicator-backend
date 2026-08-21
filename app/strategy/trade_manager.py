from dataclasses import dataclass
from typing import Optional

from app.strategy.models import (
    Signal,
    Trade,
    TradeDirection,
)


# ============================================================
# TRADE MANAGER CONFIG
# ============================================================

@dataclass
class TradeManagerConfig:

    # ATR Stop Loss
    atr_multiplier: float = 1.5

    # Risk Reward
    tp1_rr: float = 1.0
    tp2_rr: float = 2.0
    tp3_rr: float = 3.0


# ============================================================
# TRADE RESULT
# ============================================================

@dataclass
class TradeEvent:

    event_type: str
    trade: Trade
    bar_index: int
    timestamp: int


# ============================================================
# TRADE MANAGER
# ============================================================

class TradeManager:

    def __init__(
        self,
        config: TradeManagerConfig,
    ):
        self.config = config

        self.active_trade: Optional[Trade] = None

    # ========================================================
    # CREATE TRADE FROM SIGNAL
    # ========================================================

    def create_trade(
        self,
        signal: Signal,
        atr: float,
        bar_index: int,
    ) -> Trade:

        entry_price = signal.price

        # ====================================================
        # LONG
        # ====================================================

        if signal.direction == TradeDirection.LONG:

            stop_loss = (
                entry_price
                - atr * self.config.atr_multiplier
            )

            risk = (
                entry_price
                - stop_loss
            )

            take_profit_1 = (
                entry_price
                + risk * self.config.tp1_rr
            )

            take_profit_2 = (
                entry_price
                + risk * self.config.tp2_rr
            )

            take_profit_3 = (
                entry_price
                + risk * self.config.tp3_rr
            )

        # ====================================================
        # SHORT
        # ====================================================

        else:

            stop_loss = (
                entry_price
                + atr * self.config.atr_multiplier
            )

            risk = (
                stop_loss
                - entry_price
            )

            take_profit_1 = (
                entry_price
                - risk * self.config.tp1_rr
            )

            take_profit_2 = (
                entry_price
                - risk * self.config.tp2_rr
            )

            take_profit_3 = (
                entry_price
                - risk * self.config.tp3_rr
            )

        trade = Trade(
            direction=signal.direction,

            entry_price=entry_price,
            stop_loss=stop_loss,

            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            take_profit_3=take_profit_3,

            entry_bar_index=bar_index,
        )

        self.active_trade = trade

        return trade

    # ========================================================
    # PROCESS ACTIVE TRADE
    # ========================================================

    def process_candle(
        self,
        high: float,
        low: float,
        bar_index: int,
        timestamp: int,
    ) -> list[TradeEvent]:

        events = []

        if self.active_trade is None:
            return events

        trade = self.active_trade

        # ====================================================
        # IMPORTANT:
        # SIGNAL CANDLE DOES NOT CHECK TP / SL
        # ====================================================

        if bar_index <= trade.entry_bar_index:
            return events

        # ====================================================
        # LONG TRADE
        # ====================================================

        if trade.direction == TradeDirection.LONG:

            # Conservative rule:
            # SL has priority if SL and TP are
            # both touched in same candle.

            if low <= trade.stop_loss:

                events.append(
                    TradeEvent(
                        event_type="SL",
                        trade=trade,
                        bar_index=bar_index,
                        timestamp=timestamp,
                    )
                )

                trade.is_active = False
                self.active_trade = None

                return events

            # TP1
            if (
                not trade.tp1_hit
                and high >= trade.take_profit_1
            ):

                trade.tp1_hit = True

                events.append(
                    TradeEvent(
                        event_type="TP1",
                        trade=trade,
                        bar_index=bar_index,
                        timestamp=timestamp,
                    )
                )

            # TP2
            if (
                not trade.tp2_hit
                and high >= trade.take_profit_2
            ):

                trade.tp2_hit = True

                events.append(
                    TradeEvent(
                        event_type="TP2",
                        trade=trade,
                        bar_index=bar_index,
                        timestamp=timestamp,
                    )
                )

            # TP3
            if (
                not trade.tp3_hit
                and high >= trade.take_profit_3
            ):

                trade.tp3_hit = True

                events.append(
                    TradeEvent(
                        event_type="TP3",
                        trade=trade,
                        bar_index=bar_index,
                        timestamp=timestamp,
                    )
                )

                trade.is_active = False
                self.active_trade = None

        # ====================================================
        # SHORT TRADE
        # ====================================================

        elif trade.direction == TradeDirection.SHORT:

            # Conservative rule:
            # SL has priority if SL and TP are
            # both touched in same candle.

            if high >= trade.stop_loss:

                events.append(
                    TradeEvent(
                        event_type="SL",
                        trade=trade,
                        bar_index=bar_index,
                        timestamp=timestamp,
                    )
                )

                trade.is_active = False
                self.active_trade = None

                return events

            # TP1
            if (
                not trade.tp1_hit
                and low <= trade.take_profit_1
            ):

                trade.tp1_hit = True

                events.append(
                    TradeEvent(
                        event_type="TP1",
                        trade=trade,
                        bar_index=bar_index,
                        timestamp=timestamp,
                    )
                )

            # TP2
            if (
                not trade.tp2_hit
                and low <= trade.take_profit_2
            ):

                trade.tp2_hit = True

                events.append(
                    TradeEvent(
                        event_type="TP2",
                        trade=trade,
                        bar_index=bar_index,
                        timestamp=timestamp,
                    )
                )

            # TP3
            if (
                not trade.tp3_hit
                and low <= trade.take_profit_3
            ):

                trade.tp3_hit = True

                events.append(
                    TradeEvent(
                        event_type="TP3",
                        trade=trade,
                        bar_index=bar_index,
                        timestamp=timestamp,
                    )
                )

                trade.is_active = False
                self.active_trade = None

        return events