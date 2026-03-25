<<<<<<< HEAD
# =========================================================
# === backtest_runner.py (Sniper Edition: 70% Target) =====
# =========================================================
# 
# ✅ SESSION FILTER: Trade only London/NY Volatility
# ✅ ADR FILTER: Avoid trading exhausted moves
# ✅ CONFIDENCE BOOST: Only take 0.65+ signals
#

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from ta.volatility import AverageTrueRange
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice

# --- Import Your Actual Strategy Modules ---
=======
# ======================================================
# === backtest_engine.py ===
# ======================================================
#
# Elite backtester for Nawthviper — uses YOUR REAL logic.
#
# ✅ Candle-by-candle simulation (zero lookahead)
# ✅ Real spread + randomised slippage
# ✅ Full trade lifecycle: partial TP, SL to BE, trailing
# ✅ Equity curve + drawdown tracking
# ✅ Walk-forward testing support
# ✅ Multi-pair robustness testing
# ✅ Expectancy, profit factor, Monte Carlo
# ✅ CSV trade log (feeds learning system)
#
# USAGE:
#   python backtest_engine.py
#
# DATA FORMAT:
#   CSV files with columns: time, open, high, low, close, tick_volume
#   Filename pattern: XAUUSD_H1.csv, EURUSD_M5.csv etc.
#   Export from MT5: Tools → History Center → Export
#

import os
import csv
import json
import math
import random
import traceback
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional

from ta.volatility import AverageTrueRange
from ta.trend import MACD
from ta.momentum import RSIIndicator

# === Your real modules ===
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
from zone_detector import detect_zones, detect_fast_zones
from trade_decision_engine import run_trade_decision_engine

# ======================================================
# === CONFIGURATION
# ======================================================

# ======================================================
# === CONFIGURATION
# ======================================================
#
# ONE SOURCE OF TRUTH:
#   config.json  → all strategy rules, thresholds, symbols, timeframes
#   BT_CONFIG    → backtest-only settings (paths, balance, sim params)
#
# Strategy parameters are NEVER hardcoded here. They are loaded directly
# from config.json so live and backtest behaviour are always identical.
#

# --- Backtest-only settings (nothing that exists in config.json) ---
BT_CONFIG = {
    # ── Paths ─────────────────────────────────────────────────────────────────
    "data_dir":   "./backtest_data",   # MT5-exported CSVs: XAUUSD_H1.csv etc.
    "output_dir": "./backtest_results",

    # ── Account ───────────────────────────────────────────────────────────────
    "initial_balance": 10_000.0,       # ← Set to your live account size

    # ── Risk (not in config.json — set per backtest run) ──────────────────────
    "risk_percent": 1.0,               # Standard. aggressive=2.0, conservative=0.5

    # ── Spread per symbol (price units, not pips) ─────────────────────────────
    # Exness Zero account — raw spread + small commission. Very tight.
    # These are conservative estimates. Stress test triples them.
    "spread": {
        "XAUUSDz": 0.15,   # ~15 cents (Exness Zero gold is very tight)
        "EURUSDz": 0.00003, # ~0.3 pip
        "GBPUSDz": 0.00005, # ~0.5 pip
        "USDJPYz": 0.005,   # ~0.5 pip
        "AUDUSDz": 0.00004,
        "USDCADz": 0.00005,
    },

    # Dynamic spread multiplier — widens randomly each trade (0.8x quiet → 2.5x volatile)
    "spread_mult_range": (0.8, 2.5),

    # ── Point size per symbol (matches MT5 symbol_info.point) ─────────────────
    "point": {
        "XAUUSDz": 0.01,
        "EURUSDz": 0.00001,
        "GBPUSDz": 0.00001,
        "USDJPYz": 0.001,
        "AUDUSDz": 0.00001,
        "USDCADz": 0.00001,
    },

    # ── Pip value per 1.0 lot (for P&L calculation) ────────────────────────────
    "pip_value_per_lot": {
        "XAUUSDz": 10.0,
        "EURUSDz": 10.0,
        "GBPUSDz": 10.0,
        "USDJPYz": 9.1,
        "AUDUSDz": 10.0,
        "USDCADz": 7.7,
    },

    # ── Execution realism ─────────────────────────────────────────────────────
    "max_slippage_pips": 2.0,

    # ── Session filter (UTC hours) ─────────────────────────────────────────────
    # Joburg = UTC+2. London 07:00 → NY close 21:00 UTC.
    "session_hours": (7, 21),

    # News simulation: randomly drop ~5% of signals (broker rejections, spikes)
    "news_skip_prob": 0.05,

    # ── Walk-forward ──────────────────────────────────────────────────────────
    "walk_forward": {
        "enabled":      True,
        "train_months": 3,
        "test_months":  1,
    },

    # ── Monte Carlo ───────────────────────────────────────────────────────────
    "monte_carlo_runs": 1000,

    # ── HTF bias EMAs (must match get_htf_bias() in scalper_strategy_engine) ───
    "htf_ema_fast": 50,
    "htf_ema_slow": 200,
}

# ── Timeframe string → CSV key map ────────────────────────────────────────────
TF_MAP = {
    "TIMEFRAME_H4":  "H4",
    "TIMEFRAME_H1":  "H1",
    "TIMEFRAME_M5":  "M5",
    "TIMEFRAME_M1":  "M1",
    "TIMEFRAME_M15": "M15",
}

# === CONFIGURATION ===
SYMBOL = "XAUUSD" 
TIMEFRAME_HTF = mt5.TIMEFRAME_H1
TIMEFRAME_ENTRY = mt5.TIMEFRAME_M5

<<<<<<< HEAD
# TEST RANGE: 2025 Data
START_DATE = datetime(2025, 1, 1) 
END_DATE = datetime(2025, 10, 1)

CAPITAL = 1000.0
FIXED_LOT = 0.01 
SPREAD_COST = 0.20 

# 🛡️ RISK SETTINGS 🛡️
MAX_DAILY_CONSECUTIVE_LOSSES = 2  # Tighter Leash (Stop after 2 losses)
COOLDOWN_WIN = 15                 
COOLDOWN_LOSS = 90                # Longer penalty for losing

# 🎯 SNIPER SETTINGS 🎯
SESSION_START = 8  # London Open (08:00)
SESSION_END = 20   # NY Close (20:00)
MIN_CONFIDENCE = 0.65 # Only High Quality
ADR_PERIOD = 14

def get_data(symbol, timeframe, start, end):
    warmup_start = start - timedelta(days=20)
    rates = mt5.copy_rates_range(symbol, timeframe, warmup_start, end)
    
    if rates is None or len(rates) == 0:
        print(f"❌ Data fetch failed for {symbol}.")
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Indicators
    macd = MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['rsi'] = RSIIndicator(df['close']).rsi()
    df['atr'] = AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
    vwap = VolumeWeightedAveragePrice(df['high'], df['low'], df['close'], df['real_volume'])
    df['vwap'] = vwap.vwap
    
    df = df[df['time'] >= start]
    return df.reset_index(drop=True)

