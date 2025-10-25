# === trade_decision_engine.py (Probability-based candlestick + indicator confluence + CRT)
# Merged & updated: calibrated confidences, hard rejection for pattern/zone mismatch,
# fixes for NoneType subscripting, CRT behavior preserved (filter-only for strict/trend_follow, override for aggressive).

from datetime import datetime
from telegram_notifier import send_telegram_message
from candlestick_patterns import (
    is_bullish_pin_bar,
    is_bearish_pin_bar,
    is_bullish_engulfing,
    is_bearish_engulfing,
    is_morning_star,
    is_evening_star,
    is_bullish_rectangle,
    is_bearish_rectangle
)
from indicator_filters import macd_cross, rsi_filter, vwap_filter  # keep for compatibility
import pandas as pd
import math

# --- Config ---
REQUIRE_RETEST_FOR_ENGULFING = True   # Set False to disable the retest requirement (quick toggle)

# --- Tunable thresholds (calibrated) ---
MIN_CONFIDENCE_FOR_TRADE = 0.60    # Lowered global floor (from 0.65)
MIN_CONF_TRAD_FOLLOW = 0.60        # trend-follow floor
MIN_CONF_AGGRESSIVE = 0.65         # slightly higher for aggressive
MAX_TOUCH_ALLOWED = 3
MIN_CONF_FOR_TELEGRAM = 0.80       # lowered to 0.70
CRT_MIN_MOMENTUM = 0.25            # Minimum candle body strength (25%)
CRT_MIN_CLOSE_POSITION = 0.3       # How close to extremes (30% from edge)

# Logging & Caching
RESET_BUFFER_POINTS = 1000
rejected_signals_log = []
# runtime cache so we only send CRT alerts once per zone unless changed
_last_crt_alerts = {}  # { "<symbol>:<zone_type>:<zone_price>": { "side": "buy"/"sell", "entry": float, "sl": float, "tp": float } }
# runtime cache so CRT only fires once per symbol (symbol-level CRT)
_last_crt_crt_only = {}  # { "EURUSD": { "side":..., "entry":..., "sl":..., "tp":... } }

# runtime throttle timestamps (UTC)
_last_crt_time = {}  # { "EURUSD": datetime } 
# --- NEW: General signal throttle (for zone-based signals) ---
_last_general_signal_time = {} # { "EURUSD": datetime }

# runtime CRT throttle timestamps (UTC)
_last_crt_time = {}  # { "EURUSD": datetime }


def format_confidence_label(conf):
    if conf >= 0.85:
        return f"{conf:.2f} 🔥 High"
    elif conf >= 0.70:
        return f"{conf:.2f} ⚖️ Medium"
    else:
        return f"{conf:.2f} ❗ Low"


def notify(message: str, channel: bool = False):
    if channel:
        try:
            send_telegram_message(message)
        except Exception as e:
            print(f"[TG FAIL] {e}\nMessage: {message}")
    else:
        print(message)


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
    Handles multiple shapes of active_trades:
      - dict keyed by symbol
      - dict keyed by 'buy'/'sell'
      - list of dicts [{'symbol':..., 'side':...}, ...]
    Returns True if conflict (i.e., there exists an opposite-side open trade for same symbol or a trade on same side if you want to prevent duplicates).
    """
    if not active_trades:
        return False

    # If dict keyed by symbol: e.g. active_trades[symbol] = {...}
    if isinstance(active_trades, dict):
        if symbol in active_trades:
            existing = active_trades[symbol]
            # if stored structure has 'side'
            ex_side = existing.get('side') if isinstance(existing, dict) else None
            if ex_side and ex_side != side:
                return True  # opposite-side already present
            # if ex_side same as side, we consider it a conflict to avoid duplicate
            if ex_side == side:
                return True

        # Also check for buy/sell keys
        if side in active_trades:
            # active_trades['buy'] may be non-empty
            if active_trades.get(side):
                return True

        # Finally, check any dict values list of positions
        for k, v in active_trades.items():
            if isinstance(v, list):
                for pos in v:
                    pos_side = None
                    if isinstance(pos, dict):
                        pos_side = pos.get('side') or pos.get('type')
                    else:
                        # try attribute access
                        pos_side = getattr(pos, 'side', None)
                    if pos_side and pos_side != side and getattr(pos, 'symbol', symbol) == symbol:
                        return True
                    if pos_side == side and getattr(pos, 'symbol', symbol) == symbol:
                        return True
        return False

    # If list of positions
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
                # if any position exists on symbol, treat as conflict
                return True
        return False

    # fallback: no conflict
    return False


# === CRT Filter helper (to reduce micro/noise signals) ===
def crt_filter(symbol, entry, sl, tp, candle_range, atr_value, side, df_like, confidence,
               last_crt_time_dict, min_conf=None, min_lookback=10, min_time_sec=600, point_value=None):
    """
    Filters out micro/noise CRT signals before they are sent/used.

    Parameters:
      - symbol: instrument string
      - entry/sl/tp: float
      - candle_range: float (e.g., high - low of the key candle)
      - atr_value: float or None
      - side: "buy" or "sell"
      - df_like: pandas-like dataframe with 'high' and 'low' columns (should contain at least `min_lookback` rows)
      - confidence: numeric 0..1
      - last_crt_time_dict: dict storing last send times (UTC datetimes)
      - min_conf: minimum confidence required for CRT to be considered (if None, uses MIN_CONF_FOR_TELEGRAM)
      - min_lookback: number of bars to look back for structure check
      - min_time_sec: minimum seconds between CRT alerts for this symbol
      - point_value: instrument price point (tick), used to build min_pip fallback
    Returns:
      - dict with the CRT data if passes filters, else None
    """
    try:
        if min_conf is None:
            min_conf = MIN_CONF_FOR_TELEGRAM

        # 1) Confidence gate
        if confidence < min_conf:
            return None

        # 2) Candle size filter: require meaningful size vs ATR (if ATR provided)
        if atr_value is not None and not pd.isna(atr_value):
            if candle_range < 0.25 * float(atr_value):
                return None
        else:
            # if no ATR, require absolute candle_range > small threshold derived from point or a default
            min_range = point_value * 2 if point_value is not None else 0.0002
            if candle_range < min_range:
                return None

        # 3) Entry/SL/TP distance check: avoid tiny SL/TP
        # min_pip: default 1 * point or 0.0005 for FX
        if point_value is None:
            min_pip = 0.0005
        else:
            min_pip = max(0.0005, float(point_value))
        if abs(entry - sl) < min_pip or abs(tp - entry) < min_pip:
            return None

        # 4) Structure filter: require that entry is beyond recent swing (avoid tiny internal flips)
        try:
            if hasattr(df_like, '__len__') and len(df_like) >= 3:
                lookback = min(min_lookback, len(df_like))
                recent_high = max(df_like['high'].iloc[-lookback:])
                recent_low = min(df_like['low'].iloc[-lookback:])
                if side == "buy":
                    # entry should break above a recent swing high or at least be near it (ensure directional strength)
                    if entry <= recent_high:
                        return None
                else:  # sell
                    if entry >= recent_low:
                        return None
        except Exception:
            # if any error, be conservative and fail-safe and skip
            return None

        # 5) Time/spacing filter (avoid spam within min_time_sec)
        now = datetime.utcnow()
        last_sent = last_crt_time_dict.get(symbol)
        if last_sent is not None:
            delta = (now - last_sent).total_seconds()
            if delta < min_time_sec:
                return None

        # passed all checks
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


# --- NEW: Engulfing retest filter ---
def engulfing_retested(prev_candle, engulf_candle, next_candle, side):
    """
    Confirm that price retested the engulfing body before continuing.
    - prev_candle: the candle being engulfed (object with .open/.close/.high/.low or dict-like)
    - engulf_candle: the engulfing candle (object)
    - next_candle: the candle after engulfing (object)
    - side: "buy" or "sell"
    
    Returns True if next_candle shows a retest into the engulfing body:
      - For a bullish engulfing: next_candle.low <= engulf_body_low
      - For a bearish engulfing: next_candle.high >= engulf_body_high
    """
    try:
        # extract body edges robustly
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


# --- NEW: CRT detection ---
def is_crt_pattern(c1, c2, c3):
    """
    Enhanced CRT with stronger confirmation and corrected TP logic.
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
        
        # Bearish CRT with stronger confirmation
        if h2 > h1 and cl2 <= h1 and cl2 >= l1:
            if cl3 < cl2:
                close_position = (cl3 - l3) / range_3
                if close_position > 0.3 or body_ratio_3 < 0.25:
                    return None
                    
                entry_price = l2
                sl_price = h2
                risk_distance = abs(sl_price - entry_price)
                tp_price = entry_price - risk_distance  # <<< FIX: TP is now 1:1 R:R below entry

                return {
                    "pattern": "crt",
                    "side": "sell",
                    "entry_trigger": entry_price,
                    "sl": sl_price,
                    "tp": tp_price, # <<< FIX
                    "momentum_strength": body_ratio_3
                }

        # Bullish CRT with stronger confirmation
        if l2 < l1 and cl2 >= l1 and cl2 <= h1:
            if cl3 > cl2:
                close_position = (cl3 - l3) / range_3
                if close_position < 0.7 or body_ratio_3 < 0.25:
                    return None
                    
                entry_price = h2
                sl_price = l2
                risk_distance = abs(sl_price - entry_price)
                tp_price = entry_price + risk_distance  # <<< FIX: TP is now 1:1 R:R above entry

                return {
                    "pattern": "crt",
                    "side": "buy", 
                    "entry_trigger": entry_price,
                    "sl": sl_price,
                    "tp": tp_price, # <<< FIX
                    "momentum_strength": body_ratio_3
                }

        return None
    except Exception:
        return None


# --- Candlestick confidence computation (CALIBRATED) ---
def compute_candlestick_confidence(candles, macd=None, macd_signal=None, rsi=None, vwap=None, atr=None, m5_context=None):
    """
    Input:
      - candles: list-like or DataFrame slice where latest is candles[-1]
      - macd, macd_signal, rsi, vwap, atr: indicator arrays/values (may be None)
      - m5_context: dict with 'trend' key if present

    Output:
      - confidence: float 0.0..1.0
      - pattern_info: dict { 'pattern': str, 'side': 'buy'|'sell' or None, 'crt_extra': {...}|None }
    """
    pattern = None
    side = None
    base_conf = 0.0

    # ensure we have at least 3 candles
    try:
        if len(candles) < 3:
            return 0.0, {"pattern": None, "side": None}
    except Exception:
        return 0.0, {"pattern": None, "side": None}

    # If pandas DataFrame slice: convert to list of row-like objects that the candlestick functions expect
    c1 = candles.iloc[-3] if isinstance(candles, (pd.DataFrame, pd.Series)) else candles[-3]
    c2 = candles.iloc[-2] if isinstance(candles, (pd.DataFrame, pd.Series)) else candles[-2]
    c3 = candles.iloc[-1] if isinstance(candles, (pd.DataFrame, pd.Series)) else candles[-1]

    # Extract raw numbers robustly
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

    # --- Pattern base confidence assignments (CALIBRATED) ---
    try:
        if is_morning_star(c1, c2, c3):
            base_conf = max(base_conf, 0.68)  # was 0.72 -> lowered
            pattern = "morning_star"
            side = "buy"
        elif is_evening_star(c1, c2, c3):
            base_conf = max(base_conf, 0.68)
            pattern = "evening_star"
            side = "sell"
    except Exception:
        pass

    try:
        if is_bullish_engulfing(o2, h2, l2, cl2, o3, h3, l3, cl3, require_wick=True):
            base_conf = max(base_conf, 0.72) # Back to a higher value for a strong pattern
            pattern = "bullish_engulfing"
            side = "buy"
        elif is_bearish_engulfing(o2, h2, l2, cl2, o3, h3, l3, cl3, require_wick=True):
            base_conf = max(base_conf, 0.72) # Back to a higher value for a strong pattern
            pattern = "bearish_engulfing"
            side = "sell"
    except Exception:
        pass

    try:
        if is_bullish_pin_bar(o3, h3, l3, cl3):
            base_conf = max(base_conf, 0.70) # Increased value for a strict pin bar
            pattern = "bullish_pin_bar"
            side = "buy"
        elif is_bearish_pin_bar(o3, h3, l3, cl3):
            base_conf = max(base_conf, 0.70) # Increased value for a strict pin bar
            pattern = "bearish_pin_bar"
            side = "sell"
    except Exception:
        pass

    try:
        if len(candles) >= 5:
            if is_bullish_rectangle(candles[-5:]):
                base_conf = max(base_conf, 0.50)  # lowered from 0.58
                pattern = "bullish_rectangle"
                side = "buy"
            elif is_bearish_rectangle(candles[-5:]):
                base_conf = max(base_conf, 0.50)
                pattern = "bearish_rectangle"
                side = "sell"
    except Exception:
        pass

    # --- CRT (Candle Range Theory) ---
    crt_extra = None
    try:
        crt_signal = is_crt_pattern(c1, c2, c3)
        if crt_signal:
            # Adjust confidence based on momentum strength (calibrated)
            momentum = crt_signal.get("momentum_strength", 0.5)
            if momentum > 0.6:   # Strong momentum
                base_conf = max(base_conf, 0.72)  # lowered from 0.80
            elif momentum < 0.3: # Weak momentum  
                base_conf = max(base_conf, 0.60)  # lowered from 0.68
            else:                # Medium momentum
                base_conf = max(base_conf, 0.66)  # lowered from 0.74
            pattern = "crt"
            side = crt_signal["side"]
            crt_extra = crt_signal
    except Exception:
        crt_extra = None

    # If no pattern detected, return 0
    if not pattern or not side:
        return 0.0, {"pattern": None, "side": None}

    # --- Confluence adjustments (small boosts/penalties) ---
    conf = base_conf

    # M5 context: boost when aligned, penalize when opposite (only if provided)
    if m5_context:
        m5_trend = m5_context.get('trend')
        if m5_trend:
            if (side == "buy" and m5_trend == "uptrend") or (side == "sell" and m5_trend == "downtrend"):
                conf += 0.08
            else:
                conf -= 0.08

    # MACD: boost if MACD favors the side
    try:
        if macd is not None and macd_signal is not None and len(macd) > 0 and len(macd_signal) > 0:
            # use last values
            if side == "buy" and macd[-1] > macd_signal[-1]:
                conf += 0.06
            if side == "sell" and macd[-1] < macd_signal[-1]:
                conf += 0.06
            # small penalty if opposite
            if side == "buy" and macd[-1] <= macd_signal[-1]:
                conf -= 0.04
            if side == "sell" and macd[-1] >= macd_signal[-1]:
                conf -= 0.04
    except Exception:
        pass

    # RSI: boost if RSI supports direction (not extreme)
    try:
        if rsi is not None and len(rsi) > 0:
            last_rsi = float(rsi[-1])
            if side == "buy":
                if last_rsi >= 50:
                    conf += 0.04
                elif last_rsi < 30:
                    conf -= 0.08  # oversold weirdness (penalize)
            elif side == "sell":
                if last_rsi <= 50:
                    conf += 0.04
                elif last_rsi > 70:
                    conf -= 0.08
    except Exception:
        pass

    # VWAP: small boost if price is on the right side of VWAP (if provided)
    try:
        if vwap is not None:
            last_price = cl3 if cl3 is not None else _safe_get(c3, 'close')
            if last_price is not None:
                if side == "buy" and last_price >= vwap:
                    conf += 0.03
                if side == "sell" and last_price <= vwap:
                    conf += 0.03
    except Exception:
        pass

    # ATR/distance sanity: penalize if pattern formed far from zone relative to ATR (caller can add zone distance)
    try:
        if atr is not None and not math.isnan(float(atr)):
            distance = abs(cl3 - ((h3 + l3) / 2)) if (h3 is not None and l3 is not None) else 0
            if distance > 3.5 * float(atr):
                conf -= 0.08
            elif distance <= 1.0 * float(atr):
                conf += 0.02
    except Exception:
        pass

    # clamp confidence to [0, 1]
    conf = max(0.0, min(1.0, conf))

    return conf, {"pattern": pattern, "side": side, "crt_extra": crt_extra if pattern == "crt" else None}


# --- Main decision engine (updated with Hard Rejection) ---
def run_trade_decision_engine(
    symbol,
    point,
    current_price,
    trend,
    demand_zones,
    supply_zones,
    last3_candles,
    active_trades,
    zone_touch_counts,
    SL_BUFFER, # NOTE: legacy param kept for compatibility
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
    m5_context=None
):
    """
    Returns:
      - signals: list of orders (dict) with keys: side, entry, sl, tp, zone, lot, strategy, reason, confidence
      - flipped_zones: (kept for compatibility)
    """
    signals = []
    flipped_zones = []

    # Combine all zones for structural TP search
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

        # --- Stricter Check for Trend-Follow Mode (Hard Gate) ---
        if trend_type == "trend_follow":
            if side == "buy" and m5_trend != "uptrend":
                return False
            if side == "sell" and m5_trend != "downtrend":
                return False
            return True

        # --- Original logic for aggressive/counter-trend ---
        if is_fast_zone:
            if side == "buy" and m5_trend == "downtrend":
                return False
            if side == "sell" and m5_trend == "uptrend":
                return False
            return True

        if trend_type == "counter_trend":
            if side == "buy":
                return m5_trend == "uptrend"
            if side == "sell":
                return m5_trend == "downtrend"
        return False

    def update_touch_count(zone_price, candle_time, in_zone, min_time_gap_sec=30):
        if zone_price not in zone_touch_counts:
            zone_touch_counts[zone_price] = {
                'count': 0,
                'last_touch_time': candle_time,
                'was_outside_zone': True
            }
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
        # min_dist in price points (caller uses point)
        if trend_ == "uptrend" and (candle_.close - zone_price_) > min_dist:
            return True
        elif trend_ == "downtrend" and (zone_price_ - candle_.close) > min_dist:
            return True
        return False

    def is_valid_engulfing(prev, curr, direction):
        # re-use earlier logic (body engulfing)
        try:
            body_prev = abs(prev.close - prev.open) if hasattr(prev, 'close') else abs(prev['close'] - prev['open'])
            body_curr = abs(curr.close - curr.open) if hasattr(curr, 'close') else abs(curr['close'] - curr['open'])
        except Exception:
            return False
        if body_prev == 0:
            return False
        if direction == "bullish":
            return (curr.open < prev.close) and (curr.close > prev.open) and (body_curr > body_prev)
        elif direction == "bearish":
            return (curr.open > prev.close) and (curr.close < prev.open) and (body_curr > body_prev)
        return False

    def build_entry(side, candle, prev_candle, zone_price, lot_size, atr_value, point_value, all_zones):
        # --- 1. Dynamic SL Calculation (Mandatory ATR usage) ---
        ATR_SL_MULTIPLIER = 2.0  # 2x ATR for SL distance
        entry_price = getattr(candle, 'close', candle['close'])

        if atr_value is None or pd.isna(atr_value) or atr_value <= 0:
            MIN_ABS_SL_DISTANCE = 150 * point_value
            if side == "buy":
                wick_sl = entry_price - MIN_ABS_SL_DISTANCE
            else:
                wick_sl = entry_price + MIN_ABS_SL_DISTANCE
        else:
            sl_distance = float(atr_value) * ATR_SL_MULTIPLIER
            if side == "buy":
                recent_low = min(getattr(candle, 'low', candle['low']), getattr(prev_candle, 'low', prev_candle['low']))
                wick_sl = recent_low - sl_distance
            else:
                recent_high = max(getattr(candle, 'high', candle['high']), getattr(prev_candle, 'high', prev_candle['high']))
                wick_sl = recent_high + sl_distance

        # --- 2. Dynamic TP Calculation (Structural / Volatility-Adjusted) ---
        risk_pips = abs(entry_price - wick_sl)
        BASE_TP_RATIO = 2.0

        opposing_zone_type = "supply" if side == "buy" else "demand"
        opposing_zones = [z for z in all_zones if opposing_zone_type in z['type']]

        tp_structural = None
        min_tp_dist = float('inf')
        for z in opposing_zones:
            dist = abs(z['price'] - entry_price)
            if dist > 0 and dist < min_tp_dist:
                min_tp_dist = dist
                tp_structural = z['price']

        tp_atr_ratio = entry_price + BASE_TP_RATIO * risk_pips if side == "buy" else entry_price - BASE_TP_RATIO * risk_pips

        if tp_structural is not None:
            if abs(tp_structural - entry_price) >= risk_pips:
                if side == "buy" and tp_structural < tp_atr_ratio and abs(tp_structural - entry_price) > risk_pips * 1.5:
                    tp = tp_structural
                elif side == "sell" and tp_structural > tp_atr_ratio and abs(tp_structural - entry_price) > risk_pips * 1.5:
                    tp = tp_structural
                else:
                    tp = tp_atr_ratio
            else:
                tp = tp_atr_ratio
        else:
            tp = tp_atr_ratio

        return {
            "side": side,
            "entry": entry_price,
            "sl": wick_sl,
            "tp": tp,
            "zone": zone_price,
            "lot": lot_size,
            "strategy": strategy_mode
        }

    # --- Extract candles and context ---
    # Keep compatibility with your existing DataFrame usage
    try:
        demand_price_check = last3_candles['low'].iloc[-2]
        supply_price_check = last3_candles['high'].iloc[-2]
        candle_time = last3_candles['time'].iloc[-1]
    except Exception:
        # fallback safe defaults
        demand_price_check = float(last3_candles['low'].iloc[-1]) if 'low' in last3_candles else 0.0
        supply_price_check = float(last3_candles['high'].iloc[-1]) if 'high' in last3_candles else 0.0
        candle_time = datetime.utcnow()

    candles = last3_candles.tail(5)
    c1 = candles.iloc[-3]
    c2 = candles.iloc[-2]
    c3 = candles.iloc[-1]
    candle = c3
    prev_candle = c2

    all_zones = [("demand", demand_zones), ("supply", supply_zones)]

    # --- CRT handling ---
    crt_signal = None
    try:
        crt_signal = is_crt_pattern(c1, c2, c3)
    except Exception:
        crt_signal = None

    if crt_signal is not None:
        raw_entry = crt_signal.get("entry_trigger", getattr(c3, 'close', c3['close']))
        raw_sl = crt_signal.get("sl", getattr(c3, 'close', c3['close']))
        raw_tp = crt_signal.get("tp", getattr(c3, 'close', c3['close']))

        entry_buffer = point * 5
        if crt_signal.get("side") == "buy":
            raw_entry += entry_buffer
        elif crt_signal.get("side") == "sell":
            raw_entry -= entry_buffer

        try:
            cr_h = _safe_get(c2, 'high', _safe_get(c2, 'High', None))
            cr_l = _safe_get(c2, 'low', _safe_get(c2, 'Low', None))
            candle_range_value = abs(cr_h - cr_l) if (cr_h is not None and cr_l is not None) else abs(_safe_get(c2, 'close', 0) - _safe_get(c2, 'open', 0))
        except Exception:
            candle_range_value = abs(_safe_get(c2, 'close', 0) - _safe_get(c2, 'open', 0))

        temp_order = {
            "side": crt_signal.get("side"),
            "entry": raw_entry,
            "sl": raw_sl,
            "tp": raw_tp,
            "zone": None,
            "lot": LOT_SIZE,
            "strategy": strategy_mode,
            "reason": "crt",
            "confidence": 0.75
        }

        try:
            crt_conf, _ = compute_candlestick_confidence(
                candles,
                macd=macd,
                macd_signal=macd_signal,
                rsi=rsi,
                vwap=vwap,
                atr=atr,
                m5_context=m5_context
            )
            temp_order["confidence"] = crt_conf if crt_conf and crt_conf > 0 else temp_order["confidence"]
        except Exception:
            pass

        crt_pass = crt_filter(
            symbol=symbol,
            entry=float(temp_order["entry"]),
            sl=float(temp_order["sl"]),
            tp=float(temp_order["tp"]),
            candle_range=float(candle_range_value),
            atr_value=atr,
            side=temp_order["side"],
            df_like=last3_candles,
            confidence=temp_order["confidence"],
            last_crt_time_dict=_last_crt_time,
            min_conf=None,
            min_lookback=10,
            min_time_sec=1800,
            point_value=point
        )

        if crt_pass and strategy_mode == "aggressive":
            key = symbol
            current_state = {
                "side": temp_order['side'],
                "entry": float(temp_order['entry']),
                "sl": float(temp_order['sl']),
                "tp": float(temp_order['tp'])
            }
            last = _last_crt_crt_only.get(key)
            if last != current_state:
                notify(
                    f"📥 CRT Alert (AGGRESSIVE): {symbol} pattern detected | {temp_order['side'].upper()} idea\n"
                    f"   🔹 Entry: {temp_order['entry']:.5f}\n"
                    f"   🔹 SL: {temp_order['sl']:.5f}\n"
                    f"   🔹 TP: {temp_order['tp']:.5f}\n"
                    f"   🔹 Confidence: {format_confidence_label(temp_order['confidence'])}",
                    channel=True
                )
                _last_crt_crt_only[key] = current_state

            signals.append({
                "side": temp_order['side'],
                "entry": temp_order['entry'],
                "sl": temp_order['sl'],
                "tp": temp_order['tp'],
                "zone": None,
                "lot": LOT_SIZE,
                "strategy": strategy_mode,
                "reason": "crt",
                "confidence": temp_order['confidence']
            })

            return signals, flipped_zones

        if crt_pass:
            key = f"{symbol}:CRT"
            current_state = {
                "side": temp_order['side'],
                "entry": float(temp_order['entry']),
                "sl": float(temp_order['sl']),
                "tp": float(temp_order['tp'])
            }
            last = _last_crt_alerts.get(key)
            if last != current_state:
                notify(
                    f"📥 CRT Alert: {symbol} pattern detected | {temp_order['side'].upper()} idea\n"
                    f"   🔹 Entry: {temp_order['entry']:.5f}\n"
                    f"   🔹 SL: {temp_order['sl']:.5f}\n"
                    f"   🔹 TP: {temp_order['tp']:.5f}\n"
                    f"   🔹 Confidence: {format_confidence_label(temp_order['confidence'])}",
                    channel=True
                )
                _last_crt_alerts[key] = current_state

    # --- Zone-based patterns (engulfing, pin bars, rectangles, etc.) ---
    entry_buffer = point * 5  # 5 pip buffer

    for zone_type, zones in all_zones:
        for zone in list(zones):
            zone_price = zone['price']
            is_fast = "fast" in str(zone.get('type', '')).lower()
            lot_size = LOT_SIZE / 2 if is_fast else LOT_SIZE

            dist = abs(demand_price_check - zone_price) if zone_type == "demand" else abs(supply_price_check - zone_price)
            in_zone = dist < CHECK_RANGE
            touch_number = update_touch_count(zone_price, candle_time, in_zone)

            # skip if too many touches or not touched yet
            if touch_number is None or touch_number == 0:
                continue
            if touch_number and touch_number > MAX_TOUCH_ALLOWED:
                log_rejection("too many touches", zone_type, zone_price, strategy_mode, trend)
                continue

            trade_trend_type = "trend_follow" if (
                (zone_type == "demand" and trend == "uptrend") or
                (zone_type == "supply" and trend == "downtrend")
            ) else "counter_trend"

            if strategy_mode == "trend_follow":
                if (zone_type == "demand" and trend != "uptrend") or (zone_type == "supply" and trend != "downtrend"):
                    log_rejection("trend mismatch", zone_type, zone_price, strategy_mode, trend)
                    continue

            # --- Compute candlestick confidence + pattern info ---
            cand_conf, pattern_info = compute_candlestick_confidence(
                candles,
                macd=macd,
                macd_signal=macd_signal,
                rsi=rsi,
                vwap=vwap,
                atr=atr,
                m5_context=m5_context
            )
            
            # ==========================================================
            # === NEW: Volatility/Momentum Filter  ===
            # ==========================================================
            try:
                if atr is not None and not pd.isna(atr) and atr > 0:
                    pattern_candle = c3 # The last candle forms the pattern
                    candle_range = pattern_candle.high - pattern_candle.low
                    # Reject if the candle's total range is less than 70% of the current ATR
                    if candle_range < (atr * 0.7):
                        log_rejection("low_volatility_candle", zone_type, zone_price, strategy_mode, trend)
                        continue # Skip this signal
            except Exception as e:
                # If check fails, log it but don't stop the bot
                log_rejection(f"volatility_filter_exception: {e}", zone_type, zone_price, strategy_mode, trend)
            # ==========================================================
           
           

            desired_side = "buy" if zone_type == "demand" else "sell"
            if not pattern_info or pattern_info.get('side') is None:
                log_rejection("no pattern", zone_type, zone_price, strategy_mode, trend)
                continue

            # --- HARD REJECTION for pattern-zone mismatch ---
            if pattern_info['side'] != desired_side:
                # Immediately reject such signals
                log_rejection("pattern-zone mismatch (HARD REJECT)", zone_type, zone_price, strategy_mode, trend)
                continue  # <-- hard reject (no soft penalty)

            # CRT confluence (if CRT present and not overriding)
            try:
                if crt_signal is not None:
                    if strategy_mode != "aggressive":
                        crt_side = crt_signal.get('side') if isinstance(crt_signal, dict) else None
                        if crt_side and crt_side == pattern_info.get('side'):
                            cand_conf += 0.06
                        else:
                            if crt_side and crt_side != pattern_info.get('side'):
                                cand_conf -= 0.06
            except Exception:
                pass

            # M5 soft gate
            if not m5_agrees_with_entry(pattern_info['side'], trade_trend_type, is_fast):
                log_rejection("M5 disagreement", zone_type, zone_price, strategy_mode, trend)
                continue

            # Strategy-specific indicator hard filters (aggressive mode)
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
                except Exception:
                    pass

                try:
                    if macd is not None and macd_signal is not None and len(macd) > 0 and len(macd_signal) > 0:
                        if pattern_info['side'] == "buy" and macd[-1] <= macd_signal[-1]:
                            log_rejection("MACD not bullish (aggressive)", zone_type, zone_price, strategy_mode, trend)
                            continue
                        if pattern_info['side'] == "sell" and macd[-1] >= macd_signal[-1]:
                            log_rejection("MACD not bearish (aggressive)", zone_type, zone_price, strategy_mode, trend)
                            continue
                except Exception:
                    pass

                try:
                    if vwap is not None:
                        last_price = float(_safe_get(c3, 'close', None))
                        if pattern_info['side'] == "buy" and last_price < vwap:
                            log_rejection("Price below VWAP (aggressive buy)", zone_type, zone_price, strategy_mode, trend)
                            continue
                        if pattern_info['side'] == "sell" and last_price > vwap:
                            log_rejection("Price above VWAP (aggressive sell)", zone_type, zone_price, strategy_mode, trend)
                            continue
                except Exception:
                    pass

            # Final required confidence depending on strategy (use calibrated thresholds)
            required_conf = MIN_CONFIDENCE_FOR_TRADE
            if strategy_mode == "trend_follow":
                required_conf = MIN_CONF_TRAD_FOLLOW
            elif strategy_mode == "aggressive":
                required_conf = MIN_CONF_AGGRESSIVE

            # final clamp
            cand_conf = max(0.0, min(1.0, cand_conf))

            # If confidence below required, reject
            if cand_conf < required_conf:
                log_rejection(f"low_confidence_{cand_conf:.2f}", zone_type, zone_price, strategy_mode, trend)
                continue

            # Check active trades for conflicts (avoid opening opposing hedged positions)
            conflict = _active_trade_conflict(active_trades, symbol, pattern_info['side'])
            if conflict:
                log_rejection("active_trade_conflict", zone_type, zone_price, strategy_mode, trend)
                continue

            # Engulfing retest requirement
            if REQUIRE_RETEST_FOR_ENGULFING and pattern_info.get('pattern') in ["bullish_engulfing", "bearish_engulfing"]:
                try:
                    next_candle = None
                    if len(last3_candles) > 3:
                        try:
                            idx = list(last3_candles.index).index(c3.name)
                            next_idx = idx + 1
                            if next_idx < len(last3_candles):
                                next_candle = last3_candles.iloc[next_idx]
                        except Exception:
                            next_candle = None

                    if next_candle is None:
                        try:
                            idx2 = list(candles.index).index(c3.name)
                            next_idx2 = idx2 + 1
                            if next_idx2 < len(candles):
                                next_candle = candles.iloc[next_idx2]
                        except Exception:
                            next_candle = None

                    if next_candle is None:
                        log_rejection("engulfing_no_next_candle_for_retest", zone_type, zone_price, strategy_mode, trend)
                        continue

                    if not engulfing_retested(prev_candle, candle, next_candle, pattern_info['side']):
                        log_rejection("engulfing_not_retested", zone_type, zone_price, strategy_mode, trend)
                        continue
                except Exception:
                    log_rejection("engulfing_retest_exception", zone_type, zone_price, strategy_mode, trend)
                    continue

            # Passed all checks -> build order
            order = build_entry(
                pattern_info['side'], 
                candle, 
                prev_candle, 
                zone_price, 
                lot_size, 
                atr_value=atr, 
                point_value=point,
                all_zones=all_zones_list
            )
            order["reason"] = pattern_info.get('pattern')
            order["confidence"] = cand_conf

            # Throttle + notify if strong
            MIN_THROTTLE_SEC = 300  # 5 minutes min
            now = datetime.utcnow()
            last_sent = _last_general_signal_time.get(symbol)
            can_send_now = True
            if last_sent:
                time_diff_sec = (now - last_sent).total_seconds()
                if time_diff_sec < MIN_THROTTLE_SEC:
                    can_send_now = False

            if can_send_now and cand_conf >= MIN_CONF_FOR_TELEGRAM:
                notify(
                    f"📥 SIGNAL {symbol} {zone_type.upper()} | {order['side'].upper()} {order['reason']}\n"
                    f"   🔹 Entry: {order['entry']:.5f}\n"
                    f"   🔹 SL: {order['sl']:.5f}\n"
                    f"   🔹 TP: {order['tp']:.5f}\n"
                    f"   🔹 Confidence: {format_confidence_label(cand_conf)}",
                    channel=True
                )
                _last_general_signal_time[symbol] = now

            signals.append(order)

    return signals, flipped_zones
