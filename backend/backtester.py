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
from zone_detector import detect_zones, detect_fast_zones
from trade_decision_engine import run_trade_decision_engine
from scalper_strategy_engine import calculate_trend, get_htf_bias

# === CONFIGURATION ===
SYMBOL = "XAUUSD" 
TIMEFRAME_HTF = mt5.TIMEFRAME_H1
TIMEFRAME_ENTRY = mt5.TIMEFRAME_M5

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
        )

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

if __name__ == "__main__":
    run_backtest()