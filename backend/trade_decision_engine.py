# === trade_decision_engine.py (VIX75 UPGRADES APPLIED) ===
#
# ✅ VIX75 UPGRADE 1: Multi-Timeframe (HTF) Bias
# - The 'run_trade_decision_engine' function now accepts 'htf_bias'.
# - A new master filter is added to block any trade that goes
#   against the H4 trend (e.g., blocks BUYs in an H4 DOWN bias).
#
# ✅ VIX75 UPGRADE 2: Clean Signal System
# - REMOVED all 'send_telegram_message' and 'notify' calls.
# - This file is now silent. It only analyzes and returns signals.
# - The 'scalper_strategy_engine' is now responsible for all Telegram messages.
#
from datetime import datetime
# (We keep 'send_telegram_message' imported *only* because your old
# 'notify' function uses it, but we will comment out the calls)
from telegram_notifier import send_telegram_message 
from candlestick_patterns import (
    is_bullish_pin_bar,
    is_bearish_pin_bar,
    is_bullish_engulfing,
    is_bearish_engulfing,
    is_morning_star,
    is_evening_star,
    is_bullish_rectangle,
    is_bearish_rectangle,
    is_inside_bar,                 
    is_inside_bar_false_breakout   
)
from indicator_filters import macd_cross, rsi_filter, vwap_filter
import pandas as pd
import math

# --- Config ---
REQUIRE_RETEST_FOR_ENGULFING = True   

# --- Tunable thresholds (calibrated) ---
MIN_CONFIDENCE_FOR_TRADE = 0.60    
MIN_CONF_TRAD_FOLLOW = 0.60        
MIN_CONF_AGGRESSIVE = 0.65         
MAX_TOUCH_ALLOWED = 3
MIN_CONF_FOR_TELEGRAM = 0.70 # This is now read by scalper_strategy_engine
CRT_MIN_MOMENTUM = 0.25            
CRT_MIN_CLOSE_POSITION = 0.3       

# Logging & Caching
RESET_BUFFER_POINTS = 1000
rejected_signals_log = []
_last_crt_alerts = {}  
_last_crt_crt_only = {} 
_last_crt_time = {} 
_last_general_signal_time = {}
_last_crt_time = {}


def format_confidence_label(conf):
    """
    Formats confidence score into a human-readable string with emoji.
    (This is now imported by the main engine)
    """
    if conf >= 0.85:
        return f"{conf:.2f} 🔥 High"
    elif conf >= 0.70:
        return f"{conf:.2f} ⚖️ Medium"
    else:
        return f"{conf:.2f} ❗ Low"


def notify(message: str, channel: bool = False):
    """
    VIX75 UPGRADE: This function is now SILENCED.
    All notifications are handled by the main strategy engine.
    """
    # if channel:
    #     try:
    #         send_telegram_message(message) # <-- REMOVED
    #     except Exception as e:
    #         print(f"[TG FAIL] {e}\nMessage: {message}")
    # else:
    print(f"[SILENCED_NOTIFY] {message}") # We print to console for debugging
    pass


# --- Helpers ---
def _safe_get(val, key, default=None):
    """Helper to safely get attribute or dict key from pandas Series or object"""
    try:
        return getattr(val, key)
    except Exception:
        try:
            return val[key]
        except Exception:
            return default


def _active_trade_conflict(active_trades, symbol, side):
    """
    Robust check to determine if an opposite or same-side active trade exists.
    """
    if not active_trades:
        return False

    if isinstance(active_trades, dict):
        if symbol in active_trades:
            existing = active_trades[symbol]
            ex_side = existing.get('side') if isinstance(existing, dict) else None
            if ex_side and ex_side != side:
                return True
            if ex_side == side:
                return True

        if side in active_trades:
            if active_trades.get(side):
                return True

        for k, v in active_trades.items():
            if isinstance(v, list):
                for pos in v:
                    pos_side = None
                    if isinstance(pos, dict):
                        pos_side = pos.get('side') or pos.get('type')
                    else:
                        pos_side = getattr(pos, 'side', None)
                    if pos_side and pos_side != side and getattr(pos, 'symbol', symbol) == symbol:
                        return True
                    if pos_side == side and getattr(pos, 'symbol', symbol) == symbol:
                        return True
        return False

    if isinstance(active_trades, list):
        for pos in active_trades:
            pos_sym = None
            pos_side = None
            if isinstance(pos, dict):
                pos_sym = pos.get('symbol')
                pos_side = pos.get('side')
            else:
                pos_sym = getattr(pos, 'symbol', None)
                pos_side = getattr(pos, 'side', None)
            if pos_sym == symbol:
                return True
        return False

    return False


def crt_filter(symbol, entry, sl, tp, candle_range, atr_value, side, df_like, confidence,
               last_crt_time_dict, min_conf=None, min_lookback=10, min_time_sec=600, point_value=None):
    """
    Filters out micro/noise CRT signals before they are sent/used.
    (This function is unchanged, it's just a filter)
    """
    try:
        if min_conf is None:
            min_conf = MIN_CONF_FOR_TELEGRAM 

        if confidence < min_conf:
            return None

        if atr_value is not None and not pd.isna(atr_value):
            if candle_range < 0.25 * float(atr_value):
                return None
        else:
            min_range = point_value * 2 if point_value is not None else 0.0002
            if candle_range < min_range:
                return None

        if point_value is None:
            min_pip = 0.0005
        else:
            min_pip = max(0.0005, float(point_value))
        if abs(entry - sl) < min_pip or abs(tp - entry) < min_pip:
            return None

        try:
            if hasattr(df_like, '__len__') and len(df_like) >= 3:
                lookback = min(min_lookback, len(df_like))
                recent_high = max(df_like['high'].iloc[-lookback:])
                recent_low = min(df_like['low'].iloc[-lookback:])
                if side == "buy":
                    if entry <= recent_high:
                        return None
                else:  # sell
                    if entry >= recent_low:
                        return None
        except Exception:
            return None

        now = datetime.utcnow()
        last_sent = last_crt_time_dict.get(symbol)
        if last_sent is not None:
            delta = (now - last_sent).total_seconds()
            if delta < min_time_sec:
                return None

        last_crt_time_dict[symbol] = now
        return {
            "symbol": symbol,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "side": side,
            "confidence": confidence
        }
    except Exception:
        return None


def engulfing_retested(prev_candle, engulf_candle, next_candle, side):
    """
    Confirm that price retested the engulfing body before continuing.
    (Unchanged)
    """
    try:
        e_open = _safe_get(engulf_candle, 'open', _safe_get(engulf_candle, 'Open', None))
        e_close = _safe_get(engulf_candle, 'close', _safe_get(engulf_candle, 'Close', None))
        n_low = _safe_get(next_candle, 'low', _safe_get(next_candle, 'Low', None))
        n_high = _safe_get(next_candle, 'high', _safe_get(next_candle, 'High', None))

        if e_open is None or e_close is None or n_low is None or n_high is None:
            return False

        if side == "buy":
            body_low = min(e_open, e_close)
            return float(n_low) <= float(body_low)
        elif side == "sell":
            body_high = max(e_open, e_close)
            return float(n_high) >= float(body_high)
        return False
    except Exception:
        return False



def is_crt_pattern(c1, c2, c3):
    """
    Implements Power of Three strategy:
    (Unchanged)
    """
    try:
        o1, h1, l1, cl1 = c1.open, c1.high, c1.low, c1.close
        o2, h2, l2, cl2 = c2.open, c2.high, c2.low, c2.close
        o3, h3, l3, cl3 = c3.open, c3.high, c3.low, c3.close
        
        range_3 = h3 - l3
        if range_3 == 0:
            return None
        body_3 = abs(cl3 - o3)
        body_ratio_3 = body_3 / range_3 if range_3 > 0 else 0
        
        # --- Bearish CRT ---
        if (h2 > h1) and (cl2 <= h1 and cl2 >= l1):
            if cl3 < cl2: 
                close_position = (cl3 - l3) / range_3
                if close_position > 0.3 or body_ratio_3 < 0.25:
                    return None 
                    
                entry_price = cl3
                sl_price = h2
                tp_price = l1

                if sl_price <= entry_price: return None
                if tp_price >= entry_price: return None
                risk = abs(entry_price - sl_price)
                reward = abs(entry_price - tp_price)
                if reward < (risk * 0.9): return None 

                return {
                    "pattern": "crt_power_of_3", 
                    "side": "sell",
                    "entry_trigger": entry_price, 
                    "sl": sl_price,
                    "tp": tp_price,
                    "momentum_strength": body_ratio_3
                }

        # --- Bullish CRT ---
        if (l2 < l1) and (cl2 >= l1 and cl2 <= h1):
            if cl3 > cl2:
                close_position = (cl3 - l3) / range_3
                if close_position < 0.7 or body_ratio_3 < 0.25:
                    return None
                    
                entry_price = cl3
                sl_price = l2
                tp_price = h1
                
                if sl_price >= entry_price: return None
                if tp_price <= entry_price: return None
                risk = abs(entry_price - sl_price)
                reward = abs(entry_price - tp_price)
                if reward < (risk * 0.9): return None

                return {
                    "pattern": "crt_power_of_3", 
                    "side": "buy", 
                    "entry_trigger": entry_price,
                    "sl": sl_price,
                    "tp": tp_price,
                    "momentum_strength": body_ratio_3
                }
    except Exception:
        return None
    return None

def is_crt_pattern_mtf(c2, c3, htf_high, htf_low):
    """
    Implements the multi-timeframe Power of Three strategy.
    (Unchanged)
    """
    try:
        o2, h2, l2, cl2 = c2.open, c2.high, c2.low, c2.close
        o3, h3, l3, cl3 = c3.open, c3.high, c3.low, c3.close

        range_3 = h3 - l3
        if range_3 == 0: return None
        body_3 = abs(cl3 - o3)
        body_ratio_3 = body_3 / range_3 if range_3 > 0 else 0
        
        # --- Bearish CRT (Sell Setup) ---
        if (h2 > htf_high) and (cl2 <= htf_high):
            if cl3 < cl2:
                close_position = (cl3 - l3) / range_3
                if close_position > 0.3 or body_ratio_3 < 0.25:
                    return None
                
                entry_price = cl3
                sl_price = h2
                tp_price = htf_low
                
                if sl_price <= entry_price or tp_price >= entry_price: return None
                risk = abs(entry_price - sl_price)
                reward = abs(entry_price - tp_price)
                if risk == 0 or reward < (risk * 0.9): return None

                return { "pattern": "crt_mtf_sell", "side": "sell", "entry_trigger": entry_price, "sl": sl_price, "tp": tp_price }

        # --- Bullish CRT (Buy Setup) ---
        if (l2 < htf_low) and (cl2 >= htf_low):
            if cl3 > cl2:
                close_position = (cl3 - l3) / range_3
                if close_position < 0.7 or body_ratio_3 < 0.25:
                    return None

                entry_price = cl3
                sl_price = l2
                tp_price = htf_high
                
                if sl_price >= entry_price or tp_price <= entry_price: return None
                risk = abs(entry_price - sl_price)
                reward = abs(entry_price - tp_price)
                if risk == 0 or reward < (risk * 0.9): return None

                return { "pattern": "crt_mtf_buy", "side": "buy", "entry_trigger": entry_price, "sl": sl_price, "tp": tp_price }

    except Exception:
        return None
    return None


# --- Candlestick confidence computation (CALIBRATED) ---
def compute_candlestick_confidence(candles, macd=None, macd_signal=None, rsi=None, vwap=None, atr=None, m5_context=None, last_closed_h1=None):
    """
    (This function is unchanged)
    """
    pattern = None
    side = None
    base_conf = 0.0

    try:
        if len(candles) < 3:
            return 0.0, {"pattern": None, "side": None}
    except Exception:
        return 0.0, {"pattern": None, "side": None}

    c1 = candles.iloc[-3] if isinstance(candles, (pd.DataFrame, pd.Series)) else candles[-3]
    c2 = candles.iloc[-2] if isinstance(candles, (pd.DataFrame, pd.Series)) else candles[-2]
    c3 = candles.iloc[-1] if isinstance(candles, (pd.DataFrame, pd.Series)) else candles[-1]

    o1 = _safe_get(c1, 'open', _safe_get(c1, 'Open', None))
    h1 = _safe_get(c1, 'high', _safe_get(c1, 'High', None))
    l1 = _safe_get(c1, 'low', _safe_get(c1, 'Low', None))
    cl1 = _safe_get(c1, 'close', _safe_get(c1, 'Close', None))
    o2 = _safe_get(c2, 'open', _safe_get(c2, 'Open', None))
    h2 = _safe_get(c2, 'high', _safe_get(c2, 'High', None))
    l2 = _safe_get(c2, 'low', _safe_get(c2, 'Low', None))
    cl2 = _safe_get(c2, 'close', _safe_get(c2, 'Close', None))
    o3 = _safe_get(c3, 'open', _safe_get(c3, 'Open', None))
    h3 = _safe_get(c3, 'high', _safe_get(c3, 'High', None))
    l3 = _safe_get(c3, 'low', _safe_get(c3, 'Low', None))
    cl3 = _safe_get(c3, 'close', _safe_get(c3, 'Close', None))

    try:
        if is_morning_star(c1, c2, c3):
            base_conf = max(base_conf, 0.68)
            pattern = "morning_star"
            side = "buy"
        elif is_evening_star(c1, c2, c3):
            base_conf = max(base_conf, 0.68)
            pattern = "evening_star"
            side = "sell"
    except Exception: pass
    try:
        if is_bullish_engulfing(o2, h2, l2, cl2, o3, h3, l3, cl3, require_wick=True):
            base_conf = max(base_conf, 0.72)
            pattern = "bullish_engulfing"
            side = "buy"
        elif is_bearish_engulfing(o2, h2, l2, cl2, o3, h3, l3, cl3, require_wick=True):
            base_conf = max(base_conf, 0.72)
            pattern = "bearish_engulfing"
            side = "sell"
    except Exception: pass
    try:
        if is_bullish_pin_bar(o3, h3, l3, cl3):
            base_conf = max(base_conf, 0.70)
            pattern = "bullish_pin_bar"
            side = "buy"
        elif is_bearish_pin_bar(o3, h3, l3, cl3):
            base_conf = max(base_conf, 0.70)
            pattern = "bearish_pin_bar"
            side = "sell"
    except Exception: pass
    try:
        if len(candles) >= 5:
            if is_bullish_rectangle(candles[-5:]):
                base_conf = max(base_conf, 0.50)
                pattern = "bullish_rectangle"
                side = "buy"
            elif is_bearish_rectangle(candles[-5:]):
                base_conf = max(base_conf, 0.50)
                pattern = "bearish_rectangle"
                side = "sell"
    except Exception: pass
    try:
        if is_inside_bar(o2, h2, l2, cl2, o3, h3, l3, cl3):
            if m5_context and m5_context.get('trend') == "uptrend":
                base_conf = max(base_conf, 0.65)
                pattern = "inside_bar"
                side = "buy"
            elif m5_context and m5_context.get('trend') == "downtrend":
                base_conf = max(base_conf, 0.65)
                pattern = "inside_bar"
                side = "sell"
            else: pass
    except Exception: pass
    try:
        fakeout_side = is_inside_bar_false_breakout(o2, h2, l2, cl2, o3, h3, l3, cl3)
        if fakeout_side == "buy":
            base_conf = max(base_conf, 0.75)
            pattern = "inside_bar_fakeout_bullish"
            side = "buy"
        elif fakeout_side == "sell":
            base_conf = max(base_conf, 0.75)
            pattern = "inside_bar_fakeout_bearish"
            side = "sell"
    except Exception: pass

    crt_extra = None
    try:
        crt_signal = is_crt_pattern(c1, c2, c3)
        if crt_signal:
            momentum = crt_signal.get("momentum_strength", 0.5)
            if momentum > 0.6: base_conf = max(base_conf, 0.72)
            elif momentum < 0.3: base_conf = max(base_conf, 0.60)
            else: base_conf = max(base_conf, 0.66)
            pattern = "crt"
            side = crt_signal["side"]
            crt_extra = crt_signal
    except Exception:
        crt_extra = None

    if not pattern or not side:
        return 0.0, {"pattern": None, "side": None}

    if last_closed_h1 is not None:
        try:
            h1_is_bullish = float(_safe_get(last_closed_h1, 'close', _safe_get(last_closed_h1, 'Close', None))) > float(_safe_get(last_closed_h1, 'open', _safe_get(last_closed_h1, 'Open', None)))
            h1_is_bearish = float(_safe_get(last_closed_h1, 'close', _safe_get(last_closed_h1, 'Close', None))) < float(_safe_get(last_closed_h1, 'open', _safe_get(last_closed_h1, 'Open', None)))
            
            if side == "buy" and not h1_is_bullish:
                return 0.0, {"pattern": "h1_momentum_misaligned", "side": None} 
            if side == "sell" and not h1_is_bearish:
                return 0.0, {"pattern": "h1_momentum_misaligned", "side": None}
        except Exception: pass

    conf = base_conf

    if m5_context:
        m5_trend = m5_context.get('trend')
        if m5_trend:
            if (side == "buy" and m5_trend == "uptrend") or (side == "sell" and m5_trend == "downtrend"):
                conf += 0.08
            else:
                conf -= 0.08

    try:
        if macd is not None and macd_signal is not None and len(macd) > 0 and len(macd_signal) > 0:
            if side == "buy" and macd[-1] > macd_signal[-1]: conf += 0.06
            if side == "sell" and macd[-1] < macd_signal[-1]: conf += 0.06
            if side == "buy" and macd[-1] <= macd_signal[-1]: conf -= 0.04
            if side == "sell" and macd[-1] >= macd_signal[-1]: conf -= 0.04
    except Exception: pass
    try:
        if rsi is not None and len(rsi) > 0:
            last_rsi = float(rsi[-1])
            if side == "buy":
                if last_rsi >= 50: conf += 0.04
                elif last_rsi < 30: conf -= 0.08
            elif side == "sell":
                if last_rsi <= 50: conf += 0.04
                elif last_rsi > 70: conf -= 0.08
    except Exception: pass
    try:
        if vwap is not None:
            last_price = cl3 if cl3 is not None else _safe_get(c3, 'close')
            if last_price is not None:
                if side == "buy" and last_price >= vwap: conf += 0.03
                if side == "sell" and last_price <= vwap: conf += 0.03
    except Exception: pass
    try:
        if atr is not None and not math.isnan(float(atr)):
            distance = abs(cl3 - ((h3 + l3) / 2)) if (h3 is not None and l3 is not None) else 0
            if distance > 3.5 * float(atr): conf -= 0.08
            elif distance <= 1.0 * float(atr): conf += 0.02
    except Exception: pass

    conf = max(0.0, min(1.0, conf))

    return conf, {"pattern": pattern, "side": side, "crt_extra": crt_extra if pattern == "crt" else None}


# --- Main decision engine (VIX75 UPGRADES APPLIED) ---
def run_trade_decision_engine(
    symbol,
    point,
    current_price,
    trend,
    demand_zones,
    supply_zones,
    m1_candles_for_crt,
    m5_candles_for_patterns,
    active_trades,
    zone_touch_counts,
    SL_BUFFER, 
    TP_RATIO,
    CHECK_RANGE,
    LOT_SIZE,
    MAGIC,
    strategy_mode="trend_follow",
    macd=None,
    macd_signal=None,
    rsi=None,
    vwap=None,
    atr=None,
    m5_context=None,
    htf_high=None,  
    htf_low=None,   
    last_closed_h1=None, 
    fibo_zone=None,      
    bollinger_bands=None, 
    htf_bias=None # <-- VIX75 UPGRADE 1: New parameter
):
    """
    Returns:
      - signals: list of orders (dict) with keys: side, entry, sl, tp, zone, lot, strategy, reason, confidence
      - flipped_zones: (kept for compatibility)
    """
    signals = []
    flipped_zones = []

    all_zones_list = list(demand_zones) + list(supply_zones)

    def log_rejection(reason, zone_type, zone_price, strategy_mode_local, trend_context):
        rejected_signals_log.append({
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "zone_type": zone_type,
            "zone_price": zone_price,
            "strategy": strategy_mode_local,
            "trend": trend_context
        })

    def m5_agrees_with_entry(side, trend_type="trend_follow", is_fast_zone=False):
        if not m5_context:
            return True
        m5_trend = m5_context.get("trend")
        if trend_type == "trend_follow":
            if side == "buy" and m5_trend != "uptrend": return False
            if side == "sell" and m5_trend != "downtrend": return False
            return True
        if is_fast_zone:
            if side == "buy" and m5_trend == "downtrend": return False
            if side == "sell" and m5_trend == "uptrend": return False
            return True
        if trend_type == "counter_trend":
            if side == "buy": return m5_trend == "uptrend"
            if side == "sell": return m5_trend == "downtrend"
        return False

    def update_touch_count(zone_price, candle_time, in_zone, min_time_gap_sec=30):
        if zone_price not in zone_touch_counts:
            zone_touch_counts[zone_price] = { 'count': 0, 'last_touch_time': candle_time, 'was_outside_zone': True }
        zone_state = zone_touch_counts[zone_price]
        if isinstance(candle_time, pd.Timestamp):
            candle_time = candle_time.to_pydatetime()
        last_time = zone_state['last_touch_time']
        time_diff = (candle_time - last_time).total_seconds() if last_time else min_time_gap_sec + 1
        if not in_zone:
            zone_state['was_outside_zone'] = True
        if in_zone and zone_state['was_outside_zone'] and time_diff >= min_time_gap_sec:
            zone_state['count'] += 1
            zone_state['last_touch_time'] = candle_time
            zone_state['was_outside_zone'] = False
        return zone_state['count']

    def candle_confirms_breakout(trend_, candle_, zone_price_, min_dist=20):
        if trend_ == "uptrend" and (candle_.close - zone_price_) > min_dist: return True
        elif trend_ == "downtrend" and (zone_price_ - candle_.close) > min_dist: return True
        return False

    def is_valid_engulfing(prev, curr, direction):
        try:
            body_prev = abs(prev.close - prev.open) if hasattr(prev, 'close') else abs(prev['close'] - prev['open'])
            body_curr = abs(curr.close - curr.open) if hasattr(curr, 'close') else abs(curr['close'] - curr['open'])
        except Exception: return False
        if body_prev == 0: return False
        if direction == "bullish":
            return (curr.open < prev.close) and (curr.close > prev.open) and (body_curr > body_prev)
        elif direction == "bearish":
            return (curr.open > prev.close) and (curr.close < prev.open) and (body_curr > body_prev)
        return False

    def build_entry(side, candle, prev_candle, zone_price, lot_size, atr_value, point_value, all_zones):
        ATR_SL_MULTIPLIER = 0.5 
        MIN_ABS_SL_DISTANCE = 50 * point_value
        entry_price = getattr(candle, 'close', candle['close'])
        
        if atr_value is None or pd.isna(atr_value) or atr_value <= 0:
            if side == "buy": wick_sl = getattr(candle, 'low', candle['low']) - MIN_ABS_SL_DISTANCE
            else: wick_sl = getattr(candle, 'high', candle['high']) + MIN_ABS_SL_DISTANCE
        else:
            sl_distance_buffer = float(atr_value) * ATR_SL_MULTIPLIER 
            if side == "buy":
                recent_low = min(getattr(candle, 'low', candle['low']), getattr(prev_candle, 'low', prev_candle['low']))
                wick_sl = recent_low - sl_distance_buffer
            else:
                recent_high = max(getattr(candle, 'high', candle['high']), getattr(prev_candle, 'high', prev_candle['high']))
                wick_sl = recent_high + sl_distance_buffer

        risk_distance = abs(entry_price - wick_sl)
        
        min_sl_dist = point_value * 150 
        if risk_distance < min_sl_dist:
            if side == "buy": wick_sl = entry_price - min_sl_dist
            else: wick_sl = entry_price + min_sl_dist
            risk_distance = abs(entry_price - wick_sl)

        tp_atr_ratio = entry_price + (risk_distance * TP_RATIO) if side == "buy" else entry_price - (risk_distance * TP_RATIO)

        opposing_zone_type = "supply" if side == "buy" else "demand"
        opposing_zones = [z for z in all_zones if opposing_zone_type in z['type']]
        tp_structural = None
        min_tp_dist = float('inf')
        for z in opposing_zones:
            if (side == "buy" and z['price'] > entry_price) or (side == "sell" and z['price'] < entry_price):
                dist = abs(z['price'] - entry_price)
                if dist < min_tp_dist:
                    min_tp_dist = dist
                    tp_structural = z['price']
        
        tp = tp_atr_ratio
        if tp_structural is not None:
            if abs(tp_structural - entry_price) >= risk_distance * 0.9:
                if (side == "buy" and tp_structural < tp_atr_ratio) or \
                   (side == "sell" and tp_structural > tp_atr_ratio):
                    tp = tp_structural
        
        return {
            "side": side, "entry": entry_price, "sl": wick_sl, "tp": tp,
            "zone": zone_price, "lot": lot_size, "strategy": strategy_mode
        }

    # ======================================================
    # ✅ 1. EXTRACT M1 CANDLES (for MTF CRT and M1 CRT)
    # ======================================================
    try:
        if len(m1_candles_for_crt) < 3:
            log_rejection("not_enough_m1_candles", "n/a", 0, strategy_mode, trend)
            return signals, flipped_zones
        c1_m1 = m1_candles_for_crt.iloc[-3] 
        c2_m1 = m1_candles_for_crt.iloc[-2] 
        c3_m1 = m1_candles_for_crt.iloc[-1] 
    except Exception as e:
        log_rejection(f"m1_candle_extraction_failed: {e}", "n/a", 0, strategy_mode, trend)
        return signals, flipped_zones
    
    # ======================================================
    # ✅ 2. EXTRACT M5 CANDLES (for Zone-based Patterns)
    # ======================================================
    try:
        if len(m5_candles_for_patterns) < 5:
            log_rejection("not_enough_m5_candles_for_patterns", "n/a", 0, strategy_mode, trend)
            return signals, flipped_zones
        candles_for_patterns = m5_candles_for_patterns.tail(5)
        c1_pat_m5, c2_pat_m5, c3_pat_m5 = candles_for_patterns.iloc[-3], candles_for_patterns.iloc[-2], candles_for_patterns.iloc[-1]
        candle, prev_candle = c3_pat_m5, c2_pat_m5
        demand_price_check, supply_price_check = c2_pat_m5.low, c2_pat_m5.high
        candle_time = c3_pat_m5.time
        last3_candles, candles = m5_candles_for_patterns.tail(5), m5_candles_for_patterns.tail(5)
        c1, c2, c3 = c1_pat_m5, c2_pat_m5, c3_pat_m5
    except Exception as e:
        log_rejection(f"m5_candle_extraction_failed: {e}", "n/a", 0, strategy_mode, trend)
        return signals, flipped_zones
    
    # ======================================================
    # ✅ 3. PRIORITIZED MULTI-TIMEFRAME CRT STRATEGY (H1 + M1)
    # ======================================================
    crt_signal = None
    if htf_high is not None and htf_low is not None:
        try: crt_signal = is_crt_pattern_mtf(c2_m1, c3_m1, htf_high, htf_low)
        except Exception: crt_signal = None

    if crt_signal is not None:
        
        # --- VIX75 UPGRADE 1: HTF BIAS FILTER ---
        order_side = crt_signal.get("side")
        if (htf_bias == "UP" and order_side == "sell") or (htf_bias == "DOWN" and order_side == "buy"):
            log_rejection("HTF Bias blocks MTF CRT", "crt_mtf", htf_high, strategy_mode, htf_bias)
            # Do not return yet, let M1 CRT or zone logic run
        else:
            # --- CRT Signal is valid, proceed ---
            sl_price = crt_signal.get("sl")
            entry_price = crt_signal.get("entry_trigger")
            atr_buffer = 0.0
            if atr is not None and not pd.isna(atr):
                atr_buffer = float(atr) * 1.0
            if order_side == "buy": sl_price = sl_price - atr_buffer
            else: sl_price = sl_price + atr_buffer
            
            min_sl_dist = point * 150 
            if abs(entry_price - sl_price) < min_sl_dist:
                if order_side == "buy": sl_price = entry_price - min_sl_dist
                else: sl_price = entry_price + min_sl_dist
            
            order = {
                "side": order_side, "entry": entry_price, "sl": sl_price,
                "tp": crt_signal.get("tp"), "zone": None, "lot": LOT_SIZE, 
                "strategy": "crt_mtf", "reason": crt_signal.get("pattern"),
                "confidence": 0.90 # MTF CRT gets high confidence
            }

            conflict = _active_trade_conflict(active_trades, symbol, order['side'])
            if not conflict:
                signals.append(order)

            # 🔸 Immediate return — MTF CRT takes precedence
            return signals, flipped_zones

    all_zones = [("demand", demand_zones), ("supply", supply_zones)]

    # --- CRT handling ---
    crt_signal_m1 = None
    try: crt_signal_m1 = is_crt_pattern(c1_m1, c2_m1, c3_m1)
    except Exception: crt_signal_m1 = None

    if crt_signal_m1 is not None:
        
        # --- VIX75 UPGRADE 1: HTF BIAS FILTER ---
        order_side_m1_crt = crt_signal_m1.get("side")
        if (htf_bias == "UP" and order_side_m1_crt == "sell") or (htf_bias == "DOWN" and order_side_m1_crt == "buy"):
            log_rejection("HTF Bias blocks M1 CRT", "crt_m1", 0, strategy_mode, htf_bias)
        else:
            # --- M1 CRT Signal is valid, proceed ---
            raw_entry = crt_signal_m1.get("entry_trigger", getattr(c3, 'close', c3['close']))
            raw_sl = crt_signal_m1.get("sl", getattr(c3, 'close', c3['close']))
            raw_tp = crt_signal_m1.get("tp", getattr(c3, 'close', c3['close']))
            entry_buffer = point * 5
            if crt_signal_m1.get("side") == "buy": raw_entry += entry_buffer
            elif crt_signal_m1.get("side") == "sell": raw_entry -= entry_buffer

            try:
                cr_h = _safe_get(c2, 'high', _safe_get(c2, 'High', None))
                cr_l = _safe_get(c2, 'low', _safe_get(c2, 'Low', None))
                candle_range_value = abs(cr_h - cr_l) if (cr_h is not None and cr_l is not None) else abs(_safe_get(c2, 'close', 0) - _safe_get(c2, 'open', 0))
            except Exception:
                candle_range_value = abs(_safe_get(c2, 'close', 0) - _safe_get(c2, 'open', 0))

            temp_order = {
                "side": crt_signal_m1.get("side"), "entry": raw_entry, "sl": raw_sl, "tp": raw_tp,
                "zone": None, "lot": LOT_SIZE, "strategy": strategy_mode, "reason": "crt", "confidence": 0.75
            }

            try:
                crt_conf, _ = compute_candlestick_confidence(
                    candles, macd=macd, macd_signal=macd_signal, rsi=rsi,
                    vwap=vwap, atr=atr, m5_context=m5_context,
                    last_closed_h1=last_closed_h1
                )
                temp_order["confidence"] = crt_conf if crt_conf and crt_conf > 0 else temp_order["confidence"]
            except Exception: pass

            crt_pass = crt_filter(
                symbol=symbol, entry=float(temp_order["entry"]), sl=float(temp_order["sl"]), tp=float(temp_order["tp"]),
                candle_range=float(candle_range_value), atr_value=atr, side=temp_order["side"], df_like=last3_candles,
                confidence=temp_order["confidence"], last_crt_time_dict=_last_crt_time,
                min_conf=None, min_lookback=10, min_time_sec=1800, point_value=point
            )

            if crt_pass and strategy_mode == "aggressive":
                key = symbol
                current_state = { "side": temp_order['side'], "entry": float(temp_order['entry']), "sl": float(temp_order['sl']), "tp": float(temp_order['tp']) }
                last = _last_crt_crt_only.get(key)
                if last != current_state:
                    # notify(...) # <-- VIX75 UPGRADE: REMOVED TELEGRAM FLOOD
                    _last_crt_crt_only[key] = current_state

                signals.append(temp_order)
                return signals, flipped_zones # M1 CRT also takes precedence

            if crt_pass:
                key = f"{symbol}:CRT"
                current_state = { "side": temp_order['side'], "entry": float(temp_order['entry']), "sl": float(temp_order['sl']), "tp": float(temp_order['tp']) }
                last = _last_crt_alerts.get(key)
                if last != current_state:
                    # notify(...) # <-- VIX75 UPGRADE: REMOVED TELEGRAM FLOOD
                    _last_crt_alerts[key] = current_state

    # --- Zone-based patterns (engulfing, pin bars, rectangles, etc.) ---
    entry_buffer = point * 5

    for zone_type, zones in all_zones:
        for zone in list(zones):
            zone_price = zone['price']
            is_fast = "fast" in str(zone.get('type', '')).lower()
            lot_size = LOT_SIZE / 2 if is_fast else LOT_SIZE

            # --- VIX75 UPGRADE 1: HTF BIAS FILTER ---
            desired_side = "buy" if zone_type == "demand" else "sell"
            if (htf_bias == "UP" and desired_side == "sell") or (htf_bias == "DOWN" and desired_side == "buy"):
                log_rejection("HTF Bias blocks zone", zone_type, zone_price, strategy_mode, htf_bias)
                continue # This zone is against the H4 trend, skip it
            # --- END OF FILTER ---

            if strategy_mode == "ranging" and bollinger_bands:
                bb_low, bb_high = bollinger_bands.get('demand'), bollinger_bands.get('supply')
                try:
                    if zone_type == "demand" and (bb_low is None or abs(zone_price - bb_low) > (CHECK_RANGE * 2)):
                        log_rejection("ranging_bb_no_confluence", zone_type, zone_price, strategy_mode, trend)
                        continue
                    if zone_type == "supply" and (bb_high is None or abs(zone_price - bb_high) > (CHECK_RANGE * 2)):
                        log_rejection("ranging_bb_no_confluence", zone_type, zone_price, strategy_mode, trend)
                        continue
                except Exception:
                    log_rejection("ranging_bb_exception", zone_type, zone_price, strategy_mode, trend)
                    continue

            dist = abs(demand_price_check - zone_price) if zone_type == "demand" else abs(supply_price_check - zone_price)
            in_zone = dist < CHECK_RANGE
            touch_number = update_touch_count(zone_price, candle_time, in_zone)

            if touch_number is None or touch_number == 0: continue
            if touch_number and touch_number > MAX_TOUCH_ALLOWED:
                log_rejection("too many touches", zone_type, zone_price, strategy_mode, trend)
                continue

            trade_trend_type = "trend_follow" if ((zone_type == "demand" and trend == "uptrend") or (zone_type == "supply" and trend == "downtrend")) else "counter_trend"

            if strategy_mode == "trend_follow":
                if (zone_type == "demand" and trend != "uptrend") or (zone_type == "supply" and trend != "downtrend"):
                    log_rejection("trend mismatch", zone_type, zone_price, strategy_mode, trend)
                    continue

            cand_conf, pattern_info = compute_candlestick_confidence(
                candles_for_patterns, macd=macd, macd_signal=macd_signal, rsi=rsi,
                vwap=vwap, atr=atr, m5_context=m5_context, last_closed_h1=last_closed_h1
            )
            
            try:
                if atr is not None and not pd.isna(atr) and atr > 0:
                    pattern_candle = c3
                    candle_range = pattern_candle.high - pattern_candle.low
                    if candle_range < (atr * 0.7):
                        log_rejection("low_volatility_candle", zone_type, zone_price, strategy_mode, trend)
                        continue 
            except Exception as e:
                log_rejection(f"volatility_filter_exception: {e}", zone_type, zone_price, strategy_mode, trend)

            if not pattern_info or pattern_info.get('side') is None:
                log_rejection("no pattern", zone_type, zone_price, strategy_mode, trend)
                continue

            if pattern_info['side'] != desired_side:
                log_rejection("pattern-zone mismatch (HARD REJECT)", zone_type, zone_price, strategy_mode, trend)
                continue

            try:
                if crt_signal is not None:
                    if strategy_mode != "aggressive":
                        crt_side = crt_signal.get('side') if isinstance(crt_signal, dict) else None
                        if crt_side and crt_side == pattern_info.get('side'): cand_conf += 0.06
                        else:
                            if crt_side and crt_side != pattern_info.get('side'): cand_conf -= 0.06
            except Exception: pass

            if not m5_agrees_with_entry(pattern_info['side'], trade_trend_type, is_fast):
                log_rejection("M5 disagreement", zone_type, zone_price, strategy_mode, trend)
                continue

            if strategy_mode == "aggressive":
                try:
                    if rsi is not None and len(rsi) > 0:
                        last_rsi = float(rsi[-1])
                        if pattern_info['side'] == "buy" and last_rsi < 40:
                            log_rejection("RSI too weak (aggressive buy)", zone_type, zone_price, strategy_mode, trend)
                            continue
                        if pattern_info['side'] == "sell" and last_rsi > 60:
                            log_rejection("RSI too weak (aggressive sell)", zone_type, zone_price, strategy_mode, trend)
                            continue
                except Exception: pass
                try:
                    if macd is not None and macd_signal is not None and len(macd) > 0 and len(macd_signal) > 0:
                        if pattern_info['side'] == "buy" and macd[-1] <= macd_signal[-1]:
                            log_rejection("MACD not bullish (aggressive)", zone_type, zone_price, strategy_mode, trend)
                            continue
                        if pattern_info['side'] == "sell" and macd[-1] >= macd_signal[-1]:
                            log_rejection("MACD not bearish (aggressive)", zone_type, zone_price, strategy_mode, trend)
                            continue
                except Exception: pass
                try:
                    if vwap is not None:
                        last_price = float(_safe_get(c3, 'close', None))
                        if pattern_info['side'] == "buy" and last_price < vwap:
                            log_rejection("Price below VWAP (aggressive buy)", zone_type, zone_price, strategy_mode, trend)
                            continue
                        if pattern_info['side'] == "sell" and last_price > vwap:
                            log_rejection("Price above VWAP (aggressive sell)", zone_type, zone_price, strategy_mode, trend)
                            continue
                except Exception: pass

            order_side = pattern_info.get('side')
            if fibo_zone and order_side:
                try:
                    fibo_min, fibo_max = min(fibo_zone), max(fibo_zone)
                    if fibo_min <= zone_price <= fibo_max:
                        if (order_side == "buy" and trend == "uptrend") or \
                           (order_side == "sell" and trend == "downtrend"):
                            cand_conf += 0.15 
                except Exception: pass

            required_conf = MIN_CONFIDENCE_FOR_TRADE
            if strategy_mode == "trend_follow": required_conf = MIN_CONF_TRAD_FOLLOW
            elif strategy_mode == "aggressive": required_conf = MIN_CONF_AGGRESSIVE
            cand_conf = max(0.0, min(1.0, cand_conf))

            if cand_conf < required_conf:
                log_rejection(f"low_confidence_{cand_conf:.2f}", zone_type, zone_price, strategy_mode, trend)
                continue

            conflict = _active_trade_conflict(active_trades, symbol, pattern_info['side'])
            if conflict:
                log_rejection("active_trade_conflict", zone_type, zone_price, strategy_mode, trend)
                continue

            if REQUIRE_RETEST_FOR_ENGULFING and pattern_info.get('pattern') in ["bullish_engulfing", "bearish_engulfing"]:
                try:
                    next_candle = None
                    if len(last3_candles) > 3:
                        try:
                            idx = list(last3_candles.index).index(c3.name); next_idx = idx + 1
                            if next_idx < len(last3_candles): next_candle = last3_candles.iloc[next_idx]
                        except Exception: next_candle = None
                    if next_candle is None:
                        try:
                            idx2 = list(candles.index).index(c3.name); next_idx2 = idx2 + 1
                            if next_idx2 < len(candles): next_candle = candles.iloc[next_idx2]
                        except Exception: next_candle = None
                    if next_candle is None:
                        log_rejection("engulfing_no_next_candle_for_retest", zone_type, zone_price, strategy_mode, trend)
                        continue
                    if not engulfing_retested(prev_candle, candle, next_candle, pattern_info['side']):
                        log_rejection("engulfing_not_retested", zone_type, zone_price, strategy_mode, trend)
                        continue
                except Exception:
                    log_rejection("engulfing_retest_exception", zone_type, zone_price, strategy_mode, trend)
                    continue

            order = build_entry(
                pattern_info['side'], candle, prev_candle, zone_price, lot_size, 
                atr_value=atr, point_value=point, all_zones=all_zones_list
            )
            order["reason"] = pattern_info.get('pattern')
            order["confidence"] = cand_conf
            
            OPPOSING_ZONE_PROXIMITY = 150 * point
            is_blocked = False
            order_entry, order_side = order['entry'], order['side']

            if order_side == "buy":
                for s_zone in supply_zones:
                    zone_price_supply = s_zone['price']
                    if abs(order_entry - zone_price_supply) < OPPOSING_ZONE_PROXIMITY:
                        is_blocked = True
                        log_rejection(f"blocked_by_opposing_supply_at_{zone_price_supply:.5f}", "supply", zone_price_supply, strategy_mode, trend)
                        break
            elif order_side == "sell":
                for d_zone in demand_zones:
                    zone_price_demand = d_zone['price']
                    if abs(order_entry - zone_price_demand) < OPPOSING_ZONE_PROXIMITY:
                        is_blocked = True
                        log_rejection(f"blocked_by_opposing_demand_at_{zone_price_demand:.5f}", "demand", zone_price_demand, strategy_mode, trend)
                        break
            if is_blocked:
                continue

            # --- VIX75 UPGRADE: Remove all 'notify' and 'send_telegram' calls from here ---
            # The main engine will handle messaging.
            
            signals.append(order)

    return signals, flipped_zones