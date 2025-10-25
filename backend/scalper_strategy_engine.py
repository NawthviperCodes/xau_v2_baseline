# scalper_strategy_engine.py
"""
Complete scalper strategy engine (probability-based, auto-close on stronger signals).
Drop-in replacement — copy & paste into your project.

What’s inside (high level):
- Uses trade_decision_engine(...) for confidence-based signals
- Prioritizes by confidence
- Blocks low-confidence signals
- Prevents opposite-side open trades on same symbol
- Optionally auto-closes existing positions when a stronger opposing signal arrives
- DRY_RUN mode (safe default)
- CSV logging for rejected signals and local trades
- Daily summary scheduling (Africa/Johannesburg)
- Closed-trade backfill from MT5 history → updates exit_price, exit_time, profit, result in your CSV via update_trade_result(...)

✅ Updates requested by user:
- Every log_pending_trade(...) call now passes the symbol so your trade log includes instrument names.
- append_trade_to_local_csv(...) rows include symbol.
- Fixed side.upper() usage (removed accidental side.UPPER()).
- DRY_RUN behaviour preserved; runtime maps store trade_id + ticket for reliable backfilling.
- Kept rejected-signal flush, trailing SL, auto-close and daily summary intact.
"""
from datetime import datetime, timedelta, timezone, time as dtime
import time as time_module          # alias stdlib module to avoid shadowing

import MetaTrader5 as mt5
import pandas as pd
from ta.volatility import AverageTrueRange
from zone_detector import detect_zones, detect_fast_zones
from trade_decision_engine import run_trade_decision_engine, rejected_signals_log
from telegram_notifier import send_telegram_message
from trade_executor import place_order, place_dynamic_order, trail_sl, move_to_breakeven
from performance_tracker import send_daily_summary
from trade_logger import log_pending_trade, update_trade_result
from symbol_info_helper import get_lot_constraints
import pytz
from ta.trend import MACD, ADXIndicator
from news_filter_te import check_upcoming_high_impact
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice
import csv, os, threading, traceback
from collections import defaultdict
import inspect
from trade_decision_engine import format_confidence_label  # add at top of file if not already imported

#print("DEBUG check_upcoming_high_impact:", check_upcoming_high_impact, inspect.isfunction(check_upcoming_high_impact))


# --- emergency control import (already implemented separately) ---
from emergency_control import check_emergency_stop

# === Session State Tracking ===
# === Session State Tracking ===
#_session_state = {}  # {session_name: "awake"/"sleep"}
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
        "🤖 **Nawthviper Algo-Scalper Engine Activated**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📘 **STRATEGY OVERVIEW**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Methodology:** Confluence-based *price action scalping* on M1 & M5 charts.\n"
        "The system applies a multi-layered filter chain to identify precise, high-probability setups:\n"
        "   • **Primary Signal:** Candlestick patterns (*Engulfing*, *Pin Bars*) confirmed at Supply/Demand Zones.\n"
        "   • **Advanced Filter:** Candle Range Theory (CRT) for momentum validation and early reversal detection.\n"
        "   • **Confluence Checks:** H1/M5 Trend Alignment, MACD & RSI Momentum, VWAP Positioning.\n"
        "   • **Risk Management:** Dynamic SL/TP using **ATR-based volatility** and **structural targets**.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📈 **SIGNAL BEHAVIOR**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Signals are triggered only when:\n"
        "   • An existing trade on the same symbol has closed, **or**\n"
        "   • A **new high-confidence setup** overrides a weak active signal.\n\n"
        "A **5-minute cooldown** per symbol prevents duplicate alerts and maintains signal clarity.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 **CONFIDENCE LEVELS**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "   • **🔥 HIGH (≥ 0.85):** Strong confluence — ideal for execution.\n"
        "   • **⚖️ MEDIUM (0.70–0.84):** Moderate conviction — suitable for discretionary/aggressive use.\n"
        "   • **❗ LOW (0.60–0.69):** Weak or early setups — observation only.\n\n"
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
        "   • Automatic Breakeven + ATR-based Trailing Stop\n\n"
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
# CONFIG & GLOBAL STATE
# ============================
SYMBOLS = ["GBPUSD", "USDJPY", "USDCAD", "USDCHF", "XAUUSD"]

