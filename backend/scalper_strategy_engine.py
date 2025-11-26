# ======================================================
# === scalper_strategy_engine.py (Production Final) ====
# ======================================================
# 
# ✅ ARCHITECTURE: Thread-Safe Parallel Worker
# ✅ LOGIC: Smart Lot Sizing (User Override > Risk Fallback)
# ✅ PERFORMANCE: Numba Zones + Non-Blocking News
#
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time as time_module
import json
import threading
import traceback
import os
from datetime import datetime, timedelta, timezone, time as dtime
from concurrent.futures import ThreadPoolExecutor

# --- Custom Modules ---
from ta.volatility import AverageTrueRange
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice

# High-Performance Modules
from zone_detector import detect_zones, detect_fast_zones # Numba Optimized
from news_filter_te import start_news_thread, check_upcoming_high_impact # Threaded
from trade_executor import (
    place_order, 
    modify_position_sltp, 
    trail_sl, 
    close_partial_and_move_sl_to_be, 
    close_positions_for_symbol,
    EXECUTION_LOCK
)
from trade_decision_engine import (
    run_trade_decision_engine, 
    format_confidence_label
)
from performance_tracker import send_daily_summary
from telegram_notifier import send_telegram_message

# ============================
# === CONFIGURATION LOADER ===
# ============================

def load_config(path='config.json'):
    try:
        with open(path, 'r') as f:
            config = json.load(f)
        
        # Map Timeframes
        TIMEFRAME_MAP = {
            "TIMEFRAME_M1": mt5.TIMEFRAME_M1,
            "TIMEFRAME_M5": mt5.TIMEFRAME_M5,
            "TIMEFRAME_M15": mt5.TIMEFRAME_M15,
            "TIMEFRAME_H1": mt5.TIMEFRAME_H1,
            "TIMEFRAME_H4": mt5.TIMEFRAME_H4,
        }
        
        # Apply mappings
        config['StrategyParameters']['TIMEFRAME_ZONE'] = TIMEFRAME_MAP[config['StrategyParameters']['TIMEFRAME_ZONE']]
        config['StrategyParameters']['TIMEFRAME_ENTRY'] = TIMEFRAME_MAP[config['StrategyParameters']['TIMEFRAME_ENTRY']]
        config['StrategyParameters']['TIMEFRAME_CONFIRM'] = TIMEFRAME_MAP[config['StrategyParameters']['TIMEFRAME_CONFIRM']]
        
        tf_htf_str = config['StrategyParameters'].get('TIMEFRAME_HTF', "TIMEFRAME_H4")
        config['StrategyParameters']['TIMEFRAME_HTF'] = TIMEFRAME_MAP.get(tf_htf_str, mt5.TIMEFRAME_H4)

        return config
    except Exception as e:
        print(f"[CRITICAL] Config Load Failed: {e}")
        exit()

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
CONFIDENCE_THRESHOLD = THRESHOLDS.get('MIN_CONFIDENCE_FOR_TRADE', 0.60)
MIN_CONF_FOR_TELEGRAM = THRESHOLDS.get('MIN_CONF_FOR_TELEGRAM', 0.75)

# ============================
# === STATE & CACHING ===
# ============================

SYMBOL_SPECS = {} 
tp1_hit_tickets = set()
_last_closure_time = {} 
COOLDOWN_MINUTES = 15

def get_symbol_spec(symbol):
    if symbol not in SYMBOL_SPECS:
        info = mt5.symbol_info(symbol)
        if info:
            SYMBOL_SPECS[symbol] = info
    return SYMBOL_SPECS.get(symbol)

def normalize_symbol(symbol):
    if get_symbol_spec(symbol): return symbol
    for suffix in [".mic", ".pro", ".cent", ".raw"]:
        test = symbol + suffix
        if get_symbol_spec(test): return test
    return symbol

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

def determine_lot_size(symbol, sl_price, entry_price, fixed_lot, strategy_mode):
    """
    DECISION LOGIC: Smart Override
    1. If user provided fixed_lot > 0, USE IT.
    2. Else, calculate risk based on strategy_mode.
    """
    info = get_symbol_spec(symbol)
    if not info: return 0.01

    # 1. User Override
    if fixed_lot and float(fixed_lot) > 0:
        return float(fixed_lot)

    # 2. Risk Fallback
    risk_percent = 1.0 # Default Standard
    if strategy_mode == "aggressive":
        risk_percent = 2.0
    elif strategy_mode == "conservative":
        risk_percent = 0.5
    
    # Calculate Lot based on Risk %
    try:
        acc = mt5.account_info()
        if not acc: return info.volume_min
        
        equity = acc.equity
        risk_amt = equity * (risk_percent / 100.0)
        dist = abs(entry_price - sl_price)
        
        if dist == 0 or info.trade_tick_value == 0: return info.volume_min
        
        # Risk Formula
        ticks = dist / info.trade_tick_size
        loss_per_lot = ticks * info.trade_tick_value
        if loss_per_lot <= 0: return info.volume_min
        
        lots = risk_amt / loss_per_lot
        
        # Normalize
        step = info.volume_step
        lots = round(lots / step) * step
        return max(info.volume_min, min(info.volume_max, lots))
    except:
        return info.volume_min

# ============================
# === LIVE STATE MANAGEMENT ===
# ============================

