# ======================================================
# === trade_decision_engine.py (Production Final) ====
# ======================================================
# 
# ✅ FIX: Layer 2 Momentum Continuation (Trend Pullbacks)
# ✅ SAFETY: "Panic Guard" to stop catching falling knives
#

from datetime import datetime
import pandas as pd
import math
import numpy as np
from ta.volatility import AverageTrueRange
from performance_tracker import get_pattern_weight, is_strategy_active

# Import Pattern Recognition
from candlestick_patterns import (
    is_bullish_pin_bar, is_bearish_pin_bar,
    is_bullish_engulfing, is_bearish_engulfing,
    is_morning_star, is_evening_star,
    is_crt_pattern_mtf
)

REJECTION_STATS = {
    "Pattern Not Found": 0,
    "Low Confidence": 0,
    "HTF Bias Conflict": 0,
    "Price Not In Zone": 0,
    "Trade Conflict": 0,
    "Panic Guard Block": 0, # NEW STAT
    "Other": 0
}

rejected_signals_log = []

def log_rejection(reason, zone_type, zone_price, strategy, trend):
    rejected_signals_log.append({
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "zone_type": zone_type,
        "zone_price": zone_price,
        "strategy": strategy,
        "trend": trend
    })

def is_panic_condition(candles, side):
    """
    Checks if the immediate market action is crashing against the trade.
    Returns: True if we should PANIC and BLOCK the trade.
    """
    if len(candles) < 5: return False
    
    last_c = candles.iloc[-1]
    
    # 1. Calculate Average Body Size (Volatility Baseline)
    bodies = (candles['close'] - candles['open']).abs()
    avg_body = bodies.mean()
    
    # 2. Check Last Candle Characteristics
    current_body = abs(last_c['close'] - last_c['open'])
    is_huge = current_body > (avg_body * 1.5) # Tightened: 2.0 → 1.5 catches displacement earlier
    
    # 3. crash Logic
    if side == "buy":
        # If we want to BUY, but the last candle was HUGE and RED (Crash)
        if is_huge and last_c['close'] < last_c['open']:
            return True
    
    if side == "sell":
        # If we want to SELL, but the last candle was HUGE and GREEN (Pump)
        if is_huge and last_c['close'] > last_c['open']:
            return True
            
    return False

def compute_candlestick_confidence(candles, macd=None, macd_signal=None, rsi=None, vwap=None, atr=None, htf_atr=None, m5_context=None):
    # NOTE: macd, rsi, vwap params kept for API compatibility but no longer scored.
    # Scoring is now: Pattern + M5 Context only.
    score = 0.0
    pattern_info = {"pattern": None, "side": None}
    
    if len(candles) < 3: return 0.0, pattern_info
    
    c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
    
    # --- 1. Pattern Recognition ---
    # Weights are adaptive: static defaults until 10 trades logged, then driven by real win rate.
    if is_bullish_engulfing(c2.open, c2.high, c2.low, c2.close, c3.open, c3.high, c3.low, c3.close):
        pattern_info = {"pattern": "bullish_engulfing", "side": "buy"}
        score += get_pattern_weight("bullish_engulfing", "zone_based")
    elif is_bearish_engulfing(c2.open, c2.high, c2.low, c2.close, c3.open, c3.high, c3.low, c3.close):
        pattern_info = {"pattern": "bearish_engulfing", "side": "sell"}
        score += get_pattern_weight("bearish_engulfing", "zone_based")

    elif is_bullish_pin_bar(c3.open, c3.high, c3.low, c3.close):
        pattern_info = {"pattern": "bullish_pin_bar", "side": "buy"}
        score += get_pattern_weight("bullish_pin_bar", "zone_based")
    elif is_bearish_pin_bar(c3.open, c3.high, c3.low, c3.close):
        pattern_info = {"pattern": "bearish_pin_bar", "side": "sell"}
        score += get_pattern_weight("bearish_pin_bar", "zone_based")

    elif is_morning_star(c1, c2, c3):
        pattern_info = {"pattern": "morning_star", "side": "buy"}
        score += get_pattern_weight("morning_star", "zone_based")
    elif is_evening_star(c1, c2, c3):
        pattern_info = {"pattern": "evening_star", "side": "sell"}
        score += get_pattern_weight("evening_star", "zone_based")

    if not pattern_info["side"]: return 0.0, pattern_info

    # 🧠 PATTERN KILL SWITCH — disabled per backtest evidence
    # morning_star: 17% WR on XAUUSDz across 5 years (12 trades, -$2101)
    # bearish_pin_bar: 0% WR (2 trades — small sample but consistent failure)
    # To re-enable a pattern, remove it from this set and re-backtest.
    DISABLED_PATTERNS = {"morning_star", "bearish_pin_bar"}
    if pattern_info.get("pattern") in DISABLED_PATTERNS:
        return 0.0, {"pattern": None, "side": None}

    # --- 2. Confluence Checks ---
    side = pattern_info["side"]
    
    if m5_context:
        m5_trend = m5_context.get('trend')
        if (side == "buy" and m5_trend == "uptrend") or (side == "sell" and m5_trend == "downtrend"):
            score += 0.10
        elif (side == "buy" and m5_trend == "downtrend") or (side == "sell" and m5_trend == "uptrend"):
            score -= 0.15 

    return min(1.0, score), pattern_info


def run_trade_decision_engine(
    symbol, point, current_price, trend, demand_zones, supply_zones,
    fast_demand_zones=[], fast_supply_zones=[],
    m1_candles_for_crt=None, m5_candles_for_patterns=None,
    active_trades=None, zone_touch_counts=None, SL_BUFFER=0, TP_RATIO=1.5, CHECK_RANGE=0, LOT_SIZE=0.01, MAGIC=0,
    strategy_mode="trend_follow",
    macd=None, macd_signal=None, rsi=None, vwap=None, atr=None,htf_atr=None,
    m5_context=None, htf_high=None, htf_low=None, last_closed_h1=None, 
    fibo_zone=None, bollinger_bands=None, htf_bias="NEUTRAL", thresholds={},
    adr_pct=0.0 # 🚀 ADDED ADR INPUT
):
    signals = []
    T_CONF = thresholds.get('MIN_CONFIDENCE_FOR_TRADE', 0.60)
    T_CRT_MOM = thresholds.get('CRT_MIN_MOMENTUM', 0.25)
    
    # --- 1. Layer 1 Logic (Original) ---
    try:
        if len(m1_candles_for_crt) >= 3 and htf_high and htf_low:
            c2, c3 = m1_candles_for_crt.iloc[-2], m1_candles_for_crt.iloc[-1]
            crt_sig = is_crt_pattern_mtf(c2, c3, htf_high, htf_low, min_momentum=T_CRT_MOM)
            
            if crt_sig:
                if (htf_bias == "UP" and crt_sig['side'] == "buy") or \
                   (htf_bias == "DOWN" and crt_sig['side'] == "sell"):
                    
                    # 🛡️ PANIC CHECK 🛡️
                    if is_panic_condition(m5_candles_for_patterns, crt_sig['side']):
                         log_rejection("Panic Guard Block", "Structure", htf_high, strategy_mode, trend)
                         REJECTION_STATS["Panic Guard Block"] += 1
                    else:
                        signals.append({
                            "side": crt_sig['side'],
                            "entry": crt_sig['entry_trigger'],
                            "sl": crt_sig['sl'],
                            "tp": crt_sig['tp'],
                            "zone": "MTF_Structure",
                            "strategy": "MTF_CRT",
                            "reason": crt_sig['pattern'],
                            "confidence": 0.95
                        })
                        return signals, [] 
    except Exception:
        pass

    # --- 2. Zone-Based Logic ---
    all_zones = [("demand", demand_zones), ("supply", supply_zones)]
    
    if len(m5_candles_for_patterns) < 5: return [], []
    c_last = m5_candles_for_patterns.iloc[-1]
    
    for zone_type, zones in all_zones:
        desired_side = "buy" if zone_type == "demand" else "sell"
        
        if htf_bias == "UP" and desired_side == "sell": 
            log_rejection("HTF Bias Conflict", zone_type, None, strategy_mode, trend)
            REJECTION_STATS["HTF Bias Conflict"]+= 1; continue
        if htf_bias == "DOWN" and desired_side == "buy": 
            log_rejection("HTF Bias Conflict", zone_type, None, strategy_mode, trend)
            REJECTION_STATS["HTF Bias Conflict"]+= 1; continue
        
        for zone in zones:
            zone_top, zone_bottom = zone.get("top"), zone.get("bottom")
            if not zone_top or not zone_bottom: continue

            z_price = (zone_top + zone_bottom) / 2
            zone_width = abs(zone_top - zone_bottom)

            # 🧠 ZONE STRENGTH FILTER — skip thin zones with no structure
            atr_val_now = atr if (atr and not math.isnan(atr)) else (current_price * 0.0005)
            if zone_width < atr_val_now * 0.5:
                continue

            # 🧠 STRUCTURE FILTER — zone must have between 1 and MAX_TOUCH_ALLOWED touches
            # < 1 = untested, no edge proven yet
            # > max = overused zone, institutional liquidity likely exhausted
            zone_touches = zone.get("touches", 0)
            max_touches  = thresholds.get("MAX_TOUCH_ALLOWED", 3)
            if zone_touches < 1 or zone_touches > max_touches:
                continue

            buffer = max(htf_atr * 0.5, zone_width * 0.25) if (htf_atr and not math.isnan(htf_atr)) else zone_width * 0.25

            in_zone = (zone_bottom - buffer) <= current_price <= (zone_top + buffer)
            REJECTION_STATS["Price Not In Zone"] += 1

            if not in_zone: continue
            # Pattern Check
            confidence, p_info = compute_candlestick_confidence(
                m5_candles_for_patterns,
                macd=macd[-1] if macd is not None else None,
                macd_signal=macd_signal[-1] if macd_signal is not None else None,
                rsi=rsi[-1] if rsi is not None else None,
                vwap=vwap, atr=atr, m5_context=m5_context
            )

            if not p_info["side"] or p_info['side'] != desired_side:
                log_rejection("Pattern Not Found", zone_type, z_price, strategy_mode, trend)
                REJECTION_STATS["Pattern Not Found"] += 1; continue

            if confidence < T_CONF:
                log_rejection("Low Confidence", zone_type, z_price, strategy_mode, trend)
                REJECTION_STATS["Low Confidence"] += 1; continue

            # 🛡️ PANIC CHECK 🛡️
            if is_panic_condition(m5_candles_for_patterns, desired_side):
                log_rejection("Panic Guard Block", zone_type, z_price, strategy_mode, trend)
                REJECTION_STATS["Panic Guard Block"] += 1
                continue

            # 🧠 CONFIRMATION ENTRY — only enter AFTER candle confirms rejection
            # Price must have already shown direction — not predictive guessing
            if desired_side == "buy":
                if c_last.close <= c_last.open:  # Need bullish close to confirm demand
                    log_rejection("Pattern Not Found", zone_type, z_price, strategy_mode, trend)
                    REJECTION_STATS["Pattern Not Found"] += 1; continue
                entry_price = c_last.close
            else:
                if c_last.close >= c_last.open:  # Need bearish close to confirm supply
                    log_rejection("Pattern Not Found", zone_type, z_price, strategy_mode, trend)
                    REJECTION_STATS["Pattern Not Found"] += 1; continue
                entry_price = c_last.close

            # Trade Construction
            atr_val = atr if (atr and not math.isnan(atr)) else (current_price * 0.0005)
            sl_dist = max(atr_val * 1.0, SL_BUFFER)

            if desired_side == "buy":
                sl = zone_bottom - sl_dist
                tp = entry_price + (abs(entry_price - sl) * TP_RATIO)
            else:
                sl = zone_top + sl_dist
                tp = entry_price - (abs(entry_price - sl) * TP_RATIO)

            # 🧠 HARD RR FILTER — only asymmetric trades survive
            # Confirmation entry can shrink TP distance — enforce minimum 1.3R
            rr = abs(tp - entry_price) / abs(entry_price - sl) if abs(entry_price - sl) > 0 else 0
            if rr < 1.3:
                log_rejection("Low Confidence", zone_type, z_price, strategy_mode, trend)
                REJECTION_STATS["Low Confidence"] += 1; continue

            conflict = False
            if active_trades and isinstance(active_trades, dict) and symbol in active_trades:
                if active_trades[symbol]['side'] != desired_side: conflict = True
            if conflict:
                log_rejection("Trade Conflict", zone_type, z_price, strategy_mode, trend)
                REJECTION_STATS["Trade Conflict"] += 1; continue

            # 🧠 KILL SWITCH: Skip if strategy is statistically underperforming
            if not is_strategy_active(strategy_mode):
                log_rejection("Other", zone_type, z_price, strategy_mode, trend)
                REJECTION_STATS["Other"] += 1; continue

            signals.append({
                "side": desired_side,
                "entry": entry_price, "sl": sl, "tp": tp,
                "zone": {"mid": z_price},
                "strategy": strategy_mode,
                "reason": p_info['pattern'],
                "confidence": confidence
            })

    # =================================================================
    # === LAYER 2: MOMENTUM CONTINUATION — DISABLED FOR BACKTESTING ===
    # =================================================================
    # L2 is disabled until zone-based strategy proves edge (PF > 1.2).
    # L2 continuation trades hurt stress PF first — confirmed as a leak.
    # Re-enable by removing the early return below once baseline edge exists.
    if not signals:
        return signals, []

    # --- L2 code preserved below, not reached until re-enabled ---
    if False and not signals and htf_bias != "NEUTRAL":
        L2_ATR_BUFFER  = 0.5
        L2_SL_MULTIPLE = 1.0
        L2_TP_RATIO    = 1.8   # raised from 1.25 — low RR was killing this layer
        L2_CONFIDENCE  = 0.68
        
        if htf_bias == "UP" and trend == "uptrend":
            target_zones = fast_demand_zones; l2_side = "buy"
        elif htf_bias == "DOWN" and trend == "downtrend":
            target_zones = fast_supply_zones; l2_side = "sell"
        else:
            return signals, []

        # 🧠 TRIPLE ALIGNMENT: M5 trend must also agree with L2 direction
        # Without this, L2 chases price into trend exhaustion
        if m5_context:
            m5_trend = m5_context.get('trend')
            if l2_side == "buy"  and m5_trend != "uptrend":   return signals, []
            if l2_side == "sell" and m5_trend != "downtrend": return signals, []

        current_atr = atr if (atr and not math.isnan(atr)) else (current_price * 0.0005)
        
        for zone in target_zones:
            z_price = zone.get("price")
            if not z_price: continue

            if abs(current_price - z_price) > (current_atr * L2_ATR_BUFFER): continue

            # 🧠 ANTI-CHASE FILTER — skip if market already expanded
            # If recent M5 range > 3x ATR, the move is exhausted — no edge left
            if m5_candles_for_patterns is not None and len(m5_candles_for_patterns) >= 5:
                recent_range = m5_candles_for_patterns['high'].max() - m5_candles_for_patterns['low'].min()
                if recent_range > current_atr * 3:
                    continue

            if vwap:
                if l2_side == "buy" and current_price < vwap: continue 
                if l2_side == "sell" and current_price > vwap: continue 

            # 🛡️ PANIC CHECK 🛡️
            if is_panic_condition(m5_candles_for_patterns, l2_side):
                log_rejection("Panic Guard Block", "L2_FastZone", z_price, strategy_mode, trend)
                REJECTION_STATS["Panic Guard Block"] += 1
                continue # Skip

            if len(m1_candles_for_crt) >= 3:
                c2, c3 = m1_candles_for_crt.iloc[-2], m1_candles_for_crt.iloc[-1]
                p_info = is_crt_pattern_mtf(c2, c3, z_price, z_price, min_momentum=0.35)
                
                if p_info and p_info['side'] == l2_side:
                    sl_dist = current_atr * L2_SL_MULTIPLE
                    entry_price = current_price
                    
                    if l2_side == "buy":
                        sl = entry_price - sl_dist
                        tp = entry_price + (sl_dist * L2_TP_RATIO)
                    else:
                        sl = entry_price + sl_dist
                        tp = entry_price - (sl_dist * L2_TP_RATIO)

                    conflict = False
                    if active_trades and isinstance(active_trades, dict) and symbol in active_trades:
                        if active_trades[symbol]['side'] != l2_side: conflict = True
                    if conflict: continue

                    signals.append({
                        "side": l2_side,
                        "entry": entry_price, "sl": sl, "tp": tp,
                        "zone": {"mid": z_price},
                        "strategy": "momentum_continuation_L2",
                        "reason": f"L2_{p_info['pattern']}",
                        "confidence": L2_CONFIDENCE
                    })
                    break 

    return signals, []

def format_confidence_label(score):
    if score >= 0.90: return "💎 ULTRA"
    if score >= 0.80: return "🔥 HIGH"
    if score >= 0.60: return "✅ MODERATE"
    return "⚠️ LOW"

def print_rejection_summary():
    print("\n===== REJECTION SUMMARY =====")
    total = sum(REJECTION_STATS.values())
    for k, v in REJECTION_STATS.items():
        pct = (v / total * 100) if total > 0 else 0
        print(f"{k}: {v} ({pct:.1f}%)")
    print("============================\n")