def get_daily_stats(current_time, df_m5):
    """
    Returns (DailyOpen, CurrentRange, ADR)
    """
    day_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    todays_candles = df_m5[df_m5['time'] >= day_start]
    
    if len(todays_candles) == 0: return None, 0, 0
    
    daily_open = todays_candles.iloc[0]['open']
    day_high = todays_candles['high'].max()
    day_low = todays_candles['low'].min()
    current_range = day_high - day_low
    
    # Estimate ADR using ATR of H1 or just simpler approximation here
    # (In backtest we can just use the ATR column which is typically close to H1 ATR)
    adr = todays_candles.iloc[-1]['atr'] * 24 # Rough approximation of Daily Range from M5 ATR
    # Better: Use the last closed Daily candle if possible, but for M5 stream:
    # We will assume ADR is approx 1500-2000 points for Gold, or dynamic:
    
    return daily_open, current_range, adr

def run_backtest():
    print(f"🚀 Starting SNIPER Backtest for {SYMBOL}...")
    
    if not mt5.initialize(): return
    info = mt5.symbol_info(SYMBOL)
    point = info.point if info else 0.01
    
    # Gold Calibration
    SL_BUFFER = 300 * point if "XAU" in SYMBOL else 150 * point
    CHECK_RANGE = 1000 * point if "XAU" in SYMBOL else 50 * point

    print(f"⏳ Fetching Data ({START_DATE.date()} to {END_DATE.date()})...")
    df_m1 = get_data(SYMBOL, mt5.TIMEFRAME_M1, START_DATE, END_DATE)
    df_m5 = get_data(SYMBOL, TIMEFRAME_ENTRY, START_DATE, END_DATE)
    df_h1 = get_data(SYMBOL, TIMEFRAME_HTF, START_DATE, END_DATE)
    
    if df_m5 is None: return

    print(f"✅ Loaded {len(df_m5)} M5 candles. Applying SNIPER Filters...")

    balance = CAPITAL
    wins = 0
    losses = 0
    last_trade_time = None
    consecutive_losses = 0
    current_day = None
    
    for i in range(50, len(df_m5)):
        curr_m5 = df_m5.iloc[i]
        curr_time = curr_m5['time']
        price = curr_m5['close']

        # 1. New Day Reset
        if current_day != curr_time.date():
            current_day = curr_time.date()
            consecutive_losses = 0 

        # 2. Circuit Breaker
        if consecutive_losses >= MAX_DAILY_CONSECUTIVE_LOSSES: continue 

        # 3. 🕒 TIME OF DAY FILTER (Kill Zone)
        if not (SESSION_START <= curr_time.hour < SESSION_END):
            continue # Skip Asian Session / Late NY

        # 4. Cooldown
        if last_trade_time:
            minutes_since = (curr_time - last_trade_time).total_seconds() / 60
            required_wait = COOLDOWN_LOSS if (balance < CAPITAL) else COOLDOWN_WIN 
            if minutes_since < required_wait: continue

        # 5. Daily Trend & ADR Filter
        daily_open, current_range_val, adr_val = get_daily_stats(curr_time, df_m5.iloc[:i+1])
        allow_buy = True
        allow_sell = True
        
        if daily_open:
            if price < daily_open: allow_buy = False  
            if price > daily_open: allow_sell = False 

        # 🛑 ADR EXHAUSTION Check
        # If we have moved > 80% of typical volatility, don't chase breaks
        # Hardcoded Gold ADR Baseline ~ $25-$30 (2500-3000 points)
        GOLD_ADR_POINTS = 2500 * point
        if current_range_val > (GOLD_ADR_POINTS * 0.85):
             continue # Market is exhausted for the day

        if not allow_buy and not allow_sell: continue

        # 6. Core Analysis
        h1_slice = df_h1[df_h1['time'] < curr_time] 
        if len(h1_slice) < 100: continue
        
        m5_slice = df_m5.iloc[i-50:i+1]
        
        htf_bias = get_htf_bias(h1_slice)
        trend = calculate_trend(h1_slice.tail(100))
        demand, supply = detect_zones(h1_slice.tail(200))
        fast_demand, fast_supply = detect_fast_zones(h1_slice.tail(50))
        
        signals, _ = run_trade_decision_engine(
            symbol=SYMBOL,
            point=point,
            current_price=price,
            trend=trend,
            demand_zones=demand,
            supply_zones=supply,
            fast_demand_zones=fast_demand,
            fast_supply_zones=fast_supply,
            m1_candles_for_crt=df_m1[df_m1['time'] <= curr_time].tail(3) if df_m1 is not None else pd.DataFrame(),
            m5_candles_for_patterns=m5_slice.tail(5),
            active_trades={},
            zone_touch_counts={},
            SL_BUFFER=SL_BUFFER,
            TP_RATIO=1.5,
            CHECK_RANGE=CHECK_RANGE,
            LOT_SIZE=FIXED_LOT,
            MAGIC=123,
            strategy_mode="backtest_sniper",
            macd=m5_slice['macd'].values, 
            macd_signal=m5_slice['macd_signal'].values, 
            rsi=m5_slice['rsi'].values, 
            vwap=curr_m5['vwap'], 
            atr=curr_m5['atr'],
            htf_atr=h1_slice.iloc[-1]['atr'] if 'atr' in h1_slice.columns else curr_m5['atr'],
            m5_context={'trend': trend, 'macd': m5_slice['macd'].iloc[-1], 'rsi': m5_slice['rsi'].iloc[-1]},
            htf_high=h1_slice.tail(24)['high'].max(),
            htf_low=h1_slice.tail(24)['low'].min(),
            htf_bias=htf_bias,
            thresholds={"MIN_CONFIDENCE_FOR_TRADE": MIN_CONFIDENCE} # STRICTER
=======
def load_live_config(path: str = "config.json") -> dict:
    """
    Load config.json and merge strategy parameters into BT_CONFIG.
    This is the single source of truth for all strategy rules.
    BT_CONFIG only holds backtest-specific settings (paths, balance, sim params).
    """
    with open(path, "r") as f:
        raw = json.load(f)

    strat  = raw["StrategyParameters"]
    thresh = strat["Thresholds"]

    # Pull every strategy param directly — no hardcoding
    merged = dict(BT_CONFIG)
    merged.update({
        # Symbols
        "symbols":              raw["BotSettings"]["SYMBOLS"],

        # Timeframes — resolved via TF_MAP so run_simulation uses correct CSV keys
        "tf_zone":    TF_MAP.get(strat["TIMEFRAME_ZONE"],    "H1"),
        "tf_entry":   TF_MAP.get(strat["TIMEFRAME_ENTRY"],   "M1"),
        "tf_confirm": TF_MAP.get(strat["TIMEFRAME_CONFIRM"], "M5"),
        "tf_htf":     TF_MAP.get(strat["TIMEFRAME_HTF"],     "H4"),

        # Strategy rules
        "tp_ratio":             strat["TP_RATIO"],
        "partial_close_pct":    strat["PARTIAL_CLOSE_PERCENT"],
        "zone_lookback":        strat["ZONE_LOOKBACK"],
        "allow_pyramid":        strat["ALLOW_PYRAMID_SAME_SIDE"],
        "auto_close_on_strong": strat["AUTO_CLOSE_ON_STRONG"],
        "close_conf_diff":      strat["CLOSE_CONF_DIFF"],
        "max_touch_allowed":    strat["MAX_TOUCH_ALLOWED"],

        # All thresholds — full block passed to decision engine
        # MAX_TOUCH_ALLOWED injected here so decision engine can read it from thresholds dict
        "min_confidence":       thresh["MIN_CONFIDENCE_FOR_TRADE"],
        "thresholds":           {**thresh, "MAX_TOUCH_ALLOWED": strat["MAX_TOUCH_ALLOWED"]},

        # SL/trail — 60 pips tight buffer (reduced from 150)
        "sl_buffer_pips":       60,
        "trail_pips":           150,
        "cooldown_candles":     3,
        "max_consecutive_losses": 3,
    })

    return merged


# ======================================================
# === DATA STRUCTURES
# ======================================================

@dataclass
class BacktestTrade:
    symbol:        str
    side:          str
    entry:         float
    sl:            float
    tp:            float
    lot:           float
    open_idx:      int
    open_time:     str
    confidence:    float
    strategy:      str
    reason:        str

    # Lifecycle state
    status:        str   = "open"   # open | closed
    close_idx:     int   = -1
    close_time:    str   = ""
    close_price:   float = 0.0
    close_reason:  str   = ""       # TP | SL | TRAIL | BE_TRAIL

    # After partial close
    partial_done:  bool  = False
    sl_at_be:      bool  = False
    current_sl:    float = 0.0      # tracks trailing SL

    # Result
    pnl:           float = 0.0
    result:        str   = ""       # win | loss

    def __post_init__(self):
        self.current_sl = self.sl


@dataclass
class EquityPoint:
    idx:      int
    time:     str
    balance:  float
    equity:   float
    drawdown: float


# ======================================================
# === DATA LOADING
# ======================================================

def load_csv(path: str) -> pd.DataFrame:
    """
    Load MT5-exported CSV and standardise columns.
    Handles MT5's tab-separated format:
      <DATE>  <TIME>  <OPEN>  <HIGH>  <LOW>  <CLOSE>  <TICKVOL>  <VOL>  <SPREAD>
      2021.01.03  23:00:00  1909.401  ...
    Also handles comma-separated and already-clean formats.
    """
    # Auto-detect separator by reading first line raw
    with open(path, 'r') as f:
        first_line = f.readline()
    sep = '\t' if '\t' in first_line else ','

    df = pd.read_csv(path, sep=sep)

    # Strip whitespace and angle brackets from ALL column names, lowercase
    df.columns = [c.strip().strip('<>').strip().lower() for c in df.columns]

    # Rename MT5 column variants to standard names
    rename_map = {
        'tickvol':  'tick_volume',
        'tick_vol': 'tick_volume',
        'vol':      'real_volume',
        'volume':   'real_volume',
    }
    df.rename(columns=rename_map, inplace=True)

    # Build unified datetime column
    # MT5 uses dots in dates: 2021.01.03 — replace with dashes for parsing
    if 'date' in df.columns:
        date_str = df['date'].astype(str).str.replace('.', '-', regex=False)
        if 'time' in df.columns:
            time_str = df['time'].astype(str)
            df['time'] = pd.to_datetime(date_str + ' ' + time_str,
                                        format='%Y-%m-%d %H:%M:%S')
        else:
            df['time'] = pd.to_datetime(date_str, format='%Y-%m-%d')
    elif 'time' in df.columns:
        df['time'] = pd.to_datetime(
            df['time'].astype(str).str.replace('.', '-', regex=False),
            format='mixed', dayfirst=False
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
        )
    else:
        raise ValueError(f"Cannot find date/time column in {path}.\n"
                         f"Columns found: {list(df.columns)}")

<<<<<<< HEAD
        if signals:
            best_sig = max(signals, key=lambda x: x['confidence'])
            side = best_sig['side']

            if side == 'buy' and not allow_buy: continue
            if side == 'sell' and not allow_sell: continue

            # Execution Sim
            entry, sl, tp = best_sig['entry'], best_sig['sl'], best_sig['tp']
            
            future = df_m5.iloc[i+1 : i+144] 
            result = "OPEN"
            exit_price = 0.0
            
            for _, row in future.iterrows():
                if side == 'buy':
                    if row['low'] <= sl: result = "LOSS"; exit_price = sl; break
                    if row['high'] >= tp: result = "WIN"; exit_price = tp; break
                else:
                    if row['high'] >= sl: result = "LOSS"; exit_price = sl; break
                    if row['low'] <= tp: result = "WIN"; exit_price = tp; break
            
            if result != "OPEN":
                raw_diff = (exit_price - entry) if side == 'buy' else (entry - exit_price)
                gross_pnl = raw_diff * 100 * FIXED_LOT
                net_pnl = gross_pnl - SPREAD_COST
                
                balance += net_pnl
                last_trade_time = curr_time
                
                if net_pnl > 0:
                    wins += 1
                    consecutive_losses = 0 
                else:
                    losses += 1
                    consecutive_losses += 1 
                
                icon = "🟢" if net_pnl > 0 else "🔴"
                print(f"{icon} [{curr_time}] {side.upper()} | ${net_pnl:.2f} | Streak: {consecutive_losses}")

    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    print("\n" + "="*40)
    print(f"📊 SNIPER BACKTEST ({START_DATE.date()} - {END_DATE.date()})")
    print("="*40)
    print(f"Total Trades:  {total_trades}")
    print(f"Win Rate:      {win_rate:.2f}%")
    print(f"Wins:          {wins}")
    print(f"Losses:        {losses}")
    print(f"Net PnL:       ${balance - CAPITAL:.2f}")
    print(f"Final Balance: ${balance:.2f}")
    print("="*40)
=======
    # Validate OHLC
    for col in ['open', 'high', 'low', 'close']:
        if col not in df.columns:
            raise ValueError(f"Missing column '{col}' in {path}. "
                             f"Columns: {list(df.columns)}")

    # Ensure volume columns exist
    if 'tick_volume' not in df.columns:
        df['tick_volume'] = 1
    if 'real_volume' not in df.columns:
        df['real_volume'] = df['tick_volume']

    df = df.sort_values('time').reset_index(drop=True)
    return df[['time', 'open', 'high', 'low', 'close', 'tick_volume', 'real_volume']]


def build_multi_tf(symbol: str, data_dir: str) -> dict:
    """
    Load all available timeframes for a symbol.
    Returns dict: {'H4': df, 'H1': df, 'M5': df, 'M1': df}
    Falls back gracefully if a timeframe is missing.
    """
    tfs = {}
    for tf in ['H4', 'H1', 'M5', 'M1']:
        path = os.path.join(data_dir, f"{symbol}_{tf}.csv")
        if os.path.exists(path):
            try:
                tfs[tf] = load_csv(path)
                print(f"  [Data] Loaded {symbol}_{tf}: {len(tfs[tf])} candles")
            except Exception as e:
                print(f"  [Data] Failed {symbol}_{tf}: {e}")
    return tfs


# ======================================================
# === MARKET UTILITIES
# ======================================================

def get_htf_bias(df: pd.DataFrame, fast=50, slow=200) -> str:
    if len(df) < slow:
        return "NEUTRAL"
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean().iloc[-1]
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean().iloc[-1]
    if ema_fast > ema_slow: return "UP"
    if ema_fast < ema_slow: return "DOWN"
    return "NEUTRAL"


def calculate_trend(df: pd.DataFrame) -> Optional[str]:
    if len(df) < 51: return None
    sma50 = df['close'].rolling(50).mean().iloc[-1]
    last  = df['close'].iloc[-1]
    return "uptrend" if last > sma50 else "downtrend"


def apply_spread_slippage(price: float, side: str, spread: float, max_slippage: float) -> float:
    """Realistic entry: widen by spread and randomise slippage."""
    slippage = random.uniform(0, max_slippage)
    if side == "buy":
        return price + spread + slippage
    else:
        return price - spread - slippage


def calc_lot(balance: float, risk_pct: float, entry: float, sl: float,
             pip_value: float, point: float) -> float:
    """Risk-based lot sizing — mirrors live determine_lot_size."""
    risk_amt   = balance * (risk_pct / 100.0)
    dist_price = abs(entry - sl)
    if dist_price == 0 or pip_value == 0 or point == 0:
        return 0.01
    dist_pips    = dist_price / point
    loss_per_lot = dist_pips * pip_value
    if loss_per_lot <= 0:
        return 0.01
    lot = risk_amt / loss_per_lot
    return max(0.01, round(lot, 2))


def calc_pnl(side: str, entry: float, close_price: float, lot: float,
             pip_value: float, point: float) -> float:
    """P&L in account currency."""
    dist_pips = abs(close_price - entry) / point
    pnl       = dist_pips * pip_value * lot
    if side == "buy":
        return pnl if close_price > entry else -pnl
    else:
        return pnl if close_price < entry else -pnl


# ======================================================
# === TRADE LIFECYCLE
# ======================================================

def update_trade(trade: BacktestTrade, candle: pd.Series,
                 trail_dist: float, pip_value: float, point: float,
                 partial_pct: float = 0.5) -> BacktestTrade:
    """
    Update one open trade against the current candle.
    Mirrors live logic: partial TP at 1R → realize partial profit → SL to BE → trailing stop.
    Worst-case collision: if both SL and TP would hit same candle, SL wins.
    """
    hi, lo = candle['high'], candle['low']
    risk = abs(trade.entry - trade.sl)

    # --- 1. Partial TP at 1R: realize profit on half position ---
    if not trade.partial_done and partial_pct > 0:
        one_r_target = (trade.entry + risk) if trade.side == "buy" else (trade.entry - risk)
        hit_1r = (hi >= one_r_target) if trade.side == "buy" else (lo <= one_r_target)
        if hit_1r:
            # Realize profit on the partial close portion
            partial_lot    = trade.lot * partial_pct
            partial_profit = calc_pnl(trade.side, trade.entry, one_r_target,
                                      partial_lot, pip_value, point)
            trade.pnl     += partial_profit          # Book it immediately
            trade.lot     *= (1.0 - partial_pct)     # Remaining lot shrinks
            trade.partial_done = True
            trade.sl_at_be     = True
            trade.current_sl   = trade.entry         # Move SL to breakeven

    # --- 2. Trailing SL (only after BE) ---
    if trade.partial_done:
        if trade.side == "buy":
            proposed = hi - trail_dist
            if proposed > trade.current_sl:
                trade.current_sl = proposed
        else:
            proposed = lo + trail_dist
            if trade.current_sl == trade.entry or proposed < trade.current_sl:
                trade.current_sl = proposed

    # --- 3. Worst-case collision: if SL AND TP both hit this candle, SL wins ---
    sl_hit = (lo <= trade.current_sl) if trade.side == "buy" else (hi >= trade.current_sl)
    tp_hit = (hi >= trade.tp)         if trade.side == "buy" else (lo <= trade.tp)

    if sl_hit and tp_hit:
        tp_hit = False  # Conservative: assume price hit SL first

    # --- 4. Check SL hit ---
    if sl_hit:
        reason = "BE_TRAIL" if trade.partial_done else "SL"
        return _close_trade(trade, candle, trade.current_sl, reason, pip_value, point)

    # --- 5. Check TP hit ---
    if tp_hit:
        return _close_trade(trade, candle, trade.tp, "TP", pip_value, point)

    return trade


def _close_trade(trade: BacktestTrade, candle: pd.Series, close_price: float,
                 reason: str, pip_value: float, point: float) -> BacktestTrade:
    trade.status      = "closed"
    trade.close_price = close_price
    trade.close_time  = str(candle['time'])
    trade.close_reason = reason
    # += not = : partial profit booked in update_trade() must not be overwritten.
    # When partial_close_pct == 0.0 this is a no-op (trade.pnl starts at 0.0).
    # When partials are re-enabled, this correctly accumulates partial + remainder.
    trade.pnl        += calc_pnl(trade.side, trade.entry, close_price,
                                  trade.lot, pip_value, point)
    trade.result      = "win" if trade.pnl >= 0 else "loss"
    return trade


# ======================================================
# === METRICS
# ======================================================

def compute_metrics(trades: list, initial_balance: float) -> dict:
    """Full performance metrics from a list of closed BacktestTrade objects."""
    closed = [t for t in trades if t.status == "closed"]
    if not closed:
        return {}

    pnls   = [t.pnl for t in closed]
    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_trades = len(closed)
    win_count    = len(wins)
    loss_count   = len(losses)
    win_rate     = win_count / total_trades if total_trades else 0

    avg_win  = sum(wins)  / len(wins)   if wins   else 0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    total_profit = sum(wins)
    total_loss   = abs(sum(losses))
    profit_factor = total_profit / total_loss if total_loss else float('inf')

    # Equity curve + drawdown
    balance   = initial_balance
    peak      = initial_balance
    max_dd    = 0.0
    max_dd_pct = 0.0
    consec_loss = 0
    max_consec  = 0

    for t in closed:
        balance += t.pnl
        peak     = max(peak, balance)
        dd       = peak - balance
        dd_pct   = (dd / peak * 100) if peak > 0 else 0
        max_dd     = max(max_dd, dd)
        max_dd_pct = max(max_dd_pct, dd_pct)

        if t.pnl < 0:
            consec_loss += 1
            max_consec   = max(max_consec, consec_loss)
        else:
            consec_loss  = 0

    final_balance = initial_balance + sum(pnls)
    net_return_pct = (final_balance - initial_balance) / initial_balance * 100

    return {
        "total_trades":       total_trades,
        "wins":               win_count,
        "losses":             loss_count,
        "win_rate_pct":       round(win_rate * 100, 2),
        "avg_win":            round(avg_win, 2),
        "avg_loss":           round(avg_loss, 2),
        "expectancy":         round(expectancy, 2),
        "profit_factor":      round(profit_factor, 4),
        "total_profit":       round(total_profit, 2),
        "total_loss":         round(total_loss, 2),
        "net_pnl":            round(sum(pnls), 2),
        "net_return_pct":     round(net_return_pct, 2),
        "initial_balance":    initial_balance,
        "final_balance":      round(final_balance, 2),
        "max_drawdown":       round(max_dd, 2),
        "max_drawdown_pct":   round(max_dd_pct, 2),
        "max_consec_losses":  max_consec,
    }


def monte_carlo(trades: list, initial_balance: float, runs: int = 1000) -> dict:
    """
    Shuffle win/loss order N times.
    Shows worst-case drawdown distribution and survival probability.
    """
    if not trades: return {}
    pnls = [t.pnl for t in trades if t.status == "closed"]
    if not pnls: return {}

    max_drawdowns = []
    final_balances = []

    for _ in range(runs):
        shuffled = random.sample(pnls, len(pnls))
        balance  = initial_balance
        peak     = initial_balance
        max_dd   = 0.0
        for p in shuffled:
            balance += p
            peak     = max(peak, balance)
            dd       = (peak - balance) / peak * 100 if peak > 0 else 0
            max_dd   = max(max_dd, dd)
        max_drawdowns.append(max_dd)
        final_balances.append(balance)

    dd_arr  = np.array(max_drawdowns)
    bal_arr = np.array(final_balances)

    return {
        "mc_runs":             runs,
        "mc_max_dd_median":    round(float(np.median(dd_arr)), 2),
        "mc_max_dd_95th_pct":  round(float(np.percentile(dd_arr, 95)), 2),
        "mc_max_dd_worst":     round(float(np.max(dd_arr)), 2),
        "mc_survival_rate":    round(float(np.mean(bal_arr > 0)) * 100, 1),
        "mc_final_bal_median": round(float(np.median(bal_arr)), 2),
    }


# ======================================================
# === CORE SIMULATION
# ======================================================

def run_simulation(symbol: str, tfs: dict, cfg: dict,
                   start_idx: int = 0, end_idx: int = None) -> list:
    """
    Candle-by-candle simulation over H1 data.
    Uses real detect_zones + run_trade_decision_engine.
    Returns list of BacktestTrade objects.
    """
    h1  = tfs.get(cfg.get('tf_zone',    'H1'))
    m5  = tfs.get(cfg.get('tf_confirm', 'M5'))
    m1  = tfs.get(cfg.get('tf_entry',   'M1'))
    h4  = tfs.get(cfg.get('tf_htf',     'H4'))

    if h1 is None:
        print(f"  [!] {symbol}: No H1 data. Skipping.")
        return []

    h1 = h1.iloc[start_idx:end_idx].reset_index(drop=True)
    if len(h1) < 200:
        print(f"  [!] {symbol}: Not enough H1 candles ({len(h1)}). Skipping.")
        return []

    # Config shortcuts
    spread_val   = cfg['spread'].get(symbol, 0.0002)
    point_val    = cfg['point'].get(symbol, 0.00001)
    pip_val      = cfg['pip_value_per_lot'].get(symbol, 10.0)
    sl_buffer    = cfg['sl_buffer_pips'] * point_val
    trail_dist   = cfg['trail_pips'] * point_val
    max_slip     = cfg['max_slippage_pips'] * point_val
    risk_pct     = cfg['risk_percent']
    min_conf     = cfg['min_confidence']
    tp_ratio     = cfg['tp_ratio']
    thresholds   = cfg['thresholds']
    cooldown     = cfg['cooldown_candles']
    circ_max     = cfg['max_consecutive_losses']
    partial_pct  = cfg.get('partial_close_pct', 0.5)  # use config, not hardcoded

    trades         = []
    open_trade     = None
    balance        = cfg['initial_balance']
    last_trade_idx = -cooldown - 1
    consec_losses  = 0
    current_day    = None  # Tracks calendar date for clean circuit breaker reset

    # Pending signal: detected on candle[i], executed on candle[i+1] open
    pending_signal = None

    # Equity curve
    equity_points  = []
    peak_balance   = cfg['initial_balance']

    # Session / news config
    session_start, session_end = cfg.get('session_hours', (0, 24))
    news_skip_prob = cfg.get('news_skip_prob', 0.0)
    spread_mult_lo, spread_mult_hi = cfg.get('spread_mult_range', (1.0, 1.0))

    # We need at least ZONE_LOOKBACK of history before we start making decisions
    WARMUP = 200

    for i in range(WARMUP, len(h1)):
        candle = h1.iloc[i]

        # --- 0. Execute pending signal at THIS candle's open (1-candle delay) ---
        if pending_signal is not None and open_trade is None:
            sig  = pending_signal
            side = sig['side']
            # Dynamic spread: widens randomly each trade — simulates real conditions
            dynamic_spread = random.uniform(spread_mult_lo, spread_mult_hi) * spread_val
            entry = apply_spread_slippage(candle['open'], side, dynamic_spread, max_slip)
            sl    = sig['sl']
            tp    = sig['tp']
            lot   = calc_lot(balance, risk_pct, entry, sl, pip_val, point_val)
            open_trade = BacktestTrade(
                symbol     = symbol,
                side       = side,
                entry      = entry,
                sl         = sl,
                tp         = tp,
                lot        = lot,
                open_idx   = i,
                open_time  = str(candle['time']),
                confidence = float(sig.get('confidence', 0)),
                strategy   = sig.get('strategy', 'standard'),
                reason     = sig.get('reason', ''),
            )
            last_trade_idx = i
        pending_signal = None  # Always clear after attempting execution

        # --- Session filter: skip signal generation outside trading hours ---
        candle_hour = candle['time'].hour if hasattr(candle['time'], 'hour') else 12
        in_session  = session_start <= candle_hour < session_end

        # Track equity curve
        current_equity = balance + (
            calc_pnl(open_trade.side, open_trade.entry, candle['close'],
                     open_trade.lot, pip_val, point_val)
            if open_trade and open_trade.status == "open" else 0.0
        )
        peak_balance = max(peak_balance, current_equity)
        dd_pct = ((peak_balance - current_equity) / peak_balance * 100) if peak_balance > 0 else 0
        equity_points.append(EquityPoint(i, str(candle['time']), balance, current_equity, dd_pct))

        # --- 1. Update open trade lifecycle ---
        if open_trade and open_trade.status == "open":
            open_trade = update_trade(open_trade, candle, trail_dist, pip_val, point_val, partial_pct)
            if open_trade.status == "closed":
                balance       += open_trade.pnl
                last_trade_idx = i
                result_str     = open_trade.result

                if result_str == "loss":
                    consec_losses += 1
                else:
                    consec_losses  = 0

                trades.append(open_trade)
                open_trade = None

        # --- 2. Circuit breaker: reset cleanly on new calendar day ---
        candle_day = candle['time'].date() if hasattr(candle['time'], 'date') else None
        if candle_day and candle_day != current_day:
            current_day   = candle_day
            consec_losses = 0  # New day → full reset

        if consec_losses >= circ_max:
            continue  # Blocked for the rest of today

        # --- 3. Cooldown ---
        if (i - last_trade_idx) < cooldown:
            continue

        # --- 4. Skip if already in a trade ---
        if open_trade and open_trade.status == "open":
            continue

        # --- 5. Build lookback windows ---
        h1_window = h1.iloc[max(0, i - 300):i+1]

        # Align M5 by timestamp
        if m5 is not None:
            m5_mask   = m5['time'] <= candle['time']
            m5_window = m5[m5_mask].tail(60)
        else:
            m5_window = h1.iloc[max(0, i-60):i+1]  # Fallback: use H1

        if m1 is not None:
            m1_mask   = m1['time'] <= candle['time']
            m1_window = m1[m1_mask].tail(200)
        else:
            m1_window = h1.iloc[max(0, i-200):i+1]

        if h4 is not None:
            h4_mask   = h4['time'] <= candle['time']
            h4_window = h4[h4_mask].tail(250)
        else:
            h4_window = h1_window.tail(250)

        if len(m5_window) < 5 or len(m1_window) < 35:
            continue

        # --- 6. Indicators ---
        try:
            htf_bias = get_htf_bias(h4_window,
                                    cfg['htf_ema_fast'],
                                    cfg['htf_ema_slow'])
            if htf_bias == "NEUTRAL":
                continue

            trend  = calculate_trend(h1_window)
            h1_atr = AverageTrueRange(h1_window['high'],
                                      h1_window['low'],
                                      h1_window['close']).average_true_range().iloc[-1]

            macd_obj  = MACD(m1_window['close'])
            macd_line = macd_obj.macd().dropna().values
            macd_sig  = macd_obj.macd_signal().dropna().values
            rsi_vals  = RSIIndicator(m1_window['close']).rsi().dropna().values
            atr_val   = AverageTrueRange(m1_window['high'],
                                         m1_window['low'],
                                         m1_window['close']).average_true_range().iloc[-1]

            try:
                from ta.volume import VolumeWeightedAveragePrice
                vwap = VolumeWeightedAveragePrice(
                    m1_window['high'], m1_window['low'],
                    m1_window['close'], m1_window['real_volume']
                ).vwap.iloc[-1]
            except Exception:
                vwap = m1_window['close'].mean()

            m5_context = {
                'trend': calculate_trend(m5_window),
                'macd':  MACD(m5_window['close']).macd().iloc[-1],
                'rsi':   RSIIndicator(m5_window['close']).rsi().iloc[-1]
            }

        except Exception:
            continue

        # --- 7. Zone detection ---
        try:
            demand_zones, supply_zones = detect_zones(h1_window)
            fast_demand, fast_supply   = detect_fast_zones(h1_window)
        except Exception:
            continue

        if not demand_zones and not supply_zones and not fast_demand and not fast_supply:
            continue

        # --- 8. Session + news guard (signal generation only) ---
        if not in_session:
            continue

        # Simulate ~5% of signals being killed by unpredictable news spikes
        if random.random() < news_skip_prob:
            continue

        try:
            signals, _ = run_trade_decision_engine(
                symbol        = symbol,
                point         = point_val,
                current_price = candle['close'],
                trend         = trend,
                demand_zones  = demand_zones,
                supply_zones  = supply_zones,
                fast_demand_zones = fast_demand,
                fast_supply_zones = fast_supply,
                m1_candles_for_crt    = m1_window.iloc[-3:],
                m5_candles_for_patterns = m5_window.iloc[-5:],
                active_trades = {},
                zone_touch_counts = {},
                SL_BUFFER     = sl_buffer,
                TP_RATIO      = tp_ratio,
                CHECK_RANGE   = max(atr_val, 50 * point_val),
                LOT_SIZE      = 0.01,
                MAGIC         = 0,
                strategy_mode = "standard",
                macd          = macd_line,
                macd_signal   = macd_sig,
                rsi           = rsi_vals,
                vwap          = vwap,
                atr           = atr_val,
                htf_atr       = h1_atr,
                m5_context    = m5_context,
                htf_high      = h1_window['high'].max(),
                htf_low       = h1_window['low'].min(),
                last_closed_h1 = h1_window.iloc[-2],
                htf_bias      = htf_bias,
                thresholds    = thresholds,
            )
        except Exception:
            continue

        if not signals:
            continue

        signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        sig = signals[0]
        confidence = float(sig.get('confidence', 0))

        if confidence < min_conf:
            continue

        # --- 9. Store as pending — will execute on NEXT candle's open ---
        # This eliminates same-candle entry cheat and adds 1-candle execution delay.
        pending_signal = sig

    # Close any trade still open at end of data
    if open_trade and open_trade.status == "open":
        last_candle = h1.iloc[-1]
        open_trade.status      = "closed"
        open_trade.close_price = last_candle['close']
        open_trade.close_time  = str(last_candle['time'])
        open_trade.close_reason = "END_OF_DATA"
        open_trade.pnl         = calc_pnl(open_trade.side, open_trade.entry,
                                           last_candle['close'], open_trade.lot,
                                           pip_val, point_val)
        open_trade.result      = "win" if open_trade.pnl >= 0 else "loss"
        trades.append(open_trade)

    return trades, equity_points


# ======================================================
# === WALK-FORWARD ENGINE
# ======================================================

def run_walk_forward(symbol: str, tfs: dict, cfg: dict) -> list:
    """
    Slides a test window across the full H1 dataset one month at a time.
    Returns only trades from test windows (zero look-ahead).

    Design:
      • Each iteration tests one month of live decisions.
      • The simulation for that window starts WARMUP_BARS (500 H1 bars ≈ 21 days)
        before the test window so indicators are fully warmed up.
      • Only trades whose open_time falls inside the test window are kept —
        the warmup period generates no recorded trades.
      • No parameter fitting occurs, so no "train" simulation is needed.
        The old STEP A has been removed; it was reprocessing the full history
        on every loop with zero effect on outputs, halving throughput for free.
    """
    h1 = tfs.get('H1')
    if h1 is None: return []

    wf         = cfg['walk_forward']
    train_mo   = wf['train_months']
    test_mo    = wf['test_months']
    all_trades = []

    start_dt   = h1['time'].iloc[0]
    end_dt     = h1['time'].iloc[-1]

    train_delta = timedelta(days=30 * train_mo)
    test_delta  = timedelta(days=30 * test_mo)

    window_start = start_dt
    window_num   = 0

    while True:
        train_end  = window_start + train_delta
        test_start = train_end
        test_end   = test_start + test_delta

        if test_end > end_dt:
            break

        # Index ranges
        train_mask = (h1['time'] >= window_start) & (h1['time'] < train_end)
        test_mask  = (h1['time'] >= test_start)   & (h1['time'] < test_end)

        test_start_idx = h1[test_mask].index.min() if test_mask.any() else None
        test_end_idx   = h1[test_mask].index.max() if test_mask.any() else None

        if test_start_idx is None or pd.isna(test_start_idx):
            break

        window_num += 1
        print(f"  [WF-{window_num}] Test: {test_start.date()} → {test_end.date()}")

        # ── STEP A removed ──────────────────────────────────────────────────
        # The old "train" simulation ran the entire history from bar 0 to
        # test_start on every loop — purely wasted compute, because no
        # parameters are being fitted or updated between windows.
        # Removing it cuts runtime roughly in half with zero impact on results.
        # ────────────────────────────────────────────────────────────────────

        # ── STEP B: warmup-slice simulation ─────────────────────────────────
        # Instead of re-running from bar 0 (which reprocesses the same ancient
        # history on every loop), we start 500 bars before the test window.
        # 500 H1 bars ≈ 21 days — enough for ATR(14), EMA(200), zone lookback,
        # and MACD warmup to stabilise before the first live decision is made.
        # Integrity is preserved: the simulation still only ever sees candles
        # up to the current bar; no future data leaks into indicator state.
        WARMUP_BARS = 500
        sim_start_idx = max(0, int(test_start_idx) - WARMUP_BARS)

        test_trades, _eq = run_simulation(symbol, tfs, cfg,
                                          start_idx=sim_start_idx,
                                          end_idx=int(test_end_idx) + 1)

        # Keep only trades that OPENED inside the test window
        test_trades = [
            t for t in test_trades
            if test_start <= pd.to_datetime(t.open_time) < test_end
        ]
        all_trades.extend(test_trades)

        # ── FIX: advance by test_delta (1 month), NOT by train_delta.
        # Old code set window_start = test_start, which jumped the entire
        # training window forward each iteration, leaving multi-month gaps
        # and producing only ~2 test windows over a year of data.
        # Correct behaviour: slide forward one test period at a time so
        # every month gets evaluated and trade count is no longer starved.
        window_start = window_start + test_delta

    print(f"  [WF] Complete — {window_num} test windows, {len(all_trades)} total trades collected.")
    return all_trades


# ======================================================
# === OUTPUT & REPORTING
# ======================================================

def save_trades_csv(trades: list, path: str):
    """Save all trades to CSV — feeds your learning system."""
    if not trades: return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'symbol', 'side', 'open_time', 'close_time',
            'entry', 'close_price', 'sl', 'tp',
            'lot', 'pnl', 'result', 'close_reason',
            'confidence', 'strategy', 'reason',
        ])
        for t in trades:
            writer.writerow([
                t.symbol, t.side, t.open_time, t.close_time,
                round(t.entry, 5), round(t.close_price, 5),
                round(t.sl, 5), round(t.tp, 5),
                t.lot, round(t.pnl, 2), t.result, t.close_reason,
                round(t.confidence, 4), t.strategy, t.reason,
            ])