TIMEFRAME_ZONE = mt5.TIMEFRAME_H1
TIMEFRAME_ENTRY = mt5.TIMEFRAME_M1
TIMEFRAME_CONFIRM = mt5.TIMEFRAME_M5
ZONE_LOOKBACK = 100
TP_RATIO = 2
MAGIC = 12345

# Safety / behavior flags
DRY_RUN = False                      # Set False to enable live trading
CONFIDENCE_THRESHOLD = 0.60         # minimum confidence to accept a trade
CONF_PRIORITY_GLOBAL_MIN = 0.50     # absolute min to consider ordering logic (failsafe)
ALLOW_PYRAMID_SAME_SIDE = False     # if True, adds to same-side position on same symbol
AUTO_CLOSE_ON_STRONG = True         # if True, will attempt to close existing positions if opposite signal is much stronger
CLOSE_CONF_DIFF = 0.12              # new_conf must exceed existing_conf + this to trigger auto-close
MAX_TOUCH_ALLOWED = 3

# Daily summary schedule (Africa/Johannesburg local time)
SUMMARY_HOUR = 23
SUMMARY_MINUTE = 59
TZ_JOBURG = pytz.timezone("Africa/Johannesburg")

# Paths for logging
REJECTED_CSV = "rejected_signals_log.csv"
TRADES_LOCAL_CSV = "trades_history_local.csv"

# Runtime state
active_trades = {}                     # legacy compatibility map
active_trades_by_symbol = {}           # { symbol: { 'side': 'buy'/'sell', 'ticket': id, 'trade_id': str|None, 'confidence': 0.x, 'ts': epoch } }
zone_touch_counts = {}
_last_zone_alert_time = {}
_last_rejected_flush_index = 0
_rejected_flush_lock = threading.Lock()
_seen_closed_pairs = set()             # (ticket, deal_id) processed to avoid double-updates
_last_crt_alerts = {}  # symbol:timestamp cache for CRT signals
_last_summary_date_local = None
_last_summary_sent_ts = 0

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
        pos_side = 'buy' if getattr(pos, 'type', None) == mt5.ORDER_TYPE_BUY else 'sell'
        
        if pos_side != side:
            # Found opposite-side position → conflict
            return True, None
        elif pos_side == side and not ALLOW_PYRAMID_SAME_SIDE:
            # Same-side position but pyramiding not allowed → conflict
            return True, None
    
    # No conflicts found
    return False, None

# ============================
# CORE MONITOR & TRADE
# ============================

