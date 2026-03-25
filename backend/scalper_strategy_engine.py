# ======================================================
# === scalper_strategy_engine.py (Production Sniper) ===
# ======================================================
# 
# ✅ ARCHITECTURE: Thread-Safe Parallel Worker
<<<<<<< HEAD
# ✅ SAFETY 1: Daily Circuit Breaker (Stop after 2 losses)
# ✅ SAFETY 2: Daily Candle Filter (Trend Alignment)
# ✅ SAFETY 3: Time Session Filter (London/NY Only)
# ✅ SAFETY 4: ADR Filter (Context Aware - No longer Global Block)
=======
# ✅ LOGIC: Smart Lot Sizing (User Override > Risk Fallback)
# ✅ SAFETY 1: Daily Circuit Breaker (Stop after 3 losses)
# ❌ REMOVED: Daily Candle Filter (was blocking valid zone reversals)
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
#
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time as time_module
import json
import threading
import traceback
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from trade_decision_engine import print_rejection_summary

PRINT_LOCK = Lock()

# --- Custom Modules ---
from ta.volatility import AverageTrueRange
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice

# High-Performance Modules
from zone_detector import detect_zones, detect_fast_zones 
from news_filter_te import start_news_thread, check_upcoming_high_impact 
from trade_executor import (
    place_order, 
    modify_position_sltp, 
    trail_sl, # Imported from trade_executor
    close_partial_and_move_sl_to_be, 
    close_positions_for_symbol,
    EXECUTION_LOCK
)
from trade_decision_engine import (
    run_trade_decision_engine, 
    format_confidence_label
)
<<<<<<< HEAD
=======
from performance_tracker import get_dynamic_risk, detect_market_regime, print_performance_summary, log_trade
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
from telegram_notifier import send_telegram_message

# ============================
# === CONFIGURATION LOADER ===
# ============================

def load_config(path='config.json'):
    try:
        with open(path, 'r') as f:
            config = json.load(f)
        
        TIMEFRAME_MAP = {
            "TIMEFRAME_M1": mt5.TIMEFRAME_M1,
            "TIMEFRAME_M5": mt5.TIMEFRAME_M5,
            "TIMEFRAME_M15": mt5.TIMEFRAME_M15,
            "TIMEFRAME_H1": mt5.TIMEFRAME_H1,
            "TIMEFRAME_H4": mt5.TIMEFRAME_H4,
        }
        
        config['StrategyParameters']['TIMEFRAME_ZONE'] = TIMEFRAME_MAP[config['StrategyParameters']['TIMEFRAME_ZONE']]
        config['StrategyParameters']['TIMEFRAME_ENTRY'] = TIMEFRAME_MAP[config['StrategyParameters']['TIMEFRAME_ENTRY']]
        config['StrategyParameters']['TIMEFRAME_CONFIRM'] = TIMEFRAME_MAP[config['StrategyParameters']['TIMEFRAME_CONFIRM']]
        
        tf_htf_str = config['StrategyParameters'].get('TIMEFRAME_HTF', "TIMEFRAME_H4")
        config['StrategyParameters']['TIMEFRAME_HTF'] = TIMEFRAME_MAP.get(tf_htf_str, mt5.TIMEFRAME_H4)

        return config
    except Exception as e:
        print(f"[CRITICAL] Config Load Failed: {e}")
        exit()

DECISION_STATS = {
    "cycles": 0,
    "htf_neutral_blocks": 0,
    "no_zones_found": 0,
    "price_not_in_zone": 0,
    "news_blocked": 0,
    "cooldown_blocked": 0,
<<<<<<< HEAD
    "daily_filter_blocked": 0,
    "circuit_breaker_blocked": 0,
    "session_blocked": 0,      # New Stat
    "adr_exhaustion_blocked": 0, # Legacy Stat (Should stay 0 now)
=======
    "daily_filter_blocked": 0, # New Stat
    "circuit_breaker_blocked": 0, # New Stat
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
    "signals_generated": 0,
    "signals_executed": 0,
}

ZONE_TOUCH_STATS = {
    "demand_touches": 0,
    "supply_touches": 0,
}