def save_metrics_json(metrics: dict, mc: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    combined = {**metrics, **mc}
    with open(path, 'w') as f:
        json.dump(combined, f, indent=4)


def print_report(symbol: str, metrics: dict, mc: dict):
    print(f"\n{'='*55}")
    print(f"  BACKTEST REPORT — {symbol}")
    print(f"{'='*55}")
    if not metrics:
        print("  No trades generated.")
        return

    print(f"  Trades:         {metrics['total_trades']}  ({metrics['wins']}W / {metrics['losses']}L)")
    print(f"  Win Rate:       {metrics['win_rate_pct']}%")
    print(f"  Expectancy:     ${metrics['expectancy']}")
    print(f"  Profit Factor:  {metrics['profit_factor']}")
    print(f"  Net Return:     {metrics['net_return_pct']}%  (${metrics['net_pnl']})")
    print(f"  Final Balance:  ${metrics['final_balance']}")
    print(f"  Max Drawdown:   {metrics['max_drawdown_pct']}%  (${metrics['max_drawdown']})")
    print(f"  Max Consec L:   {metrics['max_consec_losses']}")

    if mc:
        print(f"\n  ── Monte Carlo ({mc['mc_runs']} runs) ──")
        print(f"  Median DD:      {mc['mc_max_dd_median']}%")
        print(f"  95th pct DD:    {mc['mc_max_dd_95th_pct']}%")
        print(f"  Worst DD:       {mc['mc_max_dd_worst']}%")
        print(f"  Survival Rate:  {mc['mc_survival_rate']}%")

    # Verdict
    print(f"\n  ── Verdict ──")
    pf   = metrics.get('profit_factor', 0)
    wr   = metrics.get('win_rate_pct', 0)
    dd   = metrics.get('max_drawdown_pct', 100)
    exp  = metrics.get('expectancy', 0)
    total = metrics.get('total_trades', 0)

    if total < 30:
        print("  ⚠️  INSUFFICIENT DATA — Need 30+ trades for valid conclusions.")
    elif pf >= 1.5 and wr >= 45 and dd <= 20 and exp > 0:
        print("  ✅  ROBUST — System shows edge. Consider live testing.")
    elif pf >= 1.2 and exp > 0:
        print("  🟡  MARGINAL — Some edge present but refine before live.")
    else:
        print("  🔴  WEAK — No consistent edge. Do not trade live.")

    print(f"{'='*55}\n")


# ======================================================
# === ROBUSTNESS STRESS TEST
# ======================================================

def stress_test(symbol: str, tfs: dict, cfg: dict) -> dict:
    """
    'Break your bot' test.
    Runs simulation with increased spread and 1-candle entry delay.
    If it still shows edge → the system is robust.
    """
    print(f"\n  [Stress] Running stress test on {symbol}...")

    stressed_cfg = dict(cfg)
    stressed_cfg['spread'] = {k: v * 3 for k, v in cfg['spread'].items()}  # 3x spread
    stressed_cfg['max_slippage_pips'] = cfg['max_slippage_pips'] * 3         # 3x slippage

    trades, _eq = run_simulation(symbol, tfs, stressed_cfg)
    metrics = compute_metrics(trades, cfg['initial_balance'])

    pf = metrics.get('profit_factor', 0)
    verdict = "✅ HOLDS" if pf >= 1.0 else "🔴 COLLAPSES"
    print(f"  [Stress] {symbol} under 3x spread: PF={pf} → {verdict}")
    return metrics


# ======================================================
# === MAIN
# ======================================================

def main():
    # Load config.json as single source of truth, merged with backtest-only settings
    cfg = load_live_config("config.json")
    print(f"  [Config] Loaded config.json")
    print(f"  [Config] Symbols:     {cfg['symbols']}")
    print(f"  [Config] TP Ratio:    {cfg['tp_ratio']} | Partial Close: {cfg['partial_close_pct']}")
    print(f"  [Config] Min Conf:    {cfg['min_confidence']} | TF Zone: {cfg['tf_zone']} | TF HTF: {cfg['tf_htf']}")

    data_dir   = cfg['data_dir']
    output_dir = cfg['output_dir']
    os.makedirs(output_dir, exist_ok=True)

    all_symbol_results = {}

    for symbol in cfg['symbols']:
        print(f"\n{'─'*55}")
        print(f"  Processing: {symbol}")
        print(f"{'─'*55}")

        tfs = build_multi_tf(symbol, data_dir)
        if not tfs:
            print(f"  [!] No data found for {symbol} in {data_dir}. Skipping.")
            continue

        # ── Data-completeness check: warn loudly if required TFs are missing.
        # Missing M1 or H4 means the backtest silently falls back to H1 proxies,
        # which changes signal frequency and makes results non-representative.
        # Fix: export the missing TF from MT5 before trusting the output.
        required_tfs = [cfg['tf_zone'], cfg['tf_entry'], cfg['tf_confirm'], cfg['tf_htf']]
        missing_tfs  = [tf for tf in required_tfs if tf not in tfs]
        if missing_tfs:
            print(f"  [⚠️  DATA WARNING] {symbol}: Missing TFs {missing_tfs}. "
                  f"Backtest will use fallback proxies — results are NOT faithful to live config. "
                  f"Export these from MT5 before trusting this run.")

        # --- Full simulation or Walk-Forward ---
        if cfg['walk_forward']['enabled']:
            print(f"  [Mode] Walk-Forward ({cfg['walk_forward']['train_months']}m train / "
                  f"{cfg['walk_forward']['test_months']}m test)")
            trades = run_walk_forward(symbol, tfs, cfg)
            equity_points = []  # Walk-forward aggregates across windows; equity curve N/A
        else:
            print(f"  [Mode] Full simulation")
            trades, equity_points = run_simulation(symbol, tfs, cfg)

            # Save equity curve
            eq_path = os.path.join(output_dir, f"{symbol}_equity.csv")
            with open(eq_path, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(['idx', 'time', 'balance', 'equity', 'drawdown_pct'])
                for ep in equity_points:
                    w.writerow([ep.idx, ep.time, round(ep.balance, 2),
                                 round(ep.equity, 2), round(ep.drawdown, 2)])

        metrics = compute_metrics(trades, cfg['initial_balance'])
        mc      = monte_carlo(trades, cfg['initial_balance'], cfg['monte_carlo_runs'])

        # --- Stress test ---
        stress_metrics = stress_test(symbol, tfs, cfg)

        # --- Save outputs ---
        trades_path  = os.path.join(output_dir, f"{symbol}_trades.csv")
        metrics_path = os.path.join(output_dir, f"{symbol}_metrics.json")
        save_trades_csv(trades, trades_path)
        save_metrics_json(metrics, mc, metrics_path)

        # --- Print report ---
        print_report(symbol, metrics, mc)

        all_symbol_results[symbol] = {
            "metrics": metrics,
            "mc": mc,
            "stress_pf": stress_metrics.get('profit_factor', 0),
        }

    # --- Cross-pair robustness summary ---
    print(f"\n{'='*55}")
    print(f"  CROSS-PAIR ROBUSTNESS SUMMARY")
    print(f"{'='*55}")
    print(f"  {'Symbol':<10} {'WR%':>6} {'PF':>6} {'DD%':>7} {'Trades':>7} {'Stress PF':>10}")
    print(f"  {'─'*50}")
    for sym, res in all_symbol_results.items():
        m  = res['metrics']
        if not m: continue
        print(f"  {sym:<10} "
              f"{m.get('win_rate_pct', 0):>6.1f} "
              f"{m.get('profit_factor', 0):>6.2f} "
              f"{m.get('max_drawdown_pct', 0):>7.1f} "
              f"{m.get('total_trades', 0):>7} "
              f"{res['stress_pf']:>10.2f}")

    # ── FIX: require both sufficient trade count AND profit factor.
    # Old code counted any pair with PF >= 1.2 as "confirmed", so 1 pair
    # with 2 trades could mark the whole system as robust — a false positive.
    # A minimum of 30 trades is the standard threshold for statistical validity.
    MIN_TRADES_FOR_VERDICT = 30
    verdict_count = sum(
        1 for r in all_symbol_results.values()
        if r['metrics'].get('total_trades', 0) >= MIN_TRADES_FOR_VERDICT
        and r['metrics'].get('profit_factor', 0) >= 1.2
    )
    total_tested = len(all_symbol_results)
    print(f"\n  Edge confirmed on {verdict_count}/{total_tested} pairs.")
    if total_tested > 0 and verdict_count / total_tested >= 0.75:
        print("  ✅  System is ROBUST across instruments.")
    elif verdict_count > 0:
        print("  🟡  PARTIAL — Strong on some pairs, weak on others. Investigate.")
    else:
        print("  🔴  FRAGILE — System does not generalise. Do not trade live.")
    print(f"{'='*55}\n")

    # Save master summary
    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, 'w') as f:
        json.dump({s: r['metrics'] for s, r in all_symbol_results.items()}, f, indent=4)
    print(f"  Results saved to: {output_dir}/")

>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)

if __name__ == "__main__":
    main()