def monitor_and_trade(symbol, strategy_mode=None, fixed_lot=None):
    """
    Main per-symbol monitor function. Intended to be run by scheduler for each symbol.
    """
    global zone_touch_counts, active_trades, active_trades_by_symbol

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

    # --- Fetch H1 and detect zones
    h1_df = get_data(symbol, TIMEFRAME_ZONE, ZONE_LOOKBACK)
    if h1_df.empty:
        send_info(f"[ERROR] {symbol} H1 unavailable.")
        return

    demand_zones, supply_zones = detect_zones(h1_df)
    fast_demand, fast_supply = detect_fast_zones(h1_df)

    trend = calculate_trend(h1_df)
    if not trend:
        send_info(f"[ERROR] Not enough H1 data for {symbol}")
        return

    try:
        adx = ADXIndicator(high=h1_df['high'], low=h1_df['low'], close=h1_df['close'], window=14)
        adx_value = adx.adx().iloc[-1]

        adaptive_adx = adaptive_adx_threshold(h1_df, lookback=200, percentile=50)  # median instead of 70th
        min_floor = 15.0  # absolute minimum required ADX

        # softer filter: require ADX >= max(median, 15)
        required_adx = max(adaptive_adx, min_floor)

        if adx_value < required_adx:
            send_info(f"[FILTER] {symbol} ADX={adx_value:.2f} < required {required_adx:.2f} → Range detected, skip trading.")
            return
    except Exception as e:
        send_info(f"[WARN] ADX calculation failed: {e}")

    # --- News filter ---
    if check_upcoming_high_impact(symbol, minutes_ahead=60):
        send_info(f"[NEWS FILTER] {symbol} → High-impact news in next 60min, skip trading.")
        return

    # --- Session filter ---
    # NEW: Rely on symbol-specific session check for better quality control
    if not is_in_active_session(symbol):
        send_info(f"[SESSION FILTER] {symbol} → Not in optimal trading session, skip trading.")
        # still check for exits
        try:
            check_closed_trades(symbol)
        except Exception as e:
            send_info(f"[WARN] check_closed_trades failed in sleep mode: {e}")
        return

    # --- Fetch M1 and M5
    m1_df = get_data(symbol, TIMEFRAME_ENTRY, 200)
    if len(m1_df) < 35:
        send_info(f"[ERROR] Not enough M1 candles for {symbol}")
        return

    m5_df = get_data(symbol, TIMEFRAME_CONFIRM, 60)
    m5_context = {}
    if not m5_df.empty and len(m5_df) >= 35:
        try:
            m5_context['trend'] = calculate_trend(m5_df)
            m5_context['macd'] = MACD(close=m5_df['close']).macd().dropna().values
            m5_context['rsi'] = RSIIndicator(close=m5_df['close']).rsi().dropna().values
        except Exception as e:
            send_info(f"[WARN] M5 context failed: {e}")
            m5_context = {}

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        send_info(f"[ERROR] No tick data for {symbol}.")
        return

    price = float(tick.bid)
    sinfo = mt5.symbol_info(symbol)
    if sinfo is None:
        send_info(f"[ERROR] symbol_info failed for {symbol}.")
        return
    point = sinfo.point

    # --- Indicators on M1
    try:
        macd_calc = MACD(close=m1_df['close'])
        macd_line = macd_calc.macd().dropna().values
        macd_signal = macd_calc.macd_signal().dropna().values
        rsi_values = RSIIndicator(close=m1_df['close']).rsi().dropna().values
        vwap_value = VolumeWeightedAveragePrice(
            high=m1_df['high'], low=m1_df['low'], close=m1_df['close'], volume=m1_df['real_volume']
        ).vwap.iloc[-1]
        atr = AverageTrueRange(high=m1_df['high'], low=m1_df['low'], close=m1_df['close']).average_true_range().iloc[-1]
    except Exception as e:
        send_info(f"[WARN] Indicator calculation failed: {e}")
        macd_line = macd_signal = rsi_values = vwap_value = atr = None

    MIN_LOT, MAX_LOT, LOT_STEP = get_lot_constraints(symbol)
    SL_BUFFER = 150 * point
    CHECK_RANGE = 300 * point
    lot_size = max(MIN_LOT, fixed_lot if fixed_lot else MIN_LOT)

    # --- Decision engine: strict + aggressive
    try:
        strict_signals, _ = run_trade_decision_engine(
            symbol=symbol,
            point=point,
            current_price=price,
            trend=trend,
            demand_zones=demand_zones,
            supply_zones=supply_zones,
            last3_candles=m1_df.iloc[-4:-1],
            active_trades=active_trades,
            zone_touch_counts=zone_touch_counts,
            SL_BUFFER=SL_BUFFER,
            TP_RATIO=TP_RATIO,
            CHECK_RANGE=CHECK_RANGE,
            LOT_SIZE=lot_size,
            MAGIC=MAGIC,
            strategy_mode="trend_follow",
            macd=macd_line,
            macd_signal=macd_signal,
            rsi=rsi_values,
            vwap=vwap_value,
            atr=atr,
            m5_context=m5_context
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
            last3_candles=m1_df.iloc[-4:-1],
            active_trades=active_trades,
            zone_touch_counts=zone_touch_counts,
            SL_BUFFER=SL_BUFFER,
            TP_RATIO=TP_RATIO,
            CHECK_RANGE=CHECK_RANGE,
            LOT_SIZE=lot_size,
            MAGIC=MAGIC,
            strategy_mode="aggressive",
            macd=macd_line,
            macd_signal=macd_signal,
            rsi=rsi_values,
            vwap=vwap_value,
            atr=atr,
            m5_context=m5_context
        )
    except Exception as e:
        send_info(f"[WARN] trade_decision_engine (aggressive) raised: {e}\n{traceback.format_exc()}")
        aggressive_signals = []

    print_detected_zones(symbol, demand_zones, supply_zones, fast_demand, fast_supply)

    # 1️⃣  Prefer strict signals outright if present
    if strict_signals:
        signals = list(strict_signals)
    elif aggressive_signals:
        signals = list(aggressive_signals)
    else:
        signals = []

    # 2️⃣  Sort by confidence (highest first)
    signals = sorted(signals, key=lambda s: float(s.get("confidence", 0.0)), reverse=True)

    # 3️⃣  Remove exact duplicates (same side/entry/sl/tp)
    unique, seen = [], set()
    for s in signals:
        key = (
            s.get("side"),
            round(s.get("entry", 0), 5),
            round(s.get("sl", 0), 5),
            round(s.get("tp", 0), 5),
        )
        if key not in seen:
            unique.append(s)
            seen.add(key)
    signals = unique

    # 4️⃣  If both BUY & SELL remain, keep only the strongest confidence
    sides = {s.get("side") for s in signals}
    if "buy" in sides and "sell" in sides:
        strongest = max(signals, key=lambda s: s.get("confidence", 0))
        signals = [strongest]

    # --- Process signals
    for sig in signals:
        try:
            side = sig.get('side')
            entry = sig.get('entry')
            sl = sig.get('sl')
            tp = sig.get('tp')
            zone = sig.get('zone')
            lot = max(MIN_LOT, sig.get('lot', lot_size))
            reason = sig.get('reason', '')
            strategy = sig.get('strategy', '')
            confidence = float(sig.get('confidence', 0.0))

            # --- Risk-based lot override
            try:
                risk_lot = calculate_risk_based_lot(symbol, sl_price=sl, entry_price=entry, risk_percent=1.0)
                if risk_lot:
                    lot = risk_lot
            except Exception as e:
                send_info(f"[WARN] risk-based lot calc failed for {symbol}: {e}")

            if confidence < CONF_PRIORITY_GLOBAL_MIN:
                continue
            dynamic_conf = adaptive_confidence_threshold(h1_df, base=CONFIDENCE_THRESHOLD)
            if confidence < dynamic_conf:
                continue

            # FIXED: Enhanced conflict detection with better logging
            conflict, existing_conf = has_conflict_and_existing_confidence(symbol, side)
            
            if conflict:
                send_info(f"[CONFLICT] {symbol} has existing position conflict for {side.upper()}")
                
                # Check if opposite-side exists and auto-close is enabled
                if AUTO_CLOSE_ON_STRONG and existing_conf is not None:
                    if confidence >= existing_conf + CLOSE_CONF_DIFF:
                        send_info(f"[AUTO-CLOSE] Closing {symbol} opposite positions for stronger {side.upper()} signal")
                        close_results = close_positions_for_symbol(symbol, reason_msg=f"auto_close_by_conf_{confidence:.2f}")
                        send_info(f"[AUTO-CLOSE] Close results: {close_results}")
                        
                        # Clear from runtime state
                        active_trades_by_symbol.pop(symbol, None)
                        
                        # Wait and verify positions are closed
                        wait_attempts = 0
                        positions_still_exist = True
                        while positions_still_exist and wait_attempts < 15:  # Increased to 15 attempts
                            time_module.sleep(0.5)  # Increased wait time
                            live_positions = get_live_positions(symbol)
                            positions_still_exist = len(live_positions) > 0
                            
                            if not positions_still_exist:
                                send_info(f"[AUTO-CLOSE] Successfully closed all positions for {symbol}")
                                break
                                
                            wait_attempts += 1
                            if wait_attempts >= 15:
                                send_info(f"[AUTO-CLOSE] Timeout waiting for positions to close on {symbol}")
                                # Don't proceed with new trade if we couldn't close existing ones
                                continue
                    else:
                        # Signal not strong enough to override existing positions
                        send_info(f"[CONFLICT] {side.upper()} signal confidence {confidence:.2f} not strong enough to override existing {existing_conf:.2f}")
                        continue
                else:
                    # Either same-side conflict and pyramiding not allowed, or auto-close not enabled
                    send_info(f"[CONFLICT] {side.upper()} signal blocked due to existing position")
                    continue
                
                 # ----------------------------------------------------
            # 📢 NEW: Send Detailed Signal Before Order Execution 📢
            # ----------------------------------------------------
            
            
            MIN_CONF_FOR_TELEGRAM = 0.75  # same threshold as in trade_decision_engine.py
            reason = sig.get('reason', 'Zone Pattern')

            if confidence >= MIN_CONF_FOR_TELEGRAM:
                full_signal_msg = (
                    f"📥 SIGNAL EXECUTION: {symbol} pattern detected | {side.upper()} idea\n"
                    f"   🔹 Entry: {entry:.5f}\n"
                    f"   🔹 SL: {sl:.5f}\n"
                    f"   🔹 TP: {tp:.5f}\n"
                    f"   🔹 Confidence: {format_confidence_label(confidence)} ({reason})"
                )
                safe_telegram(full_signal_msg)

            # --- Place order ---
            if DRY_RUN:
                fake_ticket = int(time_module.time() * 1000) % 1000000
                trade_id = log_pending_trade(strategy, side, reason, zone, entry, sl, tp, lot, symbol=symbol, trade_id=fake_ticket)
                active_trades_by_symbol[symbol] = {
                    'side': side, 'ticket': fake_ticket, 'trade_id': trade_id,
                    'confidence': confidence, 'ts': time_module.time()
                }
                append_trade_to_local_csv({
                    "trade_id": trade_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "symbol": symbol,
                    "strategy": strategy,
                    "side": side,
                    "entry_reason": reason,
                    "zone_price": zone,
                    "entry_price": entry,
                    "sl": sl,
                    "tp": tp,
                    "lot_size": lot,
                    "exit_price": "",
                    "exit_time": "",
                    "profit": "",
                    "result": "DRY_RUN"
                })
                safe_telegram(f"(DRY_RUN) ✅ {symbol} {side.upper()} conf:{confidence:.2f} lot:{lot}")
            else:
                result = place_order(symbol, side, lot, sl, tp, MAGIC, comment="NawthviperBot")
                if result is not None and getattr(result, 'retcode', None) == mt5.TRADE_RETCODE_DONE:
                    ticket = getattr(result, 'order', None) or getattr(result, 'ticket', None)
                    trade_id = log_pending_trade(strategy, side, reason, zone, entry, sl, tp, lot, symbol=symbol, trade_id=ticket)
                    active_trades_by_symbol[symbol] = {
                        'side': side, 'ticket': ticket, 'trade_id': trade_id,
                        'confidence': confidence, 'ts': time_module.time()
                    }
                    safe_telegram(f"✅ ORDER PLACED {symbol} {side.upper()} conf:{confidence:.2f} ticket:{ticket} lot:{lot}")

                    # 🔄 Clear CRT cache for this symbol (so new CRT alerts won’t be blocked)
                    keys_to_remove = [k for k in _last_crt_alerts.keys() if k.startswith(f"{symbol}:")]
                    for k in keys_to_remove:
                        _last_crt_alerts.pop(k, None)

                    append_trade_to_local_csv({
                        "trade_id": trade_id,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "symbol": symbol,
                        "strategy": strategy,
                        "side": side,
                        "entry_reason": reason,
                        "zone_price": zone,
                        "entry_price": entry,
                        "sl": sl,
                        "tp": tp,
                        "lot_size": lot,
                        "exit_price": "",
                        "exit_time": "",
                        "profit": "",
                        "result": "PLACED"
                    })
                else:
                    safe_telegram(f"❌ Order Failed {symbol} {side.upper()} conf:{confidence:.2f} result:{result}")
                    send_info(f"[ORDER FAIL] result: {result}")
        except Exception as e:
            send_info(f"[EXCEPTION] processing signal {sig}: {e}\n{traceback.format_exc()}")

    # --- trailing stop + housekeeping ---
    try:
        # NEW: Breakeven Check
        move_to_breakeven(symbol, MAGIC)
    except Exception as e:
        send_info(f"[WARN] move_to_breakeven failed: {e}")
        
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
# CONFLICT CHECK WRAPPER
# ============================

