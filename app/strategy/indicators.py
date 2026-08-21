from typing import Tuple

import pandas as pd


# ============================================================
# RSI
# TradingView equivalent:
# ta.rsi(close, length)
# ============================================================

def calculate_rsi(
    close: pd.Series,
    length: int = 14,
) -> pd.Series:
    """
    Calculate RSI using Wilder's smoothing method.

    Intended to match TradingView:
        ta.rsi(close, length)
    """

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / length,
        adjust=False,
        min_periods=length,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / length,
        adjust=False,
        min_periods=length,
    ).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi


# ============================================================
# EMA
# TradingView equivalent:
# ta.ema(source, length)
# ============================================================

def calculate_ema(
    source: pd.Series,
    length: int,
) -> pd.Series:
    """
    Calculate Exponential Moving Average.

    Intended to match TradingView:
        ta.ema(source, length)
    """

    return source.ewm(
        span=length,
        adjust=False,
        min_periods=length,
    ).mean()


# ============================================================
# MACD
# TradingView equivalent:
# ta.macd(close, fast, slow, signal)
# ============================================================

def calculate_macd(
    close: pd.Series,
    fast_length: int = 12,
    slow_length: int = 26,
    signal_length: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD.

    Returns:
        macd_line
        signal_line
        histogram
    """

    fast_ema = calculate_ema(
        close,
        fast_length,
    )

    slow_ema = calculate_ema(
        close,
        slow_length,
    )

    macd_line = fast_ema - slow_ema

    signal_line = macd_line.ewm(
        span=signal_length,
        adjust=False,
        min_periods=signal_length,
    ).mean()

    histogram = (
        macd_line -
        signal_line
    )

    return (
        macd_line,
        signal_line,
        histogram,
    )


# ============================================================
# TRUE RANGE
# TradingView equivalent:
# ta.tr(true)
# ============================================================

def calculate_true_range(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> pd.Series:
    """
    Calculate True Range.
    """

    previous_close = close.shift(1)

    high_low = high - low

    high_previous_close = (
        high - previous_close
    ).abs()

    low_previous_close = (
        low - previous_close
    ).abs()

    true_range = pd.concat(
        [
            high_low,
            high_previous_close,
            low_previous_close,
        ],
        axis=1,
    ).max(axis=1)

    return true_range


# ============================================================
# ATR
# TradingView equivalent:
# ta.atr(length)
# ============================================================

def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    length: int = 14,
) -> pd.Series:
    """
    Calculate ATR using Wilder's smoothing method.

    Intended to match TradingView:
        ta.atr(length)
    """

    true_range = calculate_true_range(
        high,
        low,
        close,
    )

    atr = true_range.ewm(
        alpha=1 / length,
        adjust=False,
        min_periods=length,
    ).mean()

    return atr