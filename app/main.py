import os
import time
import threading

import pandas as pd
from flask import Flask, jsonify

from app.data.market_data import (
    fetch_historical_ohlcv,
)

from app.strategy.indicators import (
    calculate_rsi,
    calculate_ema,
    calculate_macd,
    calculate_atr,
)

from app.strategy.models import SignalMode

from app.strategy.signal_engine import (
    SignalConfig,
    SignalEngine,
)

from app.strategy.trade_manager import (
    TradeManagerConfig,
    TradeManager,
)

from app.backtest import (
    Backtester,
)

from app.services.telegram import (
    send_message,
)


# ============================================================
# WEB SERVICE / RENDER
# ============================================================

app = Flask(__name__)

bot_status = {
    "status": "starting",
    "symbol": None,
    "timeframe": None,
    "signal_mode": None,
    "last_candle": None,
    "last_error": None,
}


@app.route("/")
def home():

    return jsonify(
        {
            "service": "RSI + MACD Signal Bot",
            "status": bot_status["status"],
            "symbol": bot_status["symbol"],
            "timeframe": bot_status["timeframe"],
            "signal_mode": bot_status["signal_mode"],
            "last_candle": bot_status["last_candle"],
            "last_error": bot_status["last_error"],
        }
    )


@app.route("/health")
def health():

    return jsonify(
        {
            "status": bot_status["status"],
            "service": "healthy",
        }
    ), 200


# ============================================================
# CONFIG
# ============================================================

# Options:
# "BACKTEST"
# "LIVE"

RUN_MODE = "LIVE"


# ============================================================
# MARKET CONFIG
# ============================================================

SYMBOL = "XAU/USDT:USDT"

TIMEFRAME = "1m"


# ============================================================
# BACKTEST CONFIG
# ============================================================

BACKTEST_LIMIT = 5000


# ============================================================
# LIVE CONFIG
# ============================================================

LIVE_CANDLE_LIMIT = 300

CHECK_INTERVAL = 30


# ============================================================
# LIVE SIGNAL MODE
# ============================================================

LIVE_SIGNAL_MODE = SignalMode.BOTH


# ============================================================
# FETCH DATA
# ============================================================

def fetch_data(
    total_candles,
):

    return fetch_historical_ohlcv(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        total_candles=total_candles,
    )


# ============================================================
# ADD INDICATORS
# ============================================================

