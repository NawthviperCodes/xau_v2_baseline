# ==========================================
# === backtester.py (Gold Diagnostic Mode) =
# ==========================================
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from zone_detector import detect_zones
from trade_decision_engine import run_trade_decision_engine
from scalper_strategy_engine import calculate_trend, get_htf_bias


SYMBOL = "XAUUSD"
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=30) 
CAPITAL = 100.0
FIXED_LOT = 0.1

def get_data(symbol, timeframe, start, end):
    rates = mt5.copy_rates_range(symbol, timeframe, start, end)
    if rates is None or len(rates) == 0: return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def run_backtest():
    if not mt5.initialize():
        print("❌ MT5 Init Failed")
        return

    info = mt5.symbol_info(SYMBOL)
    if not info:
        print(f"❌ Could not get info for {SYMBOL}")
        return
        
    point = info.point
    print(f"ℹ️ {SYMBOL} Point: {point} | Digits: {info.digits}")
    
    # --- VOLATILITY CALIBRATION ---
    # Default (Forex)
    SL_BUFFER = 150 * point 
    CHECK_RANGE = 50 * point 
    
    if "XAU" in SYMBOL or "GOLD" in SYMBOL:
        # GOLD MODE: 20x Multiplier
        # Range: 1000 points = $10.00 (Gold needs room to breathe)
        print("⚠️ GOLD DETECTED: Setting Check Range to $10.00 (1000 points)")
        CHECK_RANGE = 1000 * point 
        SL_BUFFER = 500 * point # $5.00 Stop
    
    elif "JPY" in SYMBOL:
         print("ℹ️ JPY Mode Active")

    print(f"⏳ Fetching Data for {SYMBOL}...")
    
    df_m1 = get_data(SYMBOL, mt5.TIMEFRAME_M1, START_DATE, END_DATE)
    df_m5 = get_data(SYMBOL, mt5.TIMEFRAME_M5, START_DATE, END_DATE)
    df_h1 = get_data(SYMBOL, mt5.TIMEFRAME_H1, START_DATE, END_DATE)
    
    if df_m5 is None: return

    print(f"✅ Loaded {len(df_m5)} M5 candles. Starting Diagnostics...")

    balance = CAPITAL
    trades = []
    wins = 0
    losses = 0
    last_trade_time = None
    
    # Debug counters
    total_zones_seen = 0
    signals_rejected = 0
    
    for i in range(100, len(df_m5)):
        curr_m5 = df_m5.iloc[i]
        curr_time = curr_m5['time']
        price = curr_m5['close']

        # Slices
        h1_slice = df_h1[df_h1['time'] <= curr_time].tail(200)
        m5_slice = df_m5.iloc[i-60:i+1]
        m1_slice = df_m1[df_m1['time'] <= curr_time].tail(200)

        if len(h1_slice) < 50: continue

        # --- LOGIC ---
        htf_bias = get_htf_bias(h1_slice)
        demand, supply = detect_zones(h1_slice)
        trend = calculate_trend(h1_slice)
        
        # DEBUG: Are we seeing zones?
        total_zones_seen += len(demand) + len(supply)
        
        # DEBUG PRINT (Every 2000th candle)
        if i % 2000 == 0:
            print(f"🔎 [{curr_time}] Price: {price:.2f} | Zones Found: {len(demand)}D {len(supply)}S | Bias: {htf_bias}")

        signals, _ = run_trade_decision_engine(
            symbol=SYMBOL,
            point=point,
            current_price=price,
            trend=trend,
            demand_zones=demand,
            supply_zones=supply,
            m1_candles_for_crt=m1_slice.tail(3),
            m5_candles_for_patterns=m5_slice.tail(5),
            active_trades={}, 
            zone_touch_counts={},
            SL_BUFFER=SL_BUFFER,
            TP_RATIO=1.5,
            CHECK_RANGE=CHECK_RANGE, # <--- WIDE RANGE
            LOT_SIZE=FIXED_LOT,
            MAGIC=123,
            strategy_mode="standard",
            macd=None, macd_signal=None, rsi=None, vwap=None, atr=None,
            htf_high=h1_slice.tail(24)['high'].max(),
            htf_low=h1_slice.tail(24)['low'].min(),
            htf_bias=htf_bias,
            thresholds={"MIN_CONFIDENCE_FOR_TRADE": 0.55} # Lowered for test
        )

        if signals:
            best_sig = max(signals, key=lambda x: x['confidence'])
            
            # Cooldown
            if last_trade_time and (curr_time - last_trade_time).total_seconds() < 1800:
                signals_rejected += 1
                continue

            # Execution Sim
            entry = best_sig['entry']
            sl = best_sig['sl']
            tp = best_sig['tp']
            side = best_sig['side']
            
            future = df_m5.iloc[i+1 : i+48] 
            result = "OPEN"
            
            for _, row in future.iterrows():
                if side == 'buy':
                    if row['low'] <= sl: result = "LOSS"; break
                    if row['high'] >= tp: result = "WIN"; break
                else:
                    if row['high'] >= sl: result = "LOSS"; break
                    if row['low'] <= tp: result = "WIN"; break
            
            if result != "OPEN":
                # Gold PnL: Approx $1 per 0.01 lot per $1 move.
                # 0.1 lot = $10 per $1 move.
                dist = abs(entry - tp) if result == "WIN" else -abs(entry - sl)
                pnl = dist * 100 * FIXED_LOT # Approx for Gold
                
                balance += pnl
                trades.append(result)
                last_trade_time = curr_time
                print(f"⚡ [{curr_time}] {side} {best_sig['reason']} -> {result} (${pnl:.2f})")
                if result == "WIN": wins += 1
                else: losses += 1

    print("\n" + "="*30)
    print(f"🏁 DIAGNOSTIC RESULTS ({SYMBOL})")
    print(f"Zones Detected Total: {total_zones_seen}")
    print(f"Trades Taken: {len(trades)}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Final Balance: ${balance:.2f}")
    print("="*30)

if __name__ == "__main__":
    run_backtest()