CONFIG = load_config('config.json')

# --- Global Settings ---
SYMBOLS = CONFIG['BotSettings']['SYMBOLS']
MAGIC = CONFIG['BotSettings']['MAGIC']
DRY_RUN = CONFIG['BotSettings']['DRY_RUN']

TIMEFRAME_ZONE = CONFIG['StrategyParameters']['TIMEFRAME_ZONE']
TIMEFRAME_ENTRY = CONFIG['StrategyParameters']['TIMEFRAME_ENTRY']
TIMEFRAME_CONFIRM = CONFIG['StrategyParameters']['TIMEFRAME_CONFIRM']
TIMEFRAME_HTF = CONFIG['StrategyParameters']['TIMEFRAME_HTF']
ZONE_LOOKBACK = CONFIG['StrategyParameters']['ZONE_LOOKBACK']
TP_RATIO = CONFIG['StrategyParameters']['TP_RATIO']
PARTIAL_CLOSE_PERCENT = CONFIG['StrategyParameters']['PARTIAL_CLOSE_PERCENT']
AUTO_CLOSE_ON_STRONG = CONFIG['StrategyParameters']['AUTO_CLOSE_ON_STRONG']

THRESHOLDS = CONFIG['StrategyParameters'].get('Thresholds', {})
<<<<<<< HEAD
CONFIDENCE_THRESHOLD = THRESHOLDS.get('MIN_CONFIDENCE_FOR_TRADE', 0.65) # UPDATED TO SNIPER LEVEL
=======
# Inject MAX_TOUCH_ALLOWED so decision engine can read it from the thresholds dict
THRESHOLDS['MAX_TOUCH_ALLOWED'] = CONFIG['StrategyParameters'].get('MAX_TOUCH_ALLOWED', 2)
CONFIDENCE_THRESHOLD = THRESHOLDS.get('MIN_CONFIDENCE_FOR_TRADE', 0.60)
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
MIN_CONF_FOR_TELEGRAM = THRESHOLDS.get('MIN_CONF_FOR_TELEGRAM', 0.75)

# ============================
# === STATE & CACHING ===
# ============================

SYMBOL_SPECS = {} 
tp1_hit_tickets = set()
_last_closure_time = {} 
COOLDOWN_MINUTES = 15
<<<<<<< HEAD
MAX_DAILY_CONSECUTIVE_LOSSES = 2 # SNIPER SETTING (Tighter leash)

# SNIPER CONSTANTS
SESSION_START_HOUR = 8  # London Open
SESSION_END_HOUR = 20   # NY Close
# ADR_THRESHOLD_PCT = 0.85 # MOVED TO DECISION ENGINE LOGIC
=======
MAX_DAILY_CONSECUTIVE_LOSSES = 3 # Hard Limit

# 🧠 LEARNING LAYER STATE
# Maps position ticket → original signal dict so we can log results when trade closes
_pending_signals = {}
# Tracks deal tickets already logged to prevent double-counting
_logged_deal_tickets = set()
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)

def get_symbol_spec(symbol):
    if symbol not in SYMBOL_SPECS:
        info = mt5.symbol_info(symbol)
        if info:
            SYMBOL_SPECS[symbol] = info
    return SYMBOL_SPECS.get(symbol)

def safe_telegram(msg):
    try:
        threading.Thread(target=send_telegram_message, args=(msg,)).start()
    except:
        pass

def send_info(msg):
    print(f"[ENGINE] {datetime.now().strftime('%H:%M:%S')} {msg}")

# ============================
# === DATA & LOGIC HELPERS ===
# ============================

def get_data(symbol, timeframe, bars):
    try:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        if rates is None or len(rates) == 0: return pd.DataFrame()
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except Exception:
        return pd.DataFrame()

def calculate_trend(df):
    if df.empty or len(df) < 51: return None
    sma50 = df['close'].rolling(50).mean().iloc[-1]
    last = df['close'].iloc[-1]
    return "uptrend" if last > sma50 else "downtrend"

