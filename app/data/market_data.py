import ccxt
import pandas as pd
import time


# ============================================================
# PREPARE OHLCV DATAFRAME
# ============================================================

def prepare_ohlcv_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    # Make sure timestamp is integer
    df["timestamp"] = df["timestamp"].astype("int64")

    # Sort by timestamp
    df = df.sort_values(
        "timestamp"
    )

    # Remove duplicate candles
    df = df.drop_duplicates(
        subset=["timestamp"]
    )

    # Reset index
    df = df.reset_index(
        drop=True
    )

    return df


# ============================================================
# TIMEFRAME TO MILLISECONDS
# ============================================================

def timeframe_to_milliseconds(
    timeframe: str,
) -> int:

    timeframe_map = {
        "1m": 60 * 1000,
        "3m": 3 * 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "30m": 30 * 60 * 1000,

        "1h": 60 * 60 * 1000,
        "2h": 2 * 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,

        "1d": 24 * 60 * 60 * 1000,
    }

    if timeframe not in timeframe_map:

        raise ValueError(
            f"Unsupported timeframe: {timeframe}"
        )

    return timeframe_map[
        timeframe
    ]


# ============================================================
# FETCH HISTORICAL OHLCV
# ============================================================

def fetch_historical_ohlcv(
    symbol: str,
    timeframe: str,
    total_candles: int = 5000,
) -> pd.DataFrame:

    """
    Fetch historical OHLCV data from MEXC.

    We calculate a starting timestamp in the past,
    then fetch forward in multiple batches.
    """

    exchange = ccxt.mexc(
        {
            "enableRateLimit": True,
        }
    )

    # ========================================================
    # TIMEFRAME
    # ========================================================

    timeframe_ms = (
        timeframe_to_milliseconds(
            timeframe
        )
    )

    # ========================================================
    # CALCULATE START TIME
    # ========================================================

    now = exchange.milliseconds()

    # Add extra candles for safety
    buffer_candles = 100

    start_time = (
        now
        - (
            total_candles
            + buffer_candles
        )
        * timeframe_ms
    )

    since = start_time

    # ========================================================
    # CONFIG
    # ========================================================

    batch_limit = 500

    all_ohlcv = []

    print(
        f"Fetching approximately "
        f"{total_candles} historical candles..."
    )

    print(
        f"Starting from: "
        f"{pd.to_datetime(start_time, unit='ms')}"
    )

    # ========================================================
    # FETCH LOOP
    # ========================================================

    while True:

        if len(all_ohlcv) >= total_candles:

            break

        try:

            ohlcv = exchange.fetch_ohlcv(

                symbol,

                timeframe=timeframe,

                since=since,

                limit=batch_limit,
            )

        except Exception as error:

            print(
                f"Error fetching data: {error}"
            )

            break

        # No data returned
        if not ohlcv:

            print(
                "No more historical candles available."
            )

            break

        # ====================================================
        # ADD DATA
        # ====================================================

        all_ohlcv.extend(
            ohlcv
        )

        # Remove duplicate timestamps
        unique_timestamps = {
            candle[0]
            for candle in all_ohlcv
        }

        candle_count = len(
            unique_timestamps
        )

        print(
            f"Fetched: "
            f"{candle_count} candles"
        )

        # ====================================================
        # STOP IF ENOUGH
        # ====================================================

        if candle_count >= total_candles:

            break

        # ====================================================
        # MOVE TO NEXT BATCH
        # ====================================================

        last_timestamp = (
            ohlcv[-1][0]
        )

        next_since = (
            last_timestamp
            + timeframe_ms
        )

        # Safety check
        if next_since <= since:

            print(
                "Unable to move to next batch."
            )

            break

        since = next_since

        # ====================================================
        # RATE LIMIT
        # ====================================================

        time.sleep(
            exchange.rateLimit / 1000
        )

        # ====================================================
        # IF LESS THAN BATCH LIMIT
        # ====================================================

        if len(ohlcv) < batch_limit:

            print(
                "Reached latest available data."
            )

            break

    # ========================================================
    # CREATE DATAFRAME
    # ========================================================

    df = pd.DataFrame(

        all_ohlcv,

        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ],
    )

    # ========================================================
    # CLEAN DATA
    # ========================================================

    df = prepare_ohlcv_dataframe(
        df
    )

    # ========================================================
    # KEEP ONLY REQUESTED AMOUNT
    # ========================================================

    if len(df) > total_candles:

        df = df.tail(
            total_candles
        )

        df = df.reset_index(
            drop=True
        )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print()

    print(
        f"Final candle count: "
        f"{len(df)}"
    )

    if not df.empty:

        start_date = pd.to_datetime(
            df.iloc[0]["timestamp"],
            unit="ms",
        )

        end_date = pd.to_datetime(
            df.iloc[-1]["timestamp"],
            unit="ms",
        )

        print(
            f"Data range: "
            f"{start_date} "
            f"-> "
            f"{end_date}"
        )

    return df