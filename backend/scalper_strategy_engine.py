# scalper_strategy_engine.py
"""
Complete scalper strategy engine (probability-based, auto-close on stronger signals).
Drop-in replacement — copy & paste into your project.

✅ VIX75 UPGRADE 1: Multi-Timeframe (HTF) Bias
- Added 'get_htf_bias' function (50/200 EMA cross on H4).
- This H4 bias ("UP" or "DOWN") is now passed to the decision engine.
- The bot will only trade in the direction of the H4 trend.

✅ VIX75 UPGRADE 2: Clean Signal & Order Execution
- Removed all Telegram spam.
- The bot now only sends ONE clean "SIGNAL" message before execution.
- It sends ONE clean "ORDER PLACED" message after success.
- This logic is now inside 'monitor_and_trade' instead of the decision engine.

✅ ENHANCEMENT #3: External Configuration
- All bot settings (SYMBOLS, DRY_RUN, TP_RATIO, etc.) are now loaded
  from an external 'config.json' file.
...
"""
from datetime import datetime, timedelta, timezone, time as dtime
import time as time_module          # alias stdlib module to avoid shadowing
import json                         # <-- NEW: For loading config
import pytz                         # <-- NEW: For loading config

import MetaTrader5 as mt5
import pandas as pd
from ta.volatility import AverageTrueRange
from zone_detector import detect_zones, detect_fast_zones
# --- VIX75 UPGRADE: We now import the 'format_confidence_label' ---
from trade_decision_engine import run_trade_decision_engine, rejected_signals_log, format_confidence_label
from telegram_notifier import send_telegram_message
from trade_executor import (
    place_order,
    modify_position_sltp,
    place_dynamic_order,
    trail_sl,
    move_to_breakeven,
    close_partial_and_move_sl_to_be,
    get_position_by_ticket
)
from performance_tracker import send_daily_summary
from trade_logger import log_pending_trade, update_trade_result
from symbol_info_helper import get_lot_constraints
from ta.trend import MACD, ADXIndicator
from news_filter_te import check_upcoming_high_impact
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice
from ta.volatility import BollingerBands
import csv, os, threading, traceback
from collections import defaultdict
import inspect
# --- (Removed format_confidence_label, it's now in trade_decision_engine) ---

# ============================
# === NEW: CONFIGURATION LOADER ===
# ============================

def load_config(path='config.json'):
    """
    Loads, validates, and processes the config.json file.
    """
    try:
        with open(path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"[CRITICAL] config.json not found at {path}. Bot cannot start.")
        exit()
    except json.JSONDecodeError:
        print(f"[CRITICAL] config.json is not valid JSON. Please check the file. Bot cannot start.")
        exit()
    except Exception as e:
        print(f"[CRITICAL] An error occurred loading config.json: {e}")
        exit()

    # --- Process Timeframes ---
    TIMEFRAME_MAP = {
        "TIMEFRAME_H1": mt5.TIMEFRAME_H1,
        "TIMEFRAME_M1": mt5.TIMEFRAME_M1,
        "TIMEFRAME_M5": mt5.TIMEFRAME_M5,
        "TIMEFRAME_M15": mt5.TIMEFRAME_M15,
        "TIMEFRAME_M30": mt5.TIMEFRAME_M30,
        "TIMEFRAME_H4": mt5.TIMEFRAME_H4,
        "TIMEFRAME_D1": mt5.TIMEFRAME_D1,
    }
    
    try:
        # Get the string (e.g., "TIMEFRAME_H1")
        tf_zone_str = config['StrategyParameters']['TIMEFRAME_ZONE']
        # Convert to MT5 object (e.g., mt5.TIMEFRAME_H1)
        config['StrategyParameters']['TIMEFRAME_ZONE'] = TIMEFRAME_MAP[tf_zone_str]

        tf_entry_str = config['StrategyParameters']['TIMEFRAME_ENTRY']
        config['StrategyParameters']['TIMEFRAME_ENTRY'] = TIMEFRAME_MAP[tf_entry_str]
        
        tf_confirm_str = config['StrategyParameters']['TIMEFRAME_CONFIRM']
        config['StrategyParameters']['TIMEFRAME_CONFIRM'] = TIMEFRAME_MAP[tf_confirm_str]
        
        # --- VIX75 UPGRADE: Add HTF Timeframe from config ---
        if 'TIMEFRAME_HTF' in config['StrategyParameters']:
            tf_htf_str = config['StrategyParameters']['TIMEFRAME_HTF']
            config['StrategyParameters']['TIMEFRAME_HTF'] = TIMEFRAME_MAP[tf_htf_str]
        else:
            # Fallback if not in config
            print("[WARN] 'TIMEFRAME_HTF' not in config.json, defaulting to H4.")
            config['StrategyParameters']['TIMEFRAME_HTF'] = mt5.TIMEFRAME_H4

    except KeyError as e:
        print(f"[CRITICAL] Config error: Invalid timeframe string '{e}'. Check StrategyParameters in config.json.")
        exit()

    # --- Process Timezone ---
    try:
        tz_str = config['Schedule']['TZ_JOBURG']
        config['Schedule']['TZ_JOBURG'] = pytz.timezone(tz_str)
    except Exception as e:
        print(f"[CRITICAL] Config error: Invalid timezone string '{tz_str}'. {e}")
        exit()

    print("[INFO] config.json loaded and processed successfully.")
    return config

# --- Load Config at startup ---
CONFIG = load_config('config.json')

# ============================
# CONFIG & GLOBAL STATE (REMOVED HARD-CODED VALUES)
# ============================

# --- All settings are now loaded from the CONFIG dictionary ---
SYMBOLS = CONFIG['BotSettings']['SYMBOLS']
TIMEFRAME_ZONE = CONFIG['StrategyParameters']['TIMEFRAME_ZONE']
TIMEFRAME_ENTRY = CONFIG['StrategyParameters']['TIMEFRAME_ENTRY']
TIMEFRAME_CONFIRM = CONFIG['StrategyParameters']['TIMEFRAME_CONFIRM']
TIMEFRAME_HTF = CONFIG['StrategyParameters']['TIMEFRAME_HTF'] # <-- VIX75 UPGRADE
ZONE_LOOKBACK = CONFIG['StrategyParameters']['ZONE_LOOKBACK']
TP_RATIO = CONFIG['StrategyParameters']['TP_RATIO']
MAGIC = CONFIG['BotSettings']['MAGIC']
DRY_RUN = CONFIG['BotSettings']['DRY_RUN']
CONFIDENCE_THRESHOLD = CONFIG['StrategyParameters']['CONFIDENCE_THRESHOLD']
CONF_PRIORITY_GLOBAL_MIN = CONFIG['StrategyParameters']['CONF_PRIORITY_GLOBAL_MIN']
ALLOW_PYRAMID_SAME_SIDE = CONFIG['StrategyParameters']['ALLOW_PYRAMID_SAME_SIDE']
AUTO_CLOSE_ON_STRONG = CONFIG['StrategyParameters']['AUTO_CLOSE_ON_STRONG']
CLOSE_CONF_DIFF = CONFIG['StrategyParameters']['CLOSE_CONF_DIFF']
MAX_TOUCH_ALLOWED = CONFIG['StrategyParameters']['MAX_TOUCH_ALLOWED']
PARTIAL_CLOSE_PERCENT = CONFIG['StrategyParameters']['PARTIAL_CLOSE_PERCENT']
SUMMARY_HOUR = CONFIG['Schedule']['SUMMARY_HOUR']
SUMMARY_MINUTE = CONFIG['Schedule']['SUMMARY_MINUTE']
TZ_JOBURG = CONFIG['Schedule']['TZ_JOBURG']
REJECTED_CSV = CONFIG['FilePaths']['REJECTED_CSV']
TRADES_LOCAL_CSV = CONFIG['FilePaths']['TRADES_LOCAL_CSV']
# --- VIX75 UPGRADE: Add new threshold for clean signals ---
MIN_CONF_FOR_TELEGRAM = CONFIG['StrategyParameters'].get('MIN_CONF_FOR_TELEGRAM', 0.75) # Default 0.75 if not in config