def add_indicators(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    df["rsi"] = calculate_rsi(
        df["close"],
        length=14,
    )

    df["ema_200"] = calculate_ema(
        df["close"],
        length=200,
    )

    (
        df["macd"],
        df["macd_signal"],
        df["macd_histogram"],
    ) = calculate_macd(
        df["close"],
        fast_length=12,
        slow_length=26,
        signal_length=9,
    )

    df["atr"] = calculate_atr(
        df["high"],
        df["low"],
        df["close"],
        length=14,
    )

    return df


# ============================================================
# CREATE SIGNAL ENGINE
# ============================================================

def create_signal_engine(
    signal_mode,
):

    config = SignalConfig(

        signal_mode=signal_mode,

        rsi_mid_level=50.0,

        confirmation_window=5,

        use_trend_filter=True,
    )

    return SignalEngine(
        config=config,
    )


# ============================================================
# CREATE TRADE MANAGER
# ============================================================

def create_trade_manager():

    config = TradeManagerConfig(

        atr_multiplier=1.5,

        tp1_rr=1.0,

        tp2_rr=2.0,

        tp3_rr=3.0,
    )

    return TradeManager(
        config=config,
    )


# ============================================================
# TELEGRAM - NEW SIGNAL
# ============================================================

def format_telegram_signal(
    signal,
    trade,
    candle_time,
):

    emoji = (
        "🟢"
        if signal.direction.value == "LONG"
        else "🔴"
    )

    message = (
        f"🚀 <b>RSI + MACD SIGNAL</b>\n\n"

        f"{emoji} <b>{signal.direction.value} SIGNAL</b>\n\n"

        f"📊 <b>Symbol:</b> {SYMBOL}\n"
        f"⏱ <b>Timeframe:</b> {TIMEFRAME}\n"
        f"⚙️ <b>Mode:</b> {LIVE_SIGNAL_MODE.value}\n\n"

        f"🕒 <b>Time:</b>\n"
        f"{candle_time}\n\n"

        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"💰 <b>Entry:</b> {trade.entry_price:.4f}\n"
        f"🛑 <b>SL:</b> {trade.stop_loss:.4f}\n\n"

        f"🎯 <b>TP1:</b> {trade.take_profit_1:.4f}\n"
        f"🎯 <b>TP2:</b> {trade.take_profit_2:.4f}\n"
        f"🎯 <b>TP3:</b> {trade.take_profit_3:.4f}\n\n"

        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"📈 <b>RSI:</b> {signal.rsi_value:.2f}\n"

        f"📊 <b>MACD:</b> "
        f"{signal.macd_value:.6f}\n"

        f"📉 <b>MACD Signal:</b> "
        f"{signal.macd_signal:.6f}\n\n"

        f"🤖 <b>RSI + MACD SIGNAL BOT</b>"
    )

    return message


# ============================================================
# TELEGRAM - TRADE EVENT
# ============================================================

def format_telegram_trade_event(
    event,
):

    direction = event.trade.direction.value

    emoji = (
        "🟢"
        if direction == "LONG"
        else "🔴"
    )

    event_type = str(
        event.event_type
    )

    event_time = pd.to_datetime(
        event.timestamp,
        unit="ms",
    )

    # --------------------------------------------------------
    # TP1
    # --------------------------------------------------------

    if event_type == "TP1_HIT":

        return (
            f"🎯 <b>TP1 HIT!</b>\n\n"

            f"{emoji} <b>{direction}</b>\n\n"

            f"📊 <b>Symbol:</b> {SYMBOL}\n"
            f"⏱ <b>Timeframe:</b> {TIMEFRAME}\n"
            f"🕒 <b>Time:</b> {event_time}\n\n"

            f"💰 <b>Entry:</b> "
            f"{event.trade.entry_price:.4f}\n"

            f"🎯 <b>TP1:</b> "
            f"{event.trade.take_profit_1:.4f}\n\n"

            f"➡️ Next Target: <b>TP2</b>"
        )

    # --------------------------------------------------------
    # TP2
    # --------------------------------------------------------

    if event_type == "TP2_HIT":

        return (
            f"🎯🎯 <b>TP2 HIT!</b>\n\n"

            f"{emoji} <b>{direction}</b>\n\n"

            f"📊 <b>Symbol:</b> {SYMBOL}\n"
            f"⏱ <b>Timeframe:</b> {TIMEFRAME}\n"
            f"🕒 <b>Time:</b> {event_time}\n\n"

            f"💰 <b>Entry:</b> "
            f"{event.trade.entry_price:.4f}\n"

            f"🎯 <b>TP2:</b> "
            f"{event.trade.take_profit_2:.4f}\n\n"

            f"➡️ Final Target: <b>TP3</b>"
        )

    # --------------------------------------------------------
    # TP3
    # --------------------------------------------------------

    if event_type == "TP3_HIT":

        return (
            f"🏆 <b>TP3 HIT!</b>\n\n"

            f"{emoji} <b>{direction}</b>\n\n"

            f"📊 <b>Symbol:</b> {SYMBOL}\n"
            f"⏱ <b>Timeframe:</b> {TIMEFRAME}\n"
            f"🕒 <b>Time:</b> {event_time}\n\n"

            f"💰 <b>Entry:</b> "
            f"{event.trade.entry_price:.4f}\n"

            f"🏆 <b>TP3:</b> "
            f"{event.trade.take_profit_3:.4f}\n\n"

            f"✅ <b>TRADE COMPLETED</b>"
        )

    # --------------------------------------------------------
    # SL
    # --------------------------------------------------------

    if event_type == "SL_HIT":

        return (
            f"🛑 <b>STOP LOSS HIT</b>\n\n"

            f"{emoji} <b>{direction}</b>\n\n"

            f"📊 <b>Symbol:</b> {SYMBOL}\n"
            f"⏱ <b>Timeframe:</b> {TIMEFRAME}\n"
            f"🕒 <b>Time:</b> {event_time}\n\n"

            f"💰 <b>Entry:</b> "
            f"{event.trade.entry_price:.4f}\n"

            f"🛑 <b>SL:</b> "
            f"{event.trade.stop_loss:.4f}\n\n"

            f"❌ <b>TRADE CLOSED</b>"
        )

    return None


# ============================================================
# RUN STRATEGY
# ============================================================

def run_strategy(
    df: pd.DataFrame,
    signal_mode: SignalMode,
):

    signal_engine = create_signal_engine(
        signal_mode
    )

    trade_manager = create_trade_manager()

    strategy_events = []

    for i in range(
        1,
        len(df),
    ):

        current = df.iloc[i]

        previous = df.iloc[i - 1]

        timestamp = int(
            current["timestamp"]
        )

        trade_events = trade_manager.process_candle(

            high=float(
                current["high"]
            ),

            low=float(
                current["low"]
            ),

            bar_index=i,

            timestamp=timestamp,
        )

        for event in trade_events:

            strategy_events.append(
                {
                    "type": event.event_type,

                    "timestamp": event.timestamp,

                    "bar_index": event.bar_index,

                    "direction": event.trade.direction.value,

                    "entry": event.trade.entry_price,

                    "stop_loss": event.trade.stop_loss,

                    "tp1": event.trade.take_profit_1,

                    "tp2": event.trade.take_profit_2,

                    "tp3": event.trade.take_profit_3,
                }
            )

        if trade_manager.active_trade is not None:

            continue

        signal = signal_engine.process_candle(

            bar_index=i,

            timestamp=timestamp,

            close=float(
                current["close"]
            ),

            rsi=float(
                current["rsi"]
            ),

            previous_rsi=float(
                previous["rsi"]
            ),

            macd=float(
                current["macd"]
            ),

            macd_signal=float(
                current["macd_signal"]
            ),

            previous_macd=float(
                previous["macd"]
            ),

            previous_macd_signal=float(
                previous["macd_signal"]
            ),

            ema=float(
                current["ema_200"]
            ),
        )

        if signal:

            atr = float(
                current["atr"]
            )

            if pd.isna(atr):

                continue

            trade = trade_manager.create_trade(

                signal=signal,

                atr=atr,

                bar_index=i,
            )

            strategy_events.append(
                {
                    "type": "SIGNAL",

                    "timestamp": timestamp,

                    "bar_index": i,

                    "direction": signal.direction.value,

                    "entry": trade.entry_price,

                    "stop_loss": trade.stop_loss,

                    "tp1": trade.take_profit_1,

                    "tp2": trade.take_profit_2,

                    "tp3": trade.take_profit_3,

                    "rsi": signal.rsi_value,

                    "macd": signal.macd_value,

                    "macd_signal": signal.macd_signal,
                }
            )

    return strategy_events


# ============================================================
# RUN BACKTEST
# ============================================================

def run_backtest(
    df: pd.DataFrame,
    signal_mode: SignalMode,
):

    events = run_strategy(
        df=df,
        signal_mode=signal_mode,
    )

    backtester = Backtester()

    result = backtester.process_events(
        events
    )

    return result


# ============================================================
# GET RESULT VALUE
# ============================================================

def get_result_value(
    result,
    possible_names,
    default=0,
):

    for name in possible_names:

        if hasattr(
            result,
            name,
        ):

            return getattr(
                result,
                name,
            )

    return default


# ============================================================
# PRINT BACKTEST COMPARISON
# ============================================================

def print_comparison(
    results,
):

    print()

    print("=" * 115)

    print(
        "RSI + MACD STRATEGY COMPARISON"
    )

    print("=" * 115)

    print()

    print(
        f"{'MODE':<15}"
        f"{'TRADES':>10}"
        f"{'WINS':>8}"
        f"{'LOSSES':>10}"
        f"{'OPEN':>8}"
        f"{'TP1':>8}"
        f"{'TP2':>8}"
        f"{'TP3':>8}"
        f"{'WIN RATE':>14}"
    )

    print("-" * 115)

    for mode_name, result in results.items():

        total_trades = get_result_value(
            result,
            [
                "total_trades",
                "trades",
            ],
        )

        wins = get_result_value(
            result,
            [
                "wins",
                "winning_trades",
            ],
        )

        losses = get_result_value(
            result,
            [
                "losses",
                "losing_trades",
            ],
        )

        open_trades = get_result_value(
            result,
            [
                "open_trades",
            ],
        )

        tp1_hits = get_result_value(
            result,
            [
                "tp1_hits",
                "tp1_hit",
            ],
        )

        tp2_hits = get_result_value(
            result,
            [
                "tp2_hits",
                "tp2_hit",
            ],
        )

        tp3_hits = get_result_value(
            result,
            [
                "tp3_hits",
                "tp3_hit",
            ],
        )

        win_rate = get_result_value(
            result,
            [
                "win_rate",
            ],
        )

        print(
            f"{mode_name:<15}"
            f"{total_trades:>10}"
            f"{wins:>8}"
            f"{losses:>10}"
            f"{open_trades:>8}"
            f"{tp1_hits:>8}"
            f"{tp2_hits:>8}"
            f"{tp3_hits:>8}"
            f"{win_rate:>13.2f}%"
        )

    print()

    print("=" * 115)

    print()


# ============================================================
# BACKTEST MODE
# ============================================================

def run_backtest_mode():

    print()

    print("=" * 70)

    print(
        "RSI + MACD BACKTEST"
    )

    print("=" * 70)

    print()

    print(
        f"Symbol: {SYMBOL}"
    )

    print(
        f"Timeframe: {TIMEFRAME}"
    )

    print(
        f"Candle Limit: {BACKTEST_LIMIT}"
    )

    print()

    print(
        "Fetching historical market data..."
    )

    df = fetch_data(
        BACKTEST_LIMIT
    )

    print()

    print(
        f"Fetched {len(df)} candles"
    )

    print()

    print(
        "Calculating indicators..."
    )

    df = add_indicators(
        df
    )

    modes = {

        "RSI_ONLY":
            SignalMode.RSI_ONLY,

        "MACD_ONLY":
            SignalMode.MACD_ONLY,

        "BOTH":
            SignalMode.BOTH,
    }

    results = {}

    for mode_name, signal_mode in modes.items():

        print()

        print(
            "-" * 70
        )

        print(
            f"Running Backtest: {mode_name}"
        )

        print(
            "-" * 70
        )

        result = run_backtest(

            df=df,

            signal_mode=signal_mode,
        )

        results[
            mode_name
        ] = result

    print_comparison(
        results
    )

    print(
        "All backtests completed."
    )


# ============================================================
# LIVE MODE
# ============================================================

def run_live_mode():

    print()

    print("=" * 70)

    print(
        "LIVE RSI + MACD SIGNAL MONITOR"
    )

    print("=" * 70)

    print()

    print(
        f"Symbol: {SYMBOL}"
    )

    print(
        f"Timeframe: {TIMEFRAME}"
    )

    print(
        f"Signal Mode: {LIVE_SIGNAL_MODE.value}"
    )

    print(
        f"Check Interval: {CHECK_INTERVAL} seconds"
    )

    print()

    # ========================================================
    # UPDATE WEB SERVICE STATUS
    # ========================================================

    bot_status["status"] = "running"

    bot_status["symbol"] = SYMBOL

    bot_status["timeframe"] = TIMEFRAME

    bot_status["signal_mode"] = LIVE_SIGNAL_MODE.value

    bot_status["last_error"] = None

    signal_engine = create_signal_engine(
        LIVE_SIGNAL_MODE
    )

    trade_manager = create_trade_manager()

    last_processed_timestamp = None

    # ========================================================
    # LIVE LOOP
    # ========================================================

    while True:

        try:

            print()

            print(
                "Checking market..."
            )

            df = fetch_data(
                LIVE_CANDLE_LIMIT
            )

            df = add_indicators(
                df
            )

            if len(df) < 3:

                print(
                    "Not enough candles."
                )

                time.sleep(
                    CHECK_INTERVAL
                )

                continue

            # ------------------------------------------------
            # Latest closed candle
            # ------------------------------------------------

            current = df.iloc[-2]

            timestamp = int(
                current["timestamp"]
            )

            candle_time = pd.to_datetime(
                timestamp,
                unit="ms",
            )

            print(
                f"Latest closed candle: "
                f"{candle_time}"
            )

            bot_status["last_candle"] = str(
                candle_time
            )

            bot_status["last_error"] = None

            # ------------------------------------------------
            # Prevent duplicate processing
            # ------------------------------------------------

            if timestamp == last_processed_timestamp:

                print(
                    "No new closed candle."
                )

                time.sleep(
                    CHECK_INTERVAL
                )

                continue

            previous = df.iloc[-3]

            bar_index = len(df) - 2

            # ------------------------------------------------
            # PROCESS ACTIVE TRADE
            # ------------------------------------------------

            trade_events = trade_manager.process_candle(

                high=float(
                    current["high"]
                ),

                low=float(
                    current["low"]
                ),

                bar_index=bar_index,

                timestamp=timestamp,
            )

            # ------------------------------------------------
            # PRINT + TELEGRAM TRADE EVENTS
            # ------------------------------------------------

            for event in trade_events:

                print()

                print(
                    "=" * 60
                )

                print(
                    f"TRADE EVENT: "
                    f"{event.event_type}"
                )

                print(
                    f"Time: "
                    f"{pd.to_datetime(event.timestamp, unit='ms')}"
                )

                print(
                    f"Direction: "
                    f"{event.trade.direction.value}"
                )

                print(
                    "=" * 60
                )

                # --------------------------------------------
                # FORMAT EVENT MESSAGE
                # --------------------------------------------

                telegram_event_message = (
                    format_telegram_trade_event(
                        event
                    )
                )

                # --------------------------------------------
                # SEND EVENT TO TELEGRAM
                # --------------------------------------------

                if telegram_event_message:

                    print()

                    print(
                        "Sending Telegram trade update..."
                    )

                    telegram_success = (
                        send_message(
                            telegram_event_message
                        )
                    )

                    if telegram_success:

                        print(
                            "Telegram trade update sent successfully."
                        )

                    else:

                        print(
                            "Failed to send Telegram trade update."
                        )

            # ------------------------------------------------
            # CHECK SIGNAL
            # ------------------------------------------------

            if trade_manager.active_trade is None:

                signal = signal_engine.process_candle(

                    bar_index=bar_index,

                    timestamp=timestamp,

                    close=float(
                        current["close"]
                    ),

                    rsi=float(
                        current["rsi"]
                    ),

                    previous_rsi=float(
                        previous["rsi"]
                    ),

                    macd=float(
                        current["macd"]
                    ),

                    macd_signal=float(
                        current["macd_signal"]
                    ),

                    previous_macd=float(
                        previous["macd"]
                    ),

                    previous_macd_signal=float(
                        previous["macd_signal"]
                    ),

                    ema=float(
                        current["ema_200"]
                    ),
                )

                # --------------------------------------------
                # CREATE NEW TRADE
                # --------------------------------------------

                if signal:

                    atr = float(
                        current["atr"]
                    )

                    if not pd.isna(atr):

                        trade = trade_manager.create_trade(

                            signal=signal,

                            atr=atr,

                            bar_index=bar_index,
                        )

                        # ----------------------------------------
                        # PRINT SIGNAL
                        # ----------------------------------------

                        print()

                        print(
                            "=" * 60
                        )

                        print(
                            f"NEW {signal.direction.value} SIGNAL"
                        )

                        print(
                            "=" * 60
                        )

                        print(
                            f"Symbol: {SYMBOL}"
                        )

                        print(
                            f"Timeframe: {TIMEFRAME}"
                        )

                        print(
                            f"Mode: "
                            f"{LIVE_SIGNAL_MODE.value}"
                        )

                        print()

                        print(
                            f"Time: "
                            f"{candle_time}"
                        )

                        print()

                        print(
                            f"Entry: "
                            f"{trade.entry_price:.4f}"
                        )

                        print(
                            f"SL:    "
                            f"{trade.stop_loss:.4f}"
                        )

                        print(
                            f"TP1:   "
                            f"{trade.take_profit_1:.4f}"
                        )

                        print(
                            f"TP2:   "
                            f"{trade.take_profit_2:.4f}"
                        )

                        print(
                            f"TP3:   "
                            f"{trade.take_profit_3:.4f}"
                        )

                        print()

                        print(
                            f"RSI:   "
                            f"{signal.rsi_value:.2f}"
                        )

                        print(
                            f"MACD:  "
                            f"{signal.macd_value:.6f}"
                        )

                        print(
                            f"MACD Signal: "
                            f"{signal.macd_signal:.6f}"
                        )

                        print(
                            "=" * 60
                        )

                        # ----------------------------------------
                        # SEND SIGNAL TO TELEGRAM
                        # ----------------------------------------

                        print()

                        print(
                            "Sending Telegram signal..."
                        )

                        telegram_message = (
                            format_telegram_signal(
                                signal=signal,
                                trade=trade,
                                candle_time=candle_time,
                            )
                        )

                        telegram_success = (
                            send_message(
                                telegram_message
                            )
                        )

                        if telegram_success:

                            print(
                                "Telegram signal sent successfully."
                            )

                        else:

                            print(
                                "Failed to send Telegram signal."
                            )

            # ------------------------------------------------
            # SAVE PROCESSED CANDLE
            # ------------------------------------------------

            last_processed_timestamp = timestamp

        except KeyboardInterrupt:

            print()

            print(
                "Live monitor stopped."
            )

            bot_status["status"] = "stopped"

            break

        except Exception as error:

            print()

            print(
                f"ERROR: {error}"
            )

            bot_status["last_error"] = str(
                error
            )

        time.sleep(
            CHECK_INTERVAL
        )


# ============================================================
# START LIVE BOT IN BACKGROUND
# ============================================================

def start_live_bot():

    live_thread = threading.Thread(
        target=run_live_mode,
        daemon=True,
        name="signal-monitor",
    )

    live_thread.start()

    return live_thread


# ============================================================
# MAIN
# ============================================================

def main():

    port = int(
        os.getenv(
            "PORT",
            "10000",
        )
    )

    host = "0.0.0.0"

    print()

    print("=" * 70)

    print(
        "STARTING RSI + MACD SIGNAL BOT WEB SERVICE"
    )

    print("=" * 70)

    print()

    if RUN_MODE == "BACKTEST":

        bot_status["status"] = "backtest"

        run_backtest_mode()

        return

    if RUN_MODE != "LIVE":

        bot_status["status"] = "error"

        bot_status["last_error"] = (
            "Invalid RUN_MODE. "
            'Use "BACKTEST" or "LIVE".'
        )

        print(
            bot_status["last_error"]
        )

        return

    # --------------------------------------------------------
    # START SIGNAL BOT
    # --------------------------------------------------------

    start_live_bot()

    # --------------------------------------------------------
    # START WEB SERVER FOR RENDER
    # --------------------------------------------------------

    print()

    print(
        f"Web server starting on "
        f"http://{host}:{port}"
    )

    print(
        "Health check endpoint: /health"
    )

    print()

    app.run(
        host=host,
        port=port,
        debug=False,
        use_reloader=False,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()