def get_htf_bias(df):
    if df.empty or len(df) < 200: return "NEUTRAL"
    ema_fast = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
    ema_slow = df['close'].ewm(span=200, adjust=False).mean().iloc[-1]
    if ema_fast > ema_slow: return "UP"
    if ema_fast < ema_slow: return "DOWN"
    return "NEUTRAL"

<<<<<<< HEAD
# --- 🛡️ SAFETY MODULES ---

def check_daily_circuit_breaker(symbol):
    try:
        now = datetime.now()
        start_of_day = datetime(now.year, now.month, now.day)
        deals = mt5.history_deals_get(start_of_day, now, group=symbol)
        if deals is None or len(deals) == 0: return False
            
        consecutive_losses = 0
        for deal in reversed(deals):
            if deal.magic != MAGIC: continue
            if deal.entry != mt5.DEAL_ENTRY_OUT: continue 
            
            if deal.profit < 0: consecutive_losses += 1
            elif deal.profit > 0: 
                consecutive_losses = 0 
                break 
        
        return consecutive_losses >= MAX_DAILY_CONSECUTIVE_LOSSES
    except Exception:
        return False

def get_daily_candle_direction(symbol):
    try:
        # Get TODAY's candle
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 1)
        if rates is None or len(rates) == 0: return 'neutral'
        
        open_p = rates[0]['open']
        current_p = mt5.symbol_info_tick(symbol).bid
        
        if current_p > open_p: return 'buy'
        if current_p < open_p: return 'sell'
        return 'neutral'
    except:
        return 'neutral'

def get_adr_percentage(symbol):
    """
    Calculates how much of the ADR has been consumed today.
    Returns: float (e.g., 0.85 for 85%)
    """
    try:
        # Get last 14 Daily candles for ADR calc
        rates_d1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 15)
        if rates_d1 is None or len(rates_d1) < 14: return 0.0 # Not enough data
        
        df_d1 = pd.DataFrame(rates_d1)
        # Calculate ATR(14) manually or approx
        df_d1['tr'] = np.maximum(df_d1['high'] - df_d1['low'], 
                                 np.abs(df_d1['high'] - df_d1['close'].shift(1)))
        adr = df_d1['tr'].rolling(14).mean().iloc[-1]
        
        # Get TODAY's range
        today = rates_d1[-1] # The last candle is the current unfinished daily candle
        current_range = today['high'] - today['low']
        
        if adr == 0: return 0.0
        return current_range / adr
    except:
        return 0.0

def check_session_time():
    """
    Returns True if within permitted trading hours (London/NY).
    """
    try:
        current_hour = datetime.now(timezone.utc).hour + 2 # Approx Server Time adjustment (adjust +2 or +3 as needed)
        # Alternatively, use MT5 time directly
        if len(SYMBOLS) > 0:
            tick = mt5.symbol_info_tick(SYMBOLS[0])
            if tick:
                server_hour = datetime.fromtimestamp(tick.time, timezone.utc).hour
                return SESSION_START_HOUR <= server_hour < SESSION_END_HOUR
        
        return True # Default to Open if time fetch fails
    except:
        return True 
=======
# --- 🛡️ SAFETY MODULE: CIRCUIT BREAKER ---
def check_daily_circuit_breaker(symbol):
    """
    Checks if we have hit 3 consecutive losses TODAY.
    Returns True if we should BLOCK trading.
    """
    try:
        # Get history for today
        now = datetime.now()
        start_of_day = datetime(now.year, now.month, now.day)
        
        deals = mt5.history_deals_get(start_of_day, now, group=symbol)
        if deals is None or len(deals) == 0:
            return False
            
        consecutive_losses = 0
        
        # Iterate backwards (newest first)
        for deal in reversed(deals):
            if deal.magic != MAGIC: continue
            if deal.entry != mt5.DEAL_ENTRY_OUT: continue # Only check exits
            
            profit = deal.profit
            if profit < 0:
                consecutive_losses += 1
            elif profit > 0:
                consecutive_losses = 0 # Reset on win
                break # We are safe
        
        if consecutive_losses >= MAX_DAILY_CONSECUTIVE_LOSSES:
            return True # BLOCK TRADING
            
        return False
    except Exception as e:
        print(f"Circuit Breaker Error: {e}")
        return False