# Runtime state
active_trades = {}
active_trades_by_symbol = {}
zone_touch_counts = {}
_last_zone_alert_time = {}
_last_rejected_flush_index = 0
_rejected_flush_lock = threading.Lock()
_seen_closed_pairs = set()
_last_crt_alerts = {}
_last_summary_date_local = None
_last_summary_sent_ts = 0
tp1_hit_tickets = set()

# --- emergency control import (already implemented separately) ---
from emergency_control import check_emergency_stop

# === Session State Tracking ===
_current_global_session = None  # None / "Asia" / "London" / "New York"

def get_current_global_session():
    now = datetime.utcnow().time()
    if dtime(0, 0) <= now <= dtime(9, 0):
        return "Asia"
    if dtime(7, 0) <= now <= dtime(16, 0):
        return "London"
    if dtime(12, 0) <= now <= dtime(21, 0):
        return "New York"
    return None

def handle_global_session():
    global _current_global_session
    session = get_current_global_session()
    if session != _current_global_session:
        if session is None and _current_global_session is not None:
            safe_telegram(f"⏸️ {_current_global_session} session closed – bot sleeping until next active session.")
        elif session is not None:
            safe_telegram(f"✅ Bot awake – {session} session open.")
        _current_global_session = session
    return session is not None


def get_current_session_name():
    """Return human-readable session name based on UTC time."""
    now_utc = datetime.now(timezone.utc).time()

    # London 07:00–16:00 UTC
    if dtime(7, 0) <= now_utc <= dtime(16, 0):
        return "London"
    # New York 12:00–21:00 UTC
    if dtime(12, 0) <= now_utc <= dtime(21, 0):
        return "New York"
    # Asia 00:00–09:00 UTC
    if dtime(0, 0) <= now_utc <= dtime(9, 0):
        return "Asia"
    return None

