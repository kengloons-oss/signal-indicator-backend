from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.strategy.models import (
    Signal,
    SignalMode,
    TradeDirection,
)


# ============================================================
# STRATEGY CONFIG
# ============================================================

@dataclass
class SignalConfig:

    # Signal mode
    signal_mode: SignalMode = SignalMode.BOTH

    # RSI
    rsi_mid_level: float = 50.0

    # BOTH confirmation
    confirmation_window: int = 5

    # Trend filter
    use_trend_filter: bool = True


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def is_crossover(
    current_value: float,
    current_reference: float,
    previous_value: float,
    previous_reference: float,
) -> bool:
    """
    Equivalent to TradingView:

        ta.crossover(value, reference)

    Current:
        value > reference

    Previous:
        value <= reference
    """

    return (
        current_value > current_reference
        and previous_value <= previous_reference
    )


def is_crossunder(
    current_value: float,
    current_reference: float,
    previous_value: float,
    previous_reference: float,
) -> bool:
    """
    Equivalent to TradingView:

        ta.crossunder(value, reference)

    Current:
        value < reference

    Previous:
        value >= reference
    """

    return (
        current_value < current_reference
        and previous_value >= previous_reference
    )


# ============================================================
# SIGNAL ENGINE
# ============================================================

class SignalEngine:

    def __init__(
        self,
        config: SignalConfig,
    ):
        self.config = config

        # Equivalent to Pine Script:
        #
        # var int lastRsiBullBar = na
        # var int lastRsiBearBar = na
        # var int lastMacdBullBar = na
        # var int lastMacdBearBar = na

        self.last_rsi_bull_bar: Optional[int] = None
        self.last_rsi_bear_bar: Optional[int] = None

        self.last_macd_bull_bar: Optional[int] = None
        self.last_macd_bear_bar: Optional[int] = None

    # ========================================================
    # PROCESS ONE CANDLE
    # ========================================================

    def process_candle(
        self,
        bar_index: int,
        timestamp: int,
        close: float,
        rsi: float,
        macd: float,
        macd_signal: float,
        ema: float,
        previous_rsi: float,
        previous_macd: float,
        previous_macd_signal: float,
    ) -> Optional[Signal]:

        # Skip candle if indicators are not ready
        values = [
            rsi,
            macd,
            macd_signal,
            ema,
            previous_rsi,
            previous_macd,
            previous_macd_signal,
        ]

        if any(pd.isna(value) for value in values):
            return None

        # ====================================================
        # RSI CROSS
        # ====================================================

        rsi_bullish = is_crossover(
            current_value=rsi,
            current_reference=self.config.rsi_mid_level,
            previous_value=previous_rsi,
            previous_reference=self.config.rsi_mid_level,
        )

        rsi_bearish = is_crossunder(
            current_value=rsi,
            current_reference=self.config.rsi_mid_level,
            previous_value=previous_rsi,
            previous_reference=self.config.rsi_mid_level,
        )

        # ====================================================
        # MACD CROSS
        # ====================================================

        macd_bullish = is_crossover(
            current_value=macd,
            current_reference=macd_signal,
            previous_value=previous_macd,
            previous_reference=previous_macd_signal,
        )

        macd_bearish = is_crossunder(
            current_value=macd,
            current_reference=macd_signal,
            previous_value=previous_macd,
            previous_reference=previous_macd_signal,
        )

        # ====================================================
        # STORE EVENT BARS
        # Equivalent to TradingView
        # ====================================================

        if rsi_bullish:
            self.last_rsi_bull_bar = bar_index

        if rsi_bearish:
            self.last_rsi_bear_bar = bar_index

        if macd_bullish:
            self.last_macd_bull_bar = bar_index

        if macd_bearish:
            self.last_macd_bear_bar = bar_index

        # ====================================================
        # BOTH MODE CONFIRMATION
        # ====================================================

        both_bullish = (
            self.last_rsi_bull_bar is not None
            and self.last_macd_bull_bar is not None
            and abs(
                self.last_rsi_bull_bar
                - self.last_macd_bull_bar
            )
            <= self.config.confirmation_window
        )

        both_bearish = (
            self.last_rsi_bear_bar is not None
            and self.last_macd_bear_bar is not None
            and abs(
                self.last_rsi_bear_bar
                - self.last_macd_bear_bar
            )
            <= self.config.confirmation_window
        )

        # ====================================================
        # RAW SIGNAL LOGIC
        # ====================================================

        raw_buy_signal = False
        raw_sell_signal = False

        if self.config.signal_mode == SignalMode.RSI_ONLY:

            raw_buy_signal = rsi_bullish
            raw_sell_signal = rsi_bearish

        elif self.config.signal_mode == SignalMode.MACD_ONLY:

            raw_buy_signal = macd_bullish
            raw_sell_signal = macd_bearish

        elif self.config.signal_mode == SignalMode.BOTH:

            raw_buy_signal = (
                both_bullish
                and (
                    rsi_bullish
                    or macd_bullish
                )
            )

            raw_sell_signal = (
                both_bearish
                and (
                    rsi_bearish
                    or macd_bearish
                )
            )

        # ====================================================
        # EMA TREND FILTER
        # ====================================================

        bullish_trend = close > ema
        bearish_trend = close < ema

        buy_trend_allowed = (
            not self.config.use_trend_filter
            or bullish_trend
        )

        sell_trend_allowed = (
            not self.config.use_trend_filter
            or bearish_trend
        )

        buy_signal = (
            raw_buy_signal
            and buy_trend_allowed
        )

        sell_signal = (
            raw_sell_signal
            and sell_trend_allowed
        )

        # ====================================================
        # RETURN SIGNAL
        # ====================================================

        if buy_signal:

            return Signal(
                direction=TradeDirection.LONG,
                timestamp=timestamp,
                price=close,
                rsi_value=rsi,
                macd_value=macd,
                macd_signal=macd_signal,
            )

        if sell_signal:

            return Signal(
                direction=TradeDirection.SHORT,
                timestamp=timestamp,
                price=close,
                rsi_value=rsi,
                macd_value=macd,
                macd_signal=macd_signal,
            )

        return None