# 🧠 LEARNING LAYER: Detect closed trades and feed results into performance memory
def check_and_log_closed_trades(symbol):
    """
    Polls MT5 deal history for today. For each closed exit deal that matches
    a signal we opened, logs the win/loss to trade_performance.json.

    Called once per cycle — lightweight, uses today-only history window.
    """
    try:
        now = datetime.now()
        start_of_day = datetime(now.year, now.month, now.day)

        deals = mt5.history_deals_get(start_of_day, now, group=symbol)
        if not deals:
            return

        for deal in deals:
            if deal.magic != MAGIC:               continue  # Not our bot
            if deal.entry != mt5.DEAL_ENTRY_OUT:  continue  # Only exits
            if deal.ticket in _logged_deal_tickets: continue  # Already logged

            # Match deal back to the signal we stored at open time
            position_ticket = deal.position_id
            signal = _pending_signals.get(position_ticket)

            if signal is None:
                continue  # Trade not opened by this session — skip

            result = "win" if deal.profit >= 0 else "loss"
            log_trade(signal, result)

            _logged_deal_tickets.add(deal.ticket)
            _pending_signals.pop(position_ticket, None)  # Clean up memory

            send_info(f"🧠 Logged: {symbol} {signal.get('reason')} "
                      f"[{signal.get('strategy')}] → {result.upper()} (${deal.profit:.2f})")
    except Exception as e:
        send_info(f"[LogClosed] Error for {symbol}: {e}")

>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)

def determine_lot_size(symbol, sl_price, entry_price, fixed_lot, strategy_mode):
    info = get_symbol_spec(symbol)
    if not info: return 0.01

    if fixed_lot and float(fixed_lot) > 0:
        return float(fixed_lot)

    risk_percent = 1.0 
    if strategy_mode == "aggressive": risk_percent = 2.0
    elif strategy_mode == "conservative": risk_percent = 0.5
    elif strategy_mode == "momentum_continuation_L2": risk_percent = 0.4
<<<<<<< HEAD
=======
    
    # 🧠 ADAPTIVE: Scale risk up/down based on strategy's live win rate
    # Neutral until 20 trades logged. Then: hot streak → 1.5x, cold → 0.5x
    dynamic_multiplier = get_dynamic_risk(strategy_mode)
    risk_percent = risk_percent * dynamic_multiplier
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
    
    try:
        acc = mt5.account_info()
        if not acc: return info.volume_min
        
        equity = acc.equity
        risk_amt = equity * (risk_percent / 100.0)
        dist = abs(entry_price - sl_price)
        
        if dist == 0 or info.trade_tick_value == 0: return info.volume_min
        
<<<<<<< HEAD
        # Calculate raw lots based on risk
=======
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
        ticks = dist / info.trade_tick_size
        loss_per_lot = ticks * info.trade_tick_value
        if loss_per_lot <= 0: return info.volume_min
        
        lots = risk_amt / loss_per_lot
<<<<<<< HEAD
        
        # --- 🔧 FIX STARTS HERE 🔧 ---
=======
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
        step = info.volume_step
        
        # 1. Quantize to step
        lots = round(lots / step) * step
        
        # 2. CLEAN THE FLOAT (Crucial Step)
        # Calculate how many decimals the step has (e.g., 0.1 has 1, 0.01 has 2)
        import math
        decimals = 0
        if step < 1:
            decimals = int(math.ceil(-math.log10(step)))
            
        # Hard rounding to remove floating point noise like 0.1000000001
        lots = round(lots, decimals)
        # --- 🔧 FIX ENDS HERE 🔧 ---

        return max(info.volume_min, min(info.volume_max, lots))
    except:
        return info.volume_min

# ============================
# === LIVE STATE MANAGEMENT ===
# ============================