def send_startup_intro():
    intro = (
        "🤖 **Nawthviper Algo-Scalper Engine Activated (FOREX/GOLD)**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📘 **STRATEGY OVERVIEW**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Methodology:** Confluence-based *price action scalping* on M1 & M5 charts.\n"
        "The system applies a multi-layered filter chain to identify precise, high-probability setups:\n"
        "   • **✅ VIX75 UPGRADE: H4 Trend Bias Filter (50/200 EMA)**\n"
        "   • **Primary Signal:** Candlestick patterns (*Engulfing*, *Pin Bars*) confirmed at H1 Supply/Demand Zones.\n"
        "   • **Advanced Filter:** Candle Range Theory (CRT) for momentum validation and early reversal detection.\n"
        "   • **Confluence Checks:** M5 Trend Alignment, MACD & RSI Momentum, VWAP Positioning.\n"
        "   • **Risk Management:** Dynamic SL/TP using **ATR-based volatility** and **structural targets**.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📈 **SIGNAL BEHAVIOR (VIX75 UPGRADE)**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Signals are now filtered and clean. Telegram spam is **DISABLED**.\n"
        "The bot will only send a single `SIGNAL EXECUTION` message when a trade is being placed.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 **CONFIDENCE LEVELS**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "   • **🔥 HIGH (≥ 0.85):** Strong confluence — ideal for execution.\n"
        "   • **⚖️ MEDIUM (0.70–0.84):** Moderate conviction.\n"
        "   • **❗ LOW (< 0.70):** Weak or early setups — observation only.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🕒 **ACTIVE TRADING SESSIONS (UTC)**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "   • **Asia (00:00–09:00):** JPY, AUD, NZD pairs\n"
        "   • **London (07:00–16:00):** GBPUSD, EURUSD, USDCHF\n"
        "   • **New York (12:00–21:00):** USDJPY, XAUUSD, USDCAD\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🧠 **SAFETY & MANAGEMENT FEATURES**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "   • News impact filter (to avoid high-volatility events)\n"
        "   • Equity-based emergency stop\n"
        "   • **Partial TP @ 1:1 R/R + Automatic Breakeven SL**\n"
        "   • ATR-based Trailing Stop\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ **DISCLAIMER**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "This bot is an **automated trading assistant**, not a financial advisor.\n"
        "Trading involves significant risk — never trade with funds you cannot afford to lose.\n"
        "Recommended: risk **1–2% of total equity per trade** for long-term sustainability.\n\n"
        "All signals are generated automatically without human intervention.\n\n"
        "👤 **Developer:** Thabo Masilompana\n"
        "📞 **Contact:** 066 229 7338\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    safe_telegram(intro)


# ============================
# HELPERS
# ============================

def send_info(msg):
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[SCALPER] {ts} {msg}")
    
def adaptive_adx_threshold(h1_df, lookback=200, percentile=70):
    """
    Dynamic ADX cutoff = Nth percentile of recent ADX values.
    Keeps the 'trade only in trending markets' logic but adapts to volatility.
    """
    from ta.trend import ADXIndicator
    adx_series = ADXIndicator(
        high=h1_df['high'], low=h1_df['low'], close=h1_df['close'], window=14
    ).adx()
    valid = adx_series.dropna()
    if len(valid) == 0:
        return 25  # safe fallback
    recent = valid.tail(min(lookback, len(valid)))
    return recent.quantile(percentile / 100.0)


def adaptive_confidence_threshold(h1_df, base=0.60, high_vol_add=0.05, low_vol_sub=0.05):
    """
    Adjust confidence threshold based on recent ATR volatility.
    Higher vol → slightly stricter, lower vol → slightly easier.
    """
    atr_series = AverageTrueRange(
        high=h1_df['high'], low=h1_df['low'], close=h1_df['close'], window=14
    ).average_true_range()
    if atr_series.empty:
        return base
    current = atr_series.iloc[-1]
    median = atr_series.median()
    if current > median * 1.3:
        return base + high_vol_add
    elif current < median * 0.7:
        return base - low_vol_sub
    return base


def safe_telegram(msg):
    try:
        send_telegram_message(msg)
    except Exception as e:
        print(f"[WARN] Telegram send failed: {e}")
        
def normalize_symbol(symbol):
    """
    Ensure correct broker suffix for the symbol (e.g., .mic, .pro).
    Checks availability via mt5.symbol_info.
    """
    # Direct symbol works
    if mt5.symbol_info(symbol):
        return symbol
    # Try common suffixes for Vault micro/pro accounts
    for suffix in [".mic", ".pro", ".cent"]:
        if mt5.symbol_info(symbol + suffix):
            return symbol + suffix
    return symbol  # fallback (may still fail if broker doesn't offer it)

def get_data(symbol, timeframe, bars):
    try:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    except Exception as e:
        print(f"[WARN] mt5.copy_rates_from_pos failed: {e}")
        return pd.DataFrame()
    if rates is None:
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    if df.empty:
        return df
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df


def calculate_trend(df):
    if df.empty:
        return None
    df = df.copy()
    df['SMA50'] = df['close'].rolling(50).mean()
    if len(df) < 51:
        return None
    last = float(df['close'].iloc[-1])
    sma = float(df['SMA50'].iloc[-1])
    if last > sma:
        return "uptrend"
    elif last < sma:
        return "downtrend"
    else:
        return "sideways"

# --- VIX75 UPGRADE 1: H4 BIAS FUNCTION ---
def get_htf_bias(df, fast_ma=50, slow_ma=200):
    """
    Determines the Higher-Timeframe bias using an EMA cross.
    Returns 'UP', 'DOWN', or 'NEUTRAL'.
    """
    if df.empty or len(df) < slow_ma:
        return None  # Not enough data

    df = df.copy()
    try:
        df['EMA_fast'] = df['close'].ewm(span=fast_ma, adjust=False).mean()
        df['EMA_slow'] = df['close'].ewm(span=slow_ma, adjust=False).mean()
        
        last_fast = df['EMA_fast'].iloc[-1]
        last_slow = df['EMA_slow'].iloc[-1]
        
        if last_fast > last_slow:
            return "UP"
        elif last_fast < last_slow:
            return "DOWN"
        else:
            return "NEUTRAL"
    except Exception as e:
        send_info(f"[ERROR] Failed to calculate HTF Bias: {e}")
        return None
# --- END UPGRADE 1 ---


def calculate_risk_based_lot(symbol, sl_price, entry_price, risk_percent=1.0):
    """
    Calculate lot size based on % equity risk and SL distance.
    If equity is too small to support risk-based sizing (e.g., $10 account),
    it falls back to MIN_LOT and warns via Telegram.
    """
    try:
        if sl_price is None or entry_price is None:
            return None
        if sl_price == entry_price:
            return None

        acc = mt5.account_info()
        if acc is None:
            send_info(f"[WARN] calculate_risk_based_lot: account_info unavailable")
            return None
        equity = float(acc.equity)

        # --- Small account safety: fallback to MIN_LOT if too small ---
        MIN_LOT, MAX_LOT, LOT_STEP = get_lot_constraints(symbol)
        if equity <= 50:  # 👈 threshold: accounts <= $50 considered too small
            safe_telegram(f"[RISK WARNING] Equity ${equity:.2f} too low for % risk sizing. Using fixed lot={MIN_LOT}")
            return MIN_LOT

        sinfo = mt5.symbol_info(symbol)
        if sinfo is None:
            send_info(f"[WARN] calculate_risk_based_lot: symbol_info unavailable for {symbol}")
            return None

        tick_value = getattr(sinfo, "trade_tick_value", None)
        tick_size = getattr(sinfo, "trade_tick_size", None)

        if tick_value is None or tick_size is None or tick_value == 0 or tick_size == 0:
            send_info(f"[WARN] calculate_risk_based_lot: tick metadata missing for {symbol}, using MIN_LOT")
            return MIN_LOT

        # Compute risk amount
        risk_amount = equity * (risk_percent / 100.0)

        sl_distance = abs(entry_price - sl_price)
        if sl_distance <= 0:
            return None

        sl_distance_in_ticks = sl_distance / float(tick_size)
        cost_per_lot = sl_distance_in_ticks * float(tick_value)
        if cost_per_lot <= 0:
            send_info(f"[WARN] calculate_risk_based_lot: cost_per_lot <= 0 for {symbol}, using MIN_LOT")
            return MIN_LOT

        raw_lots = risk_amount / cost_per_lot
        if raw_lots <= 0:
            return MIN_LOT

        # Clamp and round
        raw_lots = max(MIN_LOT, min(MAX_LOT, raw_lots))
        steps = int(raw_lots / LOT_STEP)
        lot = round(steps * LOT_STEP, 8)
        lot = max(MIN_LOT, min(MAX_LOT, lot))
        return float(lot)

    except Exception as e:
        send_info(f"[WARN] Risk-based lot calc failed: {e}")
        return None



def is_in_active_session(symbol: str) -> bool:
    """Return True if symbol is in its strong session window (UTC hours)."""
    now_utc = datetime.now(timezone.utc).hour

    session_map = {
        "GBPUSD": range(7, 16),   # London
        "EURUSD": range(7, 16),   # London
        "USDJPY": list(range(0, 9)) + list(range(12, 21)),  # Tokyo + New York
        "AUDUSD": range(0, 9),    # Asia
        "NZDUSD": range(0, 9),    # Asia
        "USDCAD": range(12, 21),  # New York
        "USDCHF": range(7, 16),   # London
        "XAUUSD": range(12, 21),  # New York
    }

    hours = session_map.get(symbol.upper())
    if not hours:
        return True  # default: always trade if not mapped
    return now_utc in hours

def print_detected_zones(symbol, demand_zones, supply_zones, fast_demand, fast_supply):
    print(f"[INFO] {symbol} Zones: {len(demand_zones)} demand, {len(supply_zones)} supply")
    for z in demand_zones:
        try:
            zp = float(z.get('price', 0.0))
            print(f"  Demand @ {zp:.5f} time:{z.get('time')}")
        except Exception:
            print(f"  Demand zone: {z}")
    for z in supply_zones:
        try:
            zp = float(z.get('price', 0.0))
            print(f"  Supply @ {zp:.5f} time:{z.get('time')}")
        except Exception:
            print(f"  Supply zone: {z}")
    print(f"[INFO] {symbol} Fast Zones: demand {len(fast_demand)} supply {len(fast_supply)}")

# ============================
# STATE RECOVERY (NEW)
# ============================

def load_open_trades_from_csv(path=TRADES_LOCAL_CSV):
    """
    Reloads active trades from the CSV file on startup.
    This repopulates the 'active_trades_by_symbol' map so the bot
    can manage and close trades that were open before a restart.
    """
    global active_trades_by_symbol, tp1_hit_tickets
    if not os.path.isfile(path):
        send_info("[STATE] No local trade history found, starting fresh.")
        return

    send_info(f"[STATE] Loading open trades from {path}...")
    reloaded_count = 0
    try:
        with open(path, mode="r", newline="", encoding="utf-8") as f:
            # Use DictReader to read CSV by header names
            reader = csv.DictReader(f)
            for row in reader:
                # An 'open' trade has no exit_price or result
                is_open = (row.get('exit_price') == '' or row.get('exit_price') is None) and \
                          (row.get('result') == '' or row.get('result') is None)
                
                if is_open:
                    symbol = row.get('symbol')
                    side = row.get('side')
                    ticket_str = row.get('trade_id') # This is the ticket
                    timestamp_str = row.get('timestamp')
                    entry_price_str = row.get('entry_price') # <-- NEW
                    sl_str = row.get('sl') # <-- NEW

                    if not all([symbol, side, ticket_str, timestamp_str, entry_price_str, sl_str]):
                        send_info(f"[WARN] Skipping malformed open trade row (missing data): {row}")
                        continue

                    try:
                        # Convert string timestamp back to epoch float
                        ts_epoch = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").timestamp()
                        ticket_int = int(ticket_str)
                        entry_price = float(entry_price_str)
                        sl = float(sl_str)
                    except Exception as e:
                        send_info(f"[WARN] Could not parse reloaded trade data for {ticket_str}: {e}")
                        continue

                    # Check for conflict (should not happen if logic is sound, but good safety)
                    if symbol in active_trades_by_symbol:
                        send_info(f"[WARN] Conflict on reload: {symbol} already in active map. Ignoring CSV row.")
                        continue
                        
                    # Repopulate the map with all data needed for partial TP
                    active_trades_by_symbol[symbol] = {
                        'side': side,
                        'ticket': ticket_int,
                        'trade_id': ticket_str,
                        'confidence': None,     # Confidence is lost on restart
                        'ts': ts_epoch,
                        'entry_price': entry_price, # <-- NEW
                        'sl': sl                    # <-- NEW
                    }
                    
                    # Check if the trade is already risk-free (by checking live SL)
                    position = get_position_by_ticket(ticket_int)
                    if position:
                        if (side == 'buy' and position.sl >= entry_price) or \
                           (side == 'sell' and position.sl <= entry_price):
                            tp1_hit_tickets.add(ticket_int)
                            send_info(f"  > Reloaded risk-free trade: {symbol} {side.upper()} (Ticket: {ticket_str})")
                        else:
                            send_info(f"  > Reloaded active trade: {symbol} {side.upper()} (Ticket: {ticket_str})")
                            reloaded_count += 1
                    else:
                        send_info(f"  > Reloaded active trade (position not found in MT5): {symbol} {side.upper()} (Ticket: {ticket_str})")
                        reloaded_count += 1

        if reloaded_count > 0:
            send_info(f"[STATE] Successfully reloaded {reloaded_count} open trade(s).")
        else:
            send_info("[STATE] No open trades found in CSV to reload.")

    except Exception as e:
        send_info(f"[ERROR] Failed to read trade history file {path}: {e}\n{traceback.format_exc()}")
        
        
# ============================
# REJECTED SIGNALS CSV FLUSH
# ============================

def flush_rejected_signals_to_csv(path=REJECTED_CSV):
    global _last_rejected_flush_index
    with _rejected_flush_lock:
        try:
            start_index = _last_rejected_flush_index
            total = len(rejected_signals_log)
            if total <= start_index:
                return
            file_exists = os.path.isfile(path)
            with open(path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["timestamp", "reason", "zone_type", "zone_price", "strategy", "trend"])
                for entry in rejected_signals_log[start_index:total]:
                    writer.writerow([
                        entry.get("timestamp", ""),
                        entry.get("reason", ""),
                        entry.get("zone_type", ""),
                        entry.get("zone_price", ""),
                        entry.get("strategy", ""),
                        entry.get("trend", "")
                    ])
            _last_rejected_flush_index = total
            send_info(f"Flushed {total - start_index} rejected signals to {path}")
        except Exception as e:
            send_info(f"[WARN] Failed to flush rejected signals: {e}")


# ============================
# LOCAL TRADES CSV - fallback
# ============================

def append_trade_to_local_csv(row: dict, path=TRADES_LOCAL_CSV):
    """Local safety log. Includes symbol column as requested."""
    try:
        file_exists = os.path.isfile(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            fieldnames = [
                "trade_id", "timestamp", "symbol", "strategy", "side", "entry_reason", "zone_price",
                "entry_price", "sl", "tp", "lot_size", "exit_price", "exit_time", "profit", "result"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception as e:
        send_info(f"[WARN] Could not append trade to local CSV: {e}")


# ============================
# MT5 POSITION HELPERS (inspect & close)
# ============================

def mt5_init_if_needed():
    try:
        if not mt5.initialize():
            send_info(f"[WARN] mt5.initialize failed: {mt5.last_error()}")
            return False
        return True
    except Exception as e:
        send_info(f"[WARN] mt5.initialize threw: {e}")
        return False


def get_live_positions(symbol=None):
    try:
        if not mt5_init_if_needed():
            return []
        if symbol:
            pos = mt5.positions_get(symbol=symbol)
        else:
            pos = mt5.positions_get()
        return pos if pos is not None else []
    except Exception as e:
        send_info(f"[WARN] positions_get error: {e}")
        return []


def find_live_position_for_symbol(symbol):
    """
    Return the first live position object for this symbol (if any).
    For netting accounts there will be at most one; for hedging, there may be multiple.
    """
    positions = get_live_positions(symbol)
    if not positions:
        return None
    # Return first position (caller may inspect type/volume)
    return positions[0]


def close_positions_for_symbol(symbol, reason_msg=None):
    """
    Attempt to close all live positions for the symbol.
    Uses mt5.order_send DEAL opposite volume to close positions one-by-one.
    Returns list of dicts with results.
    """
    results = []
    try:
        positions = get_live_positions(symbol)
        if not positions:
            return results
        for pos in positions:
            vol = float(getattr(pos, 'volume', getattr(pos, 'volume_float', 0.0)))
            if vol <= 0:
                continue
            pos_type = getattr(pos, 'type', None)
            # Determine opposite side
            if pos_type == mt5.ORDER_TYPE_BUY:
                close_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(symbol).bid
            else:
                close_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(symbol).ask
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": vol,
                "type": close_type,
                "price": price,
                "deviation": 20,
                "magic": MAGIC,
                "comment": f"auto_close:{reason_msg or 'auto_close'}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC
            }
            if DRY_RUN:
                send_info(f"(DRY_RUN) Would close {symbol} vol={vol} type={close_type}")
                results.append({"status": "DRY", "symbol": symbol, "volume": vol})
                continue
            res = mt5.order_send(request)
            results.append({"status": getattr(res, 'retcode', None), "symbol": symbol, "volume": vol, "result": str(res)})
        return results
    except Exception as e:
        send_info(f"[WARN] close_positions_for_symbol exception: {e}\n{traceback.format_exc()}")
        return [{"status": "error", "error": str(e)}]


def has_live_conflict(symbol, side):
    """
    Return: (conflict_exists: bool, existing_confidence: float or None)
    Conflict exists if there's any live position on the symbol and either:
     - it's opposite side (hedging or netting)
     - or same-side but we don't allow pyramid (ALLOW_PYRAMID_SAME_SIDE False)
    We'll try to return known confidence if we stored it in active_trades_by_symbol.
    """
    # Check runtime map first
    rec = active_trades_by_symbol.get(symbol)
    if rec:
        existing_side = rec.get('side')
        existing_conf = rec.get('confidence', None)
        if existing_side != side:
            return True, existing_conf
        if existing_side == side and not ALLOW_PYRAMID_SAME_SIDE:
            return True, existing_conf
        # else allow
        return False, existing_conf

    # If not in runtime map, check live MT5 positions
    positions = get_live_positions(symbol)
    if not positions:
        return False, None
    # If any position exists, consider it a conflict by default (safe)
    # Caller may decide to close if new signal strong enough
    for pos in positions:
        pos_side = 'buy' if getattr(pos, 'type', None) == mt5.ORDER_TYPE_BUY else 'sell'
        # if pos_side != side -> conflict
        if pos_side != side:
            return True, None
        else:
            # same side exists; if pyramid not allowed, conflict
            if not ALLOW_PYRAMID_SAME_SIDE:
                return True, None
    return False, None

# ============================
# CONFLICT CHECK WRAPPER (pyramiding + auto-close)
# ============================

def has_conflict_and_existing_confidence(symbol, side):
    """
    Returns (conflict_exists, existing_confidence or None)
    Handles pyramiding & auto-close logic.
    FIXED: Now properly detects opposite-side conflicts in all cases.
    """
    # Check runtime map first
    rec = active_trades_by_symbol.get(symbol)
    if rec:
        existing_side = rec.get('side')
        existing_conf = rec.get('confidence', None)

        if existing_side != side:
            # Opposite side exists → conflict
            return True, existing_conf
        if existing_side == side and not ALLOW_PYRAMID_SAME_SIDE:
            # Same-side exists, pyramid disabled → conflict
            return True, existing_conf
        # Same-side, pyramid allowed → no conflict
        return False, existing_conf

    # No active runtime record → check live positions from MT5
    positions = get_live_positions(symbol)
    if not positions:
        return False, None

    # FIXED: Check each position to find conflicts
    for pos in positions:
        pos_side = 'buy' if getattr(pos, 'type',None) == mt5.ORDER_TYPE_BUY else 'sell'
        
        if pos_side != side:
            # Found opposite-side position → conflict
            return True, None
        elif pos_side == side and not ALLOW_PYRAMID_SAME_SIDE:
            # Same-side position but pyramiding not allowed → conflict
            return True, None
    
    # No conflicts found
    return False, None

# ==========================================================
# === NEW TRADE MANAGEMENT FUNCTION (ENHANCEMENT #2) ===
# ==========================================================
def check_for_partial_tp(symbol):
    """
    Checks all active trades for the symbol to see if 1R (TP1) has been hit.
    If so, triggers partial close and moves SL to BE.
    """
    global active_trades_by_symbol, tp1_hit_tickets
    
    # Check if there are any active trades for this symbol
    if symbol not in active_trades_by_symbol:
        return

    # Get the trade record from our bot's memory
    trade_record = active_trades_by_symbol.get(symbol)
    if not trade_record:
        return
        
    ticket = trade_record.get('ticket')
    if not ticket:
        return
        
    # 1. Check if this trade is already risk-free
    if ticket in tp1_hit_tickets:
        return

    # 2. Get the trade data needed to calculate TP1
    entry_price = trade_record.get('entry_price')
    sl = trade_record.get('sl')
    side = trade_record.get('side')
    
    if not all([entry_price, sl, side]):
        send_info(f"[WARN] Trade {ticket} missing data for partial TP calc.")
        return

    # 3. Calculate the 1R risk distance and the TP1 target
    try:
        risk_distance = abs(entry_price - sl)
        if risk_distance == 0:
            return
            
        tp1_target = entry_price + risk_distance if side == 'buy' else entry_price - risk_distance
    except Exception as e:
        send_info(f"[WARN] TP1 calc failed for {ticket}: {e}")
        return

    # 4. Get the current market price
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return
    
    current_price = tick.bid if side == 'buy' else tick.ask

    # 5. Check if TP1 has been hit
    tp1_hit = False
    if side == 'buy' and current_price >= tp1_target:
        tp1_hit = True
    elif side == 'sell' and current_price <= tp1_target:
        tp1_hit = True

    # 6. If TP1 hit, execute partial close and move to BE
    if tp1_hit:
        send_info(f"✅ {symbol} 1R target hit at {tp1_target:.5f}. Securing trade...")
        
        if DRY_RUN:
            send_info(f"(DRY_RUN) Would close {PARTIAL_CLOSE_PERCENT*100}% and move SL to BE for {ticket}")
            tp1_hit_tickets.add(ticket) # Add to set even in dry run
        else:
            success = close_partial_and_move_sl_to_be(ticket, partial_close_percent=PARTIAL_CLOSE_PERCENT)
            
            if success:
                # Add to our set to prevent this from running again
                tp1_hit_tickets.add(ticket)
                # --- VIX75 UPGRADE: We move the TG message to trade_executor ---
                # safe_telegram(f"💰 {symbol} TP1 hit! Closed 50% and moved SL to BE.")
            else:
                send_info(f"[ERROR] Partial close execution failed for {ticket}.")

# ============================
# CORE MONITOR & TRADE
# ============================

def monitor_and_trade(symbol, strategy_mode=None, fixed_lot=None):
    """
    Main per-symbol monitor function. Intended to be run by scheduler for each symbol.
    """
    global zone_touch_counts, active_trades, active_trades_by_symbol, tp1_hit_tickets

    try:
        account = mt5.account_info()
    except Exception as e:
        send_info(f"[WARN] account_info failed: {e}")
        return

    if account:
        try:
            reason = check_emergency_stop(account.equity)
            if reason:
                msg = f"🚨 Emergency Stop Triggered: {reason}. Trading halted ({symbol})"
                send_info(msg)
                safe_telegram(msg)
                return
        except Exception as e:
            send_info(f"[WARN] check_emergency_stop failed: {e}")

    # --- VIX75 UPGRADE 1: Fetch H4 data for bias ---
    h4_df = get_data(symbol, TIMEFRAME_HTF, 250) # 200 + buffer
    if h4_df.empty:
        send_info(f"[ERROR] {symbol} H4 data unavailable.")
        return

    htf_bias = get_htf_bias(h4_df)
    if not htf_bias or htf_bias == "NEUTRAL":
        send_info(f"[INFO] {symbol} Waiting for clear H4 bias. Current: {htf_bias}")
        return
    
    send_info(f"[INFO] {symbol} H4 BIAS IS: {htf_bias}")
    # --- END UPGRADE 1 ---

    # --- Fetch H1 (Zone Timeframe) and detect zones
    h1_df = get_data(symbol, TIMEFRAME_ZONE, ZONE_LOOKBACK)
    if h1_df.empty or len(h1_df) < 3: # Ensure we have enough data for the range
        send_info(f"[ERROR] {symbol} H1 unavailable or insufficient data.")
        return

    last_completed_h1_candle = h1_df.iloc[-2] # Use [-2] for the last *closed* candle
    htf_high = last_completed_h1_candle['high']
    htf_low = last_completed_h1_candle['low']

    demand_zones, supply_zones = detect_zones(h1_df)
    fast_demand, fast_supply = detect_fast_zones(h1_df)

    trend = calculate_trend(h1_df)
    if not trend:
        send_info(f"[ERROR] Not enough H1 data for {symbol}")
        return

    strategy_to_run = "trend_follow"  # Default strategy
    try:
        adx = ADXIndicator(high=h1_df['high'], low=h1_df['low'], close=h1_df['close'], window=14)
        adx_value = adx.adx().iloc[-1]
        adaptive_adx = adaptive_adx_threshold(h1_df, lookback=200, percentile=50)
        min_floor = 15.0
        required_adx = max(adaptive_adx, min_floor)
        
        if adx_value < required_adx:
            send_info(f"[FILTER] {symbol} ADX={adx_value:.2f} < required {required_adx:.2f} → Switching to Ranging Strategy.")
            strategy_to_run = "ranging"
    except Exception as e:
        send_info(f"[WARN] ADX calculation failed: {e}")
        
    fibo_zone = None
    try:
        if trend == "uptrend":
            low_point = h1_df['low'].rolling(20).min().iloc[-1]
            high_point = h1_df['high'].iloc[-1]
            diff = high_point - low_point
            fibo_zone = (high_point - (diff * 0.618), high_point - (diff * 0.50))
        elif trend == "downtrend":
            high_point = h1_df['high'].rolling(20).max().iloc[-1]
            low_point = h1_df['low'].iloc[-1]
            diff = high_point - low_point
            fibo_zone = (high_point - (diff * 0.50), high_point - (diff * 0.618))
    except Exception as e:
        send_info(f"[WARN] Fibo calc failed: {e}")
        fibo_zone = None

    if check_upcoming_high_impact(symbol, minutes_ahead=60):
        send_info(f"[NEWS FILTER] {symbol} → High-impact news in next 60min, skip trading.")
        return

    if not is_in_active_session(symbol):
        send_info(f"[SESSION FILTER] {symbol} → Not in optimal trading session, skip trading.")
        try:
            check_closed_trades(symbol)
        except Exception as e:
            send_info(f"[WARN] check_closed_trades failed in sleep mode: {e}")
        return

    # === DATA FETCH & VALIDATION (M1 and M5) ===
    m1_df = get_data(symbol, TIMEFRAME_ENTRY, 200)
    if len(m1_df) < 35: 
        send_info(f"[ERROR] Not enough M1 candles for {symbol} (need 35, got {len(m1_df)})")
        return
    
    m5_df = get_data(symbol, TIMEFRAME_CONFIRM, 60)
    m5_context = {}
    
    if m5_df.empty or len(m5_df) < 5:
        send_info(f"[ERROR] Not enough M5 candles for {symbol} (need 5, got {len(m5_df)}). Skipping pattern check.")
        return
        
    bb_zones = None
    if strategy_to_run == "ranging" and not m5_df.empty and len(m5_df) >= 20:
        try:
            bb = BollingerBands(close=m5_df['close'], window=20, window_dev=2)
            bb_high = bb.bollinger_hband().iloc[-1]
            bb_low = bb.bollinger_lband().iloc[-1]
            bb_zones = { "supply": bb_high, "demand": bb_low }
        except Exception:
            bb_zones = None
        
    if len(m5_df) >= 35: 
        try:
            m5_context['trend'] = calculate_trend(m5_df)
            m5_context['macd'] = MACD(close=m5_df['close']).macd().dropna().values
            m5_context['rsi'] = RSIIndicator(close=m5_df['close']).rsi().dropna().values
        except Exception as e:
            send_info(f"[WARN] M5 context indicators failed: {e}")
            m5_context = {}

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        send_info(f"[ERROR] No tick data for {symbol}.")
        return
    price = float(tick.bid)

    original_demand_count = len(demand_zones)
    original_supply_count = len(supply_zones)
    
    demand_zones = [z for z in demand_zones if z['price'] < price]
    supply_zones = [z for z in supply_zones if z['price'] > price]

    filtered_demand_count = len(demand_zones)
    filtered_supply_count = len(supply_zones)
    
    if (original_demand_count != filtered_demand_count) or (original_supply_count != filtered_supply_count):
        send_info(f"[ZONE FILTER] {symbol}: Filtered zones. Demand: {original_demand_count} -> {filtered_demand_count}. Supply: {original_supply_count} -> {filtered_supply_count}.")

    sinfo = mt5.symbol_info(symbol)
    if sinfo is None:
        send_info(f"[ERROR] symbol_info failed for {symbol}.")
        return
    point = sinfo.point

    try:
        # M1 indicators
        macd_calc = MACD(close=m1_df['close'])
        macd_line = macd_calc.macd().dropna().values
        macd_signal = macd_calc.macd_signal().dropna().values
        rsi_values = RSIIndicator(close=m1_df['close']).rsi().dropna().values
        vwap_value = VolumeWeightedAveragePrice(
            high=m1_df['high'], low=m1_df['low'], close=m1_df['close'], volume=m1_df['real_volume']
        ).vwap.iloc[-1]
        atr = AverageTrueRange(high=m1_df['high'], low=m1_df['low'], close=m1_df['close']).average_true_range().iloc[-1]
    except Exception as e:
        send_info(f"[WARN] M1 Indicator calculation failed: {e}")
        macd_line = macd_signal = rsi_values = vwap_value = atr = None

    MIN_LOT, MAX_LOT, LOT_STEP = get_lot_constraints(symbol)
    SL_BUFFER = 150 * point
    lot_size = max(MIN_LOT, fixed_lot if fixed_lot else MIN_LOT)

    fallback_range = 50 * point 
    if atr is not None and not pd.isna(atr) and atr > 0:
        adaptive_check_range = max(atr * 1.0, fallback_range) 
    else:
        adaptive_check_range = fallback_range
        send_info(f"[WARN] {symbol} M1 ATR invalid, using fallback check_range: {adaptive_check_range}")
    
    try:
        strict_signals, _ = run_trade_decision_engine(
            symbol=symbol,
            point=point,
            current_price=price,
            trend=trend,
            demand_zones=demand_zones,
            supply_zones=supply_zones,
            m1_candles_for_crt=m1_df.iloc[-3:],
            m5_candles_for_patterns=m5_df.iloc[-5:],
            active_trades=active_trades,
            zone_touch_counts=zone_touch_counts,
            SL_BUFFER=SL_BUFFER,
            TP_RATIO=TP_RATIO,
            CHECK_RANGE=adaptive_check_range, 
            LOT_SIZE=lot_size,
            MAGIC=MAGIC,
            strategy_mode="trend_follow",
            macd=macd_line,
            macd_signal=macd_signal,
            rsi=rsi_values,
            vwap=vwap_value,
            atr=atr,
            m5_context=m5_context,
            htf_high=htf_high,
            htf_low=htf_low,
            last_closed_h1=last_completed_h1_candle, 
            fibo_zone=fibo_zone,                      
            bollinger_bands=bb_zones,
            htf_bias=htf_bias # <-- VIX75 UPGRADE 1
        )
    except Exception as e:
        send_info(f"[WARN] trade_decision_engine (strict) raised: {e}\n{traceback.format_exc()}")
        strict_signals = []

    try:
        aggressive_signals, _ = run_trade_decision_engine(
            symbol=symbol,
            point=point,
            current_price=price,
            trend=trend,
            demand_zones=fast_demand,
            supply_zones=fast_supply,
            m1_candles_for_crt=m1_df.iloc[-3:],
            m5_candles_for_patterns=m5_df.iloc[-5:],
            active_trades=active_trades,
            zone_touch_counts=zone_touch_counts,
            SL_BUFFER=SL_BUFFER,
            TP_RATIO=TP_RATIO,
            CHECK_RANGE=adaptive_check_range, 
            LOT_SIZE=lot_size,
            MAGIC=MAGIC,
            strategy_mode="aggressive",
            macd=macd_line,
            macd_signal=macd_signal,
            rsi=rsi_values,
            vwap=vwap_value,
            atr=atr,
            m5_context=m5_context,
            htf_high=htf_high, 
            htf_low=htf_low,
            last_closed_h1=last_completed_h1_candle,
            fibo_zone=fibo_zone,
            bollinger_bands=bb_zones,
            htf_bias=htf_bias # <-- VIX75 UPGRADE 1
        )
    except Exception as e:
        send_info(f"[WARN] trade_decision_engine (aggressive) raised: {e}\n{traceback.format_exc()}")
        aggressive_signals = []

    print_detected_zones(symbol, demand_zones, supply_zones, fast_demand, fast_supply)

    if strict_signals:
        signals = list(strict_signals)
    elif aggressive_signals:
        signals = list(aggressive_signals)
    else:
        signals = []

    signals = sorted(signals, key=lambda s: float(s.get("confidence", 0.0)), reverse=True)

    unique, seen = [], set()
    for s in signals:
        key = (s.get("side"), round(s.get("entry", 0), 5), round(s.get("sl", 0), 5), round(s.get("tp", 0), 5))
        if key not in seen:
            unique.append(s)
            seen.add(key)
    signals = unique

    if len({s.get("side") for s in signals}) > 1:
        strongest = max(signals, key=lambda s: s.get("confidence", 0))
        signals = [strongest]

    # ==========================================================
    # === VIX75 UPGRADE 2: NEW CLEAN SIGNAL/EXECUTION LOOP ===
    # ==========================================================
    for sig in signals:
        try:
            side = sig.get('side')
            entry = sig.get('entry')
            sl = sig.get('sl')
            tp = sig.get('tp')
            zone = sig.get('zone')
            reason = sig.get('reason', '')
            strategy = sig.get('strategy', '')
            confidence = float(sig.get('confidence', 0.0))

            # --- Risk-based lot override ---
            try:
                risk_lot = calculate_risk_based_lot(symbol, sl_price=sl, entry_price=entry, risk_percent=1.0) # Using 1% risk from config
                if risk_lot:
                    lot = risk_lot
                else:
                    lot = max(MIN_LOT, sig.get('lot', lot_size)) # Fallback to min lot
            except Exception as e:
                send_info(f"[WARN] risk-based lot calc failed for {symbol}: {e}")
                lot = max(MIN_LOT, sig.get('lot', lot_size)) # Fallback to min lot

            # --- Final Confidence Check ---
            if confidence < CONF_PRIORITY_GLOBAL_MIN:
                send_info(f"[SKIP] {symbol} {side} signal confidence {confidence:.2f} < global min {CONF_PRIORITY_GLOBAL_MIN}")
                continue
            dynamic_conf = adaptive_confidence_threshold(h1_df, base=CONFIDENCE_THRESHOLD)
            if confidence < dynamic_conf:
                send_info(f"[SKIP] {symbol} {side} signal confidence {confidence:.2f} < adaptive min {dynamic_conf:.2f}")
                continue

            # --- Conflict Check (Auto-Close Logic) ---
            conflict, existing_conf = has_conflict_and_existing_confidence(symbol, side)
            
            if conflict:
                send_info(f"[CONFLICT] {symbol} has existing position conflict for {side.upper()}")
                
                if AUTO_CLOSE_ON_STRONG and existing_conf is not None:
                    if confidence >= existing_conf + CLOSE_CONF_DIFF:
                        send_info(f"[AUTO-CLOSE] Closing {symbol} opposite positions for stronger {side.upper()} signal (Conf {confidence:.2f} > {existing_conf:.2f})")
                        close_results = close_positions_for_symbol(symbol, reason_msg=f"auto_close_by_conf_{confidence:.2f}")
                        send_info(f"[AUTO-CLOSE] Close results: {close_results}")
                        
                        active_trades_by_symbol.pop(symbol, None)
                        
                        wait_attempts = 0
                        positions_still_exist = True
                        while positions_still_exist and wait_attempts < 15:
                            time_module.sleep(0.5) 
                            live_positions = get_live_positions(symbol)
                            positions_still_exist = len(live_positions) > 0
                            
                            if not positions_still_exist:
                                send_info(f"[AUTO-CLOSE] Successfully closed all positions for {symbol}")
                                break
                                
                            wait_attempts += 1
                            if wait_attempts >= 15:
                                send_info(f"[AUTO-CLOSE] Timeout waiting for positions to close on {symbol}")
                                continue # Skip this signal, can't open
                    else:
                        send_info(f"[CONFLICT] {side.upper()} signal confidence {confidence:.2f} not strong enough to override existing {existing_conf:.2f}")
                        continue
                else:
                    send_info(f"[CONFLICT] {side.upper()} signal blocked due to existing position (pyramid off or no conf)")
                    continue
            
            # --- VIX75 UPGRADE: Send ONE clean signal message ---
            if confidence >= MIN_CONF_FOR_TELEGRAM:
                full_signal_msg = (
                    f"📥 SIGNAL: {symbol} | {side.upper()} {reason}\n"
                    f"   🔹 Entry: {entry:.5f}\n"
                    f"   🔹 SL: {sl:.5f}\n"
                    f"   🔹 TP (Final): {tp:.5f}\n"
                    f"   🔹 Confidence: {format_confidence_label(confidence)}"
                )
                safe_telegram(full_signal_msg)
            # --- END OF CLEAN SIGNAL MESSAGE ---

            # --- Place order ---
            if DRY_RUN:
                fake_ticket = int(time_module.time() * 1000) % 1000000
                trade_id = log_pending_trade(strategy, side, reason, zone, entry, sl, tp, lot, symbol=symbol, trade_id=fake_ticket)
                active_trades_by_symbol[symbol] = {
                    'side': side, 'ticket': fake_ticket, 'trade_id': trade_id,
                    'confidence': confidence, 'ts': time_module.time(),
                    'entry_price': entry, 'sl': sl 
                }
                append_trade_to_local_csv({
                    "trade_id": trade_id, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "symbol": symbol, "strategy": strategy, "side": side, "entry_reason": reason,
                    "zone_price": zone, "entry_price": entry, "sl": sl, "tp": tp, "lot_size": lot,
                    "exit_price": "", "exit_time": "", "profit": "", "result": "DRY_RUN"
                })
                # --- VIX75 UPGRADE: Clean Dry Run message ---
                safe_telegram(f"DRY RUN: ✅ {symbol} {side.upper()} conf:{confidence:.2f} lot:{lot} ticket:{fake_ticket}")
            
            else:
                # --- LIVE EXECUTION (using 2-step place_order -> modify_sltp) ---
                result = place_order(symbol, side, lot, MAGIC, comment="NawthviperBot") # Step 1: Market order

                if result is not None and getattr(result, 'retcode', None) == mt5.TRADE_RETCODE_DONE:
                    ticket = None
                    try:
                        deal_id = getattr(result, 'deal', None)
                        if deal_id:
                            deal_info = mt5.history_deals_get(deal=deal_id)
                            if deal_info and len(deal_info) > 0:
                                ticket = deal_info[0].position_id # This is the position ticket
                    except Exception as e:
                        send_info(f"[WARN] Could not find ticket from deal {deal_id}: {e}")

                    if not ticket:
                        try:
                            send_info("[INFO] Ticket not found via deal, trying fallback...")
                            time_module.sleep(0.5) # Wait for position to appear
                            pos = find_live_position_for_symbol(symbol)
                            if pos:
                                ticket = pos.ticket
                        except Exception as e:
                            send_info(f"[WARN] Fallback find_live_position failed: {e}")

                    if not ticket:
                        safe_telegram(f"⚠️ ORDER PLACED {symbol} {side.upper()} but FAILED to find ticket. SL/TP not set.")
                        send_info(f"[ORDER FAIL] Order opened but could not get ticket. Result: {result}")
                        continue 

                    # Step 2: Now that order is open, modify it to add SL/TP
                    modify_success = modify_position_sltp(ticket, sl, tp)

                    # Log and store the trade regardless of SL/TP modification
                    trade_id = log_pending_trade(strategy, side, reason, zone, entry, sl, tp, lot, symbol=symbol, trade_id=ticket)
                    active_trades_by_symbol[symbol] = {
                        'side': side, 'ticket': ticket, 'trade_id': trade_id,
                        'confidence': confidence, 'ts': time_module.time(),
                        'entry_price': entry, 'sl': sl 
                    }

                    # --- VIX75 UPGRADE: Clean "Order Placed" message ---
                    if modify_success:
                        safe_telegram(f"✅ ORDER PLACED: {symbol} {side.upper()} | TKT: {ticket} | Lot: {lot:.2f} | Conf: {confidence:.2f}")
                    else:
                        safe_telegram(f"⚠️ ORDER PLACED: {symbol} {side.upper()} | TKT: {ticket} | ❌ FAILED TO SET SL/TP")

                    # Clear CRT cache for this symbol
                    keys_to_remove = [k for k in _last_crt_alerts.keys() if k.startswith(f"{symbol}:")]
                    for k in keys_to_remove:
                        _last_crt_alerts.pop(k, None)

                else:
                    # The initial order placement failed
                    safe_telegram(f"❌ Order Failed {symbol} {side.upper()} conf:{confidence:.2f} result:{result}")
                    send_info(f"[ORDER FAIL] result: {result}")
                    
        except Exception as e:
            send_info(f"[EXCEPTION] processing signal {sig}: {e}\n{traceback.format_exc()}")
    # === END OF VIX75 UPGRADE 2 ===

    # --- trailing stop + housekeeping ---
    try:
        check_for_partial_tp(symbol)
    except Exception as e:
        send_info(f"[WARN] check_for_partial_tp failed: {e}")
        
    try:
        trail_sl(symbol, MAGIC)
    except Exception as e:
        send_info(f"[WARN] trail_sl failed: {e}")

    try:
        flush_rejected_signals_to_csv()
    except Exception as e:
        send_info(f"[WARN] failed to flush rejected signals: {e}")

    try:
        check_closed_trades(symbol)
    except Exception as e:
        send_info(f"[WARN] check_closed_trades failed: {e}")

    maybe_send_daily_summary()



# ============================
# (rest of file is unchanged)
# ============================

def _now_joburg():
    return datetime.now(TZ_JOBURG)


def maybe_send_daily_summary():
    global _last_summary_date_local, _last_summary_sent_ts
    now_local = _now_joburg()
    today_local = now_local.date()
    if _last_summary_date_local == today_local:
        return
    if now_local.hour == SUMMARY_HOUR and now_local.minute == SUMMARY_MINUTE:
        epoch_now = time_module.time()
        if epoch_now - _last_summary_sent_ts < 50:
            return
        try:
            send_daily_summary()
            _last_summary_date_local = today_local
            _last_summary_sent_ts = epoch_now
            send_info("[INFO] Daily summary sent.")
        except Exception as e:
            send_info(f"[WARN] Daily summary failed: {e}")


def _deal_is_exit(deal):
    """Return True if MT5 deal object represents an exit (close) leg."""
    try:
        entry = getattr(deal, 'entry', None)
        if entry is not None and hasattr(mt5, 'DEAL_ENTRY_OUT'):
            return entry == mt5.DEAL_ENTRY_OUT
    except Exception:
        pass
    try:
        profit = float(getattr(deal, 'profit', 0.0))
        return profit != 0.0
    except Exception:
        return False


def check_closed_trades(symbol, lookback_days=2):
    """Fetch recent MT5 history and update CSV for trades we know about."""
    global tp1_hit_tickets
    
    try:
        if not mt5_init_if_needed():
            return

        now = datetime.now()
        start = now - timedelta(days=lookback_days)
        deals = mt5.history_deals_get(start, now)
        if not deals:
            return

        ticket_map = {}
        for sym, rec in active_trades_by_symbol.items():
            t = rec.get('ticket')
            if t:
                ticket_map[t] = (sym, rec)

        for deal in deals:
            try:
                deal_id = getattr(deal, 'ticket', None) or getattr(deal, 'deal', None)
                order_ticket = getattr(deal, 'order', None)
                pos_id = getattr(deal,'position_id', None)

                candidate_ticket = None
                if order_ticket in ticket_map:
                    candidate_ticket = order_ticket
                elif pos_id in ticket_map:
                    candidate_ticket = pos_id

                if candidate_ticket is None:
                    continue

                key = (candidate_ticket, deal_id)
                if key in _seen_closed_pairs:
                    continue

                if not _deal_is_exit(deal):
                    continue

                sym, rec = ticket_map[candidate_ticket]
                trade_id = rec.get('trade_id')

                exit_price = float(getattr(deal, 'price', 0.0))
                exit_time_ts = int(getattr(deal, 'time', 0))
                exit_time = datetime.fromtimestamp(exit_time_ts, tz=timezone.utc)
                profit = float(getattr(deal, 'profit', 0.0))
                result_text = "win" if profit > 0 else ("loss" if profit < 0 else "breakeven")

                live_position = get_position_by_ticket(candidate_ticket)
                is_full_close = live_position is None

                if is_full_close:
                    update_trade_result(
                        trade_id=trade_id,
                        exit_price=exit_price,
                        exit_time=exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                        profit=profit,
                        result=result_text
                    )

                    _seen_closed_pairs.add(key)
                    active_trades_by_symbol.pop(sym, None)
                    tp1_hit_tickets.discard(candidate_ticket) 

                    emoji = "💰🟢" if profit > 0 else "🔻🔴" if profit < 0 else "😐"
                    safe_telegram(f"{emoji} {sym} closed | PnL: ${profit:.2f} | Price: {exit_price:.5f}")
                    
                    keys_to_remove = [k for k in _last_crt_alerts.keys() if k.startswith(f"{symbol}:")]
                    for k in keys_to_remove:
                        _last_crt_alerts.pop(k, None)
                    send_info(f"[CLOSED] {sym} ticket={candidate_ticket} pnl={profit:.2f}")
                else:
                    send_info(f"[PARTIAL] {sym} ticket={candidate_ticket} pnl={profit:.2f} (position still open)")
                    _seen_closed_pairs.add(key) 


            except Exception as inner:
                send_info(f"[WARN] processing deal failed: {inner}")

    except Exception as e:
        send_info(f"[WARN] check_closed_trades exception: {e}\n{traceback.format_exc()}")



# ============================
# CLI / Live runner
# ============================
if __name__ == "__main__":
    send_info(f"scalper_strategy_engine starting. DRY_RUN={DRY_RUN}")

    if not mt5_init_if_needed():
        send_info("[CRITICAL] MT5 connection failed on startup. Exiting.")
        safe_telegram("❌ Bot failed to connect to MT5 on startup. Please check credentials/server.")
        exit() 
        
    send_info("[INFO] MT5 connection successful.")

    try:
        load_open_trades_from_csv(path=TRADES_LOCAL_CSV)
    except Exception as e:
        send_info(f"[CRITICAL] Failed to load open trades state: {e}")
    
    send_startup_intro()
    time_module.sleep(2)   
    
    for sym in SYMBOLS:
        try:
            symbol = normalize_symbol(sym) 
            monitor_and_trade(symbol)
        except Exception as e:
            send_info(f"[ERROR] monitor_and_trade for {sym} failed: {e}\n{traceback.format_exc()}")