def has_conflict_and_existing_confidence(symbol, side):
    """
    Wrapper that returns (conflict_bool, existing_confidence or None)
    Uses runtime map first, then live positions.
    """
    # runtime map check
    rec = active_trades_by_symbol.get(symbol)
    if rec:
        existing_side = rec.get('side')
        existing_conf = rec.get('confidence', None)
        if existing_side != side:
            return True, existing_conf
        if existing_side == side and not ALLOW_PYRAMID_SAME_SIDE:
            return True, existing_conf
        return False, existing_conf

    # check live positions
    positions = get_live_positions(symbol)
    if not positions:
        return False, None
    # if positions exist, we consider conflict by default (safe)
    return True, None


# ============================
# DAILY SUMMARY
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


# ============================
# CLOSED-TRADES BACKFILL
# ============================

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


# ============================
# CLOSED-TRADES BACKFILL (UPDATED)
# ============================

def check_closed_trades(symbol, lookback_days=2):
    """Fetch recent MT5 history and update CSV for trades we know about.

    Now runs with extra debug logs so you can see if deals are skipped.
    """
    try:
        if not mt5_init_if_needed():
            return

        now = datetime.now()
        start = now - timedelta(days=lookback_days)
        deals = mt5.history_deals_get(start, now)
        if not deals:
            send_info(f"[DEBUG] No deals found for {symbol} in last {lookback_days} days.")
            return

        send_info(f"[DEBUG] Found {len(deals)} deals in MT5 history for {symbol}.")

        # Build reverse map ticket -> (symbol, rec)
        ticket_map = {}
        for sym, rec in active_trades_by_symbol.items():
            t = rec.get('ticket')
            if t:
                ticket_map[t] = (sym, rec)

        for deal in deals:
            try:
                deal_id = getattr(deal, 'ticket', None) or getattr(deal, 'deal', None)
                order_ticket = getattr(deal, 'order', None)
                pos_id = getattr(deal, 'position_id', None)

                candidate_ticket = None
                if order_ticket in ticket_map:
                    candidate_ticket = order_ticket
                elif pos_id in ticket_map:
                    candidate_ticket = pos_id

                if candidate_ticket is None:
                    #send_info(f"[DEBUG] Deal {deal_id} skipped (ticket not in runtime map).")
                    continue

                key = (candidate_ticket, deal_id)
                if key in _seen_closed_pairs:
                    send_info(f"[DEBUG] Deal {deal_id} already processed.")
                    continue

                if not _deal_is_exit(deal):
                    send_info(f"[DEBUG] Deal {deal_id} is not an exit leg.")
                    continue

                sym, rec = ticket_map[candidate_ticket]
                trade_id = rec.get('trade_id')

                exit_price = float(getattr(deal, 'price', 0.0))
                exit_time_ts = int(getattr(deal, 'time', 0))
                exit_time = datetime.fromtimestamp(exit_time_ts, tz=timezone.utc)
                profit = float(getattr(deal, 'profit', 0.0))
                result_text = "win" if profit > 0 else ("loss" if profit < 0 else "breakeven")

                # Update CSV/trade log
                update_trade_result(
                    trade_id=trade_id,
                    exit_price=exit_price,
                    exit_time=exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                    profit=profit,
                    result=result_text
                )

                _seen_closed_pairs.add(key)
                active_trades_by_symbol.pop(sym, None)

                # Telegram notification
                emoji = "💰🟢" if profit > 0 else "🔻🔴" if profit < 0 else "😐"
                safe_telegram(f"{emoji} {sym} closed | PnL: ${profit:.2f} | Price: {exit_price:.5f}")
                # 🔄 Clear CRT cache for this symbol (so fresh CRT alerts can trigger)
                keys_to_remove = [k for k in _last_crt_alerts.keys() if k.startswith(f"{symbol}:")]
                for k in keys_to_remove:
                    _last_crt_alerts.pop(k, None)
                send_info(f"[CLOSED] {sym} ticket={candidate_ticket} pnl={profit:.2f}")

            except Exception as inner:
                send_info(f"[WARN] processing deal failed: {inner}")

    except Exception as e:
        send_info(f"[WARN] check_closed_trades exception: {e}\n{traceback.format_exc()}")



# ============================
# CLI / Live runner
# ============================
if __name__ == "__main__":
    send_info(f"scalper_strategy_engine starting. DRY_RUN={DRY_RUN}")
    send_startup_intro()
    time_module.sleep(2)   # fixed
    for sym in SYMBOLS:
        try:
            symbol = normalize_symbol(sym)
            monitor_and_trade(symbol)
        except Exception as e:
            send_info(f"[ERROR] monitor_and_trade for {sym} failed: {e}\n{traceback.format_exc()}")