def check_for_partial_tp_live(symbol):
    try:
        positions = mt5.positions_get(symbol=symbol)
        if not positions: return

        for pos in positions:
            if pos.magic != MAGIC: continue
            if pos.ticket in tp1_hit_tickets: continue
            
            is_buy = pos.type == mt5.ORDER_TYPE_BUY
            entry, sl = pos.price_open, pos.sl
            
            # Check if secured
            if (is_buy and sl >= entry) or (not is_buy and sl > 0 and sl <= entry):
                tp1_hit_tickets.add(pos.ticket)
                continue
            
            if sl == 0: continue
            risk = abs(entry - sl)
            target = (entry + risk) if is_buy else (entry - risk)
            
            tick = mt5.symbol_info_tick(symbol)
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
    """
    Executed by ThreadPoolExecutor from main.py
    """
    try:
        # 1. Housekeeping
        trail_sl(symbol, MAGIC)
        check_for_partial_tp_live(symbol)
        
        if check_upcoming_high_impact(symbol): return # News Filter

        # Cooldown
        last_close = _last_closure_time.get(symbol)
        if last_close:
            elapsed = (datetime.now(timezone.utc) - last_close).total_seconds() / 60
            if elapsed < COOLDOWN_MINUTES: return

        # 2. Data Fetch
        h4_df = get_data(symbol, TIMEFRAME_HTF, 250)
        htf_bias = get_htf_bias(h4_df)
        if htf_bias == "NEUTRAL": return

        h1_df = get_data(symbol, TIMEFRAME_ZONE, ZONE_LOOKBACK)
        if len(h1_df) < 50: return
        
        m5_df = get_data(symbol, TIMEFRAME_CONFIRM, 60)
        m1_df = get_data(symbol, TIMEFRAME_ENTRY, 200)
        
        if len(m5_df) < 5 or len(m1_df) < 35: return

        # 3. Numba Analysis
        demand_zones, supply_zones = detect_zones(h1_df)
        fast_demand, fast_supply = detect_fast_zones(h1_df) 

        trend = calculate_trend(h1_df)
        
        # --- DEBUG HEARTBEAT (Print status every ~50th check to prove life) ---
        # We use a random check so we don't spam, but we see 'life' occasionally
        import random
        if random.random() < 0.05: # 5% chance to print status per cycle
            send_info(f"👀 {symbol} Status | Bias: {htf_bias} | Zones: {len(demand_zones)} Dem, {len(supply_zones)} Sup | Trend: {trend}")
        # ---------------------------------------------------------------------
        
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

        # 4. Active Trades Context
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

        # 5. Decision Engine
        spec = get_symbol_spec(symbol)
        
        signals, _ = run_trade_decision_engine(
            symbol=symbol,
            point=spec.point,
            current_price=tick.bid, 
            trend=trend,
            demand_zones=demand_zones,
            supply_zones=supply_zones,
            m1_candles_for_crt=m1_df.iloc[-3:],
            m5_candles_for_patterns=m5_df.iloc[-5:],
            active_trades=active_trades_virtual,
            zone_touch_counts={},
            SL_BUFFER=150 * spec.point,
            TP_RATIO=TP_RATIO,
            CHECK_RANGE=max(atr, 50 * spec.point),
            LOT_SIZE=spec.volume_min, 
            MAGIC=MAGIC,
            strategy_mode=strategy_mode, # Passed from Main
            macd=macd_line, macd_signal=macd_sig, rsi=rsi_val, vwap=vwap, atr=atr,
            m5_context=m5_context,
            htf_high=h1_df['high'].max(), 
            htf_low=h1_df['low'].min(),
            last_closed_h1=h1_df.iloc[-2],
            htf_bias=htf_bias,
            thresholds=THRESHOLDS
        )
        
        # 6. Execution Loop
        for sig in signals:
            confidence = float(sig.get('confidence', 0))
            side = sig['side']
            
            if confidence < CONFIDENCE_THRESHOLD: continue

            # Conflict Handling
            if symbol in active_trades_virtual:
                existing = active_trades_virtual[symbol]
                if existing['side'] != side:
                    if AUTO_CLOSE_ON_STRONG and confidence > 0.85:
                        send_info(f"⚔️ {symbol} Auto-Close for Strong Signal")
                        close_positions_for_symbol(symbol)
                        time_module.sleep(1)
                    else: continue
                else: continue

            # --- LOT SIZING (SMART OVERRIDE) ---
            entry, sl, tp = sig['entry'], sig['sl'], sig['tp']
            
            final_lot = determine_lot_size(symbol, sl, entry, fixed_lot, strategy_mode)

            # Execution
            if DRY_RUN:
                msg = (f"📥 [DRY] SIGNAL: {symbol} | {side.upper()} {sig.get('reason')}\n"
                       f"Conf: {format_confidence_label(confidence)} | Lot: {final_lot}")
                safe_telegram(msg)
            else:
                if confidence >= MIN_CONF_FOR_TELEGRAM:
                    msg = (f"📥 SIGNAL: {symbol} | {side.upper()} {sig.get('reason')}\n"
                           f"Entry: {entry:.5f} | SL: {sl:.5f}\n"
                           f"Conf: {format_confidence_label(confidence)}")
                    safe_telegram(msg)

                res = place_order(symbol, side, final_lot, MAGIC, comment=strategy_mode, sl=sl, tp=tp)
                
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    send_info(f"✅ {symbol} {side} Opened. Ticket: {res.order}")

    except Exception as e:
        send_info(f"Cycle Error {symbol}: {e}")