def check_for_partial_tp_live(symbol):
    """
    Monitors live positions to trigger Partial Close when 1R is hit.
    """
    try:
        positions = mt5.positions_get(symbol=symbol)
        if not positions: return

        for pos in positions:
            if pos.magic != MAGIC: continue
            if pos.ticket in tp1_hit_tickets: continue
            
            is_buy = pos.type == mt5.ORDER_TYPE_BUY
            entry, sl = pos.price_open, pos.sl
            
<<<<<<< HEAD
            # Check if already secured (SL moved to Entry)
=======
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
            if (is_buy and sl >= entry) or (not is_buy and sl > 0 and sl <= entry):
                tp1_hit_tickets.add(pos.ticket)
                continue
            
            if sl == 0: continue
            risk = abs(entry - sl)
            target = (entry + risk) if is_buy else (entry - risk)
            
            tick = mt5.symbol_info_tick(symbol)
            if not tick: continue
            curr = tick.bid if is_buy else tick.ask
            
            hit = (curr >= target) if is_buy else (curr <= target)
            if hit:
                send_info(f"💰 {symbol} Ticket {pos.ticket} hit 1R. Securing...")
                if not DRY_RUN:
                    if close_partial_and_move_sl_to_be(pos.ticket, PARTIAL_CLOSE_PERCENT):
                        tp1_hit_tickets.add(pos.ticket)
                        safe_telegram(f"💰 {symbol} 1R Secured!")
    except: pass

# ============================
# === MAIN WORKER ===
# ============================

def process_symbol_cycle(symbol, strategy_mode="standard", fixed_lot=None):
    try:
        DECISION_STATS["cycles"] += 1
<<<<<<< HEAD
        
        # 1. Housekeeping
        trail_sl(symbol, MAGIC) 
        check_for_partial_tp_live(symbol) 
        
=======
        trail_sl(symbol, MAGIC)
        check_for_partial_tp_live(symbol)
        check_and_log_closed_trades(symbol)  # 🧠 Log any newly closed trades
        
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
        if check_upcoming_high_impact(symbol):
            DECISION_STATS["news_blocked"] += 1
            return

<<<<<<< HEAD
        # 2. CIRCUIT BREAKER
        if check_daily_circuit_breaker(symbol):
            DECISION_STATS["circuit_breaker_blocked"] += 1
            return

        # 3. SESSION TIME FILTER (New Sniper Logic)
        if not check_session_time():
            DECISION_STATS["session_blocked"] += 1
=======
        # --- 🛡️ SAFETY CHECK 1: CIRCUIT BREAKER ---
        if check_daily_circuit_breaker(symbol):
            DECISION_STATS["circuit_breaker_blocked"] += 1
            # Optional: Print only once per 100 cycles to avoid spam
            if DECISION_STATS["cycles"] % 100 == 0:
                send_info(f"⛔ {symbol} Circuit Breaker Active (3 Consecutive Losses). Sleeping.")
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
            return

        # Cooldown
        last_close = _last_closure_time.get(symbol)
        if last_close:
            elapsed = (datetime.now(timezone.utc) - last_close).total_seconds() / 60
            if elapsed < COOLDOWN_MINUTES:
                DECISION_STATS["cooldown_blocked"] += 1
                return

        # Data Fetch
        h4_df = get_data(symbol, TIMEFRAME_HTF, 250)
        htf_bias = get_htf_bias(h4_df)
        if htf_bias == "NEUTRAL":
            DECISION_STATS["htf_neutral_blocks"] += 1
            return

        h1_df = get_data(symbol, TIMEFRAME_ZONE, ZONE_LOOKBACK)
        if len(h1_df) < 50: return
        
        h1_atr = AverageTrueRange(h1_df['high'], h1_df['low'], h1_df['close']).average_true_range().iloc[-1]
        
        m5_df = get_data(symbol, TIMEFRAME_CONFIRM, 60)
        m1_df = get_data(symbol, TIMEFRAME_ENTRY, 200)
        if len(m5_df) < 5 or len(m1_df) < 35: return

        # Numba Analysis
        demand_zones, supply_zones = detect_zones(h1_df)
        fast_demand, fast_supply = detect_fast_zones(h1_df) 
        
        if not demand_zones and not supply_zones and not fast_demand and not fast_supply:
            DECISION_STATS["no_zones_found"] += 1
            return
<<<<<<< HEAD
            
        spec = get_symbol_spec(symbol)

        # 🚀 MODIFIED: 4. ADR CALCULATION (Passed to Engine, not blocking here)
        adr_pct = get_adr_percentage(symbol)
        # We removed the 'return' blocking logic here to allow reversals

        trend = calculate_trend(h1_df)
        
        # Heartbeat
        import random
        if random.random() < 0.05: 
            send_info(f"👀 {symbol} Status | Bias: {htf_bias} | ADR: {adr_pct*100:.1f}%")
=======

        trend = calculate_trend(h1_df)
        
        # 🧠 REGIME DETECTION: Identify trending vs ranging market
        # Ranging markets suppress L2 momentum trades — they need trending conditions
        market_regime = detect_market_regime(h1_df)
        effective_strategy = strategy_mode
        if market_regime == "RANGING" and strategy_mode == "momentum_continuation_L2":
            effective_strategy = "standard"  # Demote L2 to standard in choppy markets
        
        # Heartbeat
        import random
        if random.random() < 0.05: 
            send_info(f"👀 {symbol} Status | Bias: {htf_bias} | Zones: {len(demand_zones)}/{len(fast_demand)}")
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
        
        m5_context = {
            'trend': calculate_trend(m5_df),
            'macd': MACD(m5_df['close']).macd().iloc[-1],
            'rsi': RSIIndicator(m5_df['close']).rsi().iloc[-1]
        }
        
        macd_vals = MACD(m1_df['close'])
        macd_line = macd_vals.macd().dropna().values
        macd_sig = macd_vals.macd_signal().dropna().values
        rsi_val = RSIIndicator(m1_df['close']).rsi().dropna().values
        vwap = VolumeWeightedAveragePrice(m1_df['high'], m1_df['low'], m1_df['close'], m1_df['real_volume']).vwap.iloc[-1]
        atr = AverageTrueRange(m1_df['high'], m1_df['low'], m1_df['close']).average_true_range().iloc[-1]

        # Active Trades
        tick = mt5.symbol_info_tick(symbol)
        if not tick: return
        
        active_trades_virtual = {}
        live_pos = mt5.positions_get(symbol=symbol)
        if live_pos:
            for p in live_pos:
                if p.magic == MAGIC:
                    active_trades_virtual[symbol] = {
                        'side': 'buy' if p.type == mt5.ORDER_TYPE_BUY else 'sell',
                        'ticket': p.ticket
                    }

<<<<<<< HEAD
        
        # Zone Touches
        for z in demand_zones:
            if abs(tick.bid - z["price"]) <= max(atr, 50 * spec.point):
                ZONE_TOUCH_STATS["demand_touches"] += 1
                break
        else:
            for z in supply_zones:
                if abs(tick.bid - z["price"]) <= max(atr, 50 * spec.point):
                    ZONE_TOUCH_STATS["supply_touches"] += 1
                    break
            else:
                DECISION_STATS["price_not_in_zone"] += 1
=======
        # Decision Engine
        spec = get_symbol_spec(symbol)
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
        
        # Zone Touches
        for z in demand_zones:
            if abs(tick.bid - z["price"]) <= max(atr, 50 * spec.point):
                ZONE_TOUCH_STATS["demand_touches"] += 1
                break
        else:
            for z in supply_zones:
                if abs(tick.bid - z["price"]) <= max(atr, 50 * spec.point):
                    ZONE_TOUCH_STATS["supply_touches"] += 1
                    break
            else:
                DECISION_STATS["price_not_in_zone"] += 1
        
        signals, _ = run_trade_decision_engine(
            symbol=symbol,
            point=spec.point,
            current_price=tick.bid, 
            trend=trend,
            demand_zones=demand_zones,
            supply_zones=supply_zones,
            fast_demand_zones=fast_demand,
            fast_supply_zones=fast_supply,
            m1_candles_for_crt=m1_df.iloc[-3:],
            m5_candles_for_patterns=m5_df.iloc[-5:],
            active_trades=active_trades_virtual,
            zone_touch_counts={},
            SL_BUFFER=60 * spec.point,
            TP_RATIO=TP_RATIO,
            CHECK_RANGE=max(atr, 50 * spec.point),
            LOT_SIZE=spec.volume_min, 
            MAGIC=MAGIC,
<<<<<<< HEAD
            strategy_mode=strategy_mode, 
=======
            strategy_mode=effective_strategy, 
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
            macd=macd_line, macd_signal=macd_sig, rsi=rsi_val, vwap=vwap, atr=atr, htf_atr=h1_atr,
            m5_context=m5_context,
            htf_high=h1_df['high'].max(), 
            htf_low=h1_df['low'].min(),
            last_closed_h1=h1_df.iloc[-2],
            htf_bias=htf_bias,
            thresholds=THRESHOLDS,
            adr_pct=adr_pct # 🚀 PASSED ADR INTO ENGINE
        )
        if signals:
            DECISION_STATS["signals_generated"] += len(signals)
            
            signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            best_signal = signals[0] 
            
            sig = best_signal
            confidence = float(sig.get('confidence', 0))
            side = sig['side']
            
<<<<<<< HEAD
            # 5. DAILY FILTER (Red/Green Day)
            #daily_dir = get_daily_candle_direction(symbol)
           # if side == 'buy' and daily_dir == 'sell':
           #     DECISION_STATS["daily_filter_blocked"] += 1
           #     return 
           # if side == 'sell' and daily_dir == 'buy':
           #     DECISION_STATS["daily_filter_blocked"] += 1
           #     return 

=======
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
            if confidence >= CONFIDENCE_THRESHOLD: 
                if symbol in active_trades_virtual:
                    existing = active_trades_virtual[symbol]
                    if existing['side'] != side:
                        if AUTO_CLOSE_ON_STRONG and confidence > 0.85:
                            send_info(f"⚔️ {symbol} Auto-Close for Strong Signal")
                            close_positions_for_symbol(symbol)
                            time_module.sleep(1)
                        else: pass
                    else: pass
                
                if symbol not in active_trades_virtual:
                    entry, sl, tp = sig['entry'], sig['sl'], sig['tp']
                    current_strat = sig.get('strategy', strategy_mode)
                    final_lot = determine_lot_size(symbol, sl, entry, fixed_lot, current_strat)

                    if DRY_RUN:
                        msg = (f"📥 [DRY] SIGNAL: {symbol} | {side.upper()} {sig.get('reason')}\n"
                               f"Conf: {format_confidence_label(confidence)} | Lot: {final_lot}")
                        safe_telegram(msg)
                    else:
                        res = place_order(symbol, side, final_lot, MAGIC, comment="Nawthviper", sl=sl, tp=tp)
                        
                        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                            DECISION_STATS["signals_executed"] += 1
<<<<<<< HEAD
=======
                            _pending_signals[res.order] = sig  # 🧠 Remember signal for result logging
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
                            if confidence >= MIN_CONF_FOR_TELEGRAM:
                                msg = (f"📥 SIGNAL: {symbol} | {side.upper()} {sig.get('reason')}\n"
                                       f"Entry: {entry:.5f} | SL: {sl:.5f}\n"
                                       f"Conf: {format_confidence_label(confidence)}")
                                safe_telegram(msg)
                            send_info(f"✅ {symbol} {side} Opened. Ticket: {res.order}")
                        elif res:
                            send_info(f"❌ {symbol} Order Failed: {res.comment} (Code: {res.retcode})")

        if DECISION_STATS["cycles"] % 100 == 0:
            print_decision_summary()
            print_rejection_summary()
<<<<<<< HEAD
=======
            print_performance_summary()
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
    
    except Exception as e:
        send_info(f"Cycle Error {symbol}: {e}")
        traceback.print_exc()

def print_decision_summary():
    with PRINT_LOCK:
        print("\n===== DECISION JOURNAL SUMMARY =====")
        for k, v in DECISION_STATS.items():
            print(f"{k}: {v}")
        print("Zone Touches:", ZONE_TOUCH_STATS)
        print("===================================\n")