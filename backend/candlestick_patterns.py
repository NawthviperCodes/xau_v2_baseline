# === candlestick_patterns.py ===
"""
Candlestick pattern detection functions.
Supports body-only and wick-engulfing confirmations.
"""

# --- Bullish Engulfing ---
def is_bullish_engulfing(o1, h1, l1, c1, o2, h2, l2, c2, require_wick=False):
    """
    Strong Bullish engulfing:
    1. Candle 2 body engulfs Candle 1 body.
    2. Candle 2 body is at least 1.5x larger than Candle 1 body (momentum).
    3. Optional: Candle 2 wicks engulf Candle 1 wicks.
    """
    if None in [o1, h1, l1, c1, o2, h2, l2, c2]:
        return False

    body1_size = abs(c1 - o1)
    body2_size = abs(c2 - o2)

    if body1_size == 0: # Cannot engulf a doji body
        return False

    # Body engulf check
    body_engulf = (o2 < c1) and (c2 > o1)
    # Momentum check
    has_momentum = body2_size > (body1_size * 1.5)

    if not (body_engulf and has_momentum):
        return False

    if require_wick:
        return (h2 > h1) and (l2 < l1)
    return True

def is_inside_bar(o1, h1, l1, c1, o2, h2, l2, c2):
    """
    [cite_start]Checks for an Inside Bar (Harami)[cite: 445].
    - c1 is the "mother", c2 is the "baby".
    - Candle 2 High < Candle 1 High
    - Candle 2 Low > Candle 1 Low
    """
    if None in [h1, l1, h2, l2]:
        return False
    
    # Check that the baby (c2) is fully contained within the mother's (c1) wicks
    return (h2 < h1) and (l2 > l1)


def is_inside_bar_false_breakout(o1, h1, l1, c1, o2, h2, l2, c2):
    """
    [cite_start]Checks for an Inside Bar False Breakout (Fakeout / Stop Hunt)[cite: 1498, 1500].
    - c1 is the "mother", c2 is the "fakeout" bar.
    - c2 body must close back inside c1's range (High/Low).
    - c2 must have a long wick poking *outside* c1's range.
    
    Returns: 'buy' (bullish fakeout), 'sell' (bearish fakeout), or None
    """
    if None in [o1, h1, l1, c1, o2, h2, l2, c2]:
        return None

    mother_high = h1
    mother_low = l1
    
    # [cite_start]Check for a Bearish Fakeout (Bull Trap) [cite: 1532]
    # c2 pokes *above* mother_high but *closes* back inside the range
    if (h2 > mother_high) and (c2 < mother_high):
        return "sell"
        
    # Check for a Bullish Fakeout (Bear Trap)
    # c2 pokes *below* mother_low but *closes* back inside the range
    if (l2 < mother_low) and (c2 > mother_low):
        return "buy"
    
    return None

# --- Bearish Engulfing ---
def is_bearish_engulfing(o1, h1, l1, c1, o2, h2, l2, c2, require_wick=False):
    """
    Strong Bearish engulfing:
    1. Candle 2 body engulfs Candle 1 body.
    2. Candle 2 body is at least 1.5x larger than Candle 1 body (momentum).
    3. Optional: Candle 2 wicks engulf Candle 1 wicks.
    """
    if None in [o1, h1, l1, c1, o2, h2, l2, c2]:
        return False
    
    body1_size = abs(c1 - o1)
    body2_size = abs(c2 - o2)

    if body1_size == 0: # Cannot engulf a doji body
        return False

    # Body engulf check
    body_engulf = (o2 > c1) and (c2 < o1)
    # Momentum check
    has_momentum = body2_size > (body1_size * 1.5)

    if not (body_engulf and has_momentum):
        return False

    if require_wick:
        return (h2 > h1) and (l2 < l1)
    return True


# --- Bullish Pin Bar ---
def is_bullish_pin_bar(o, h, l, c):
    """
    Strict Bullish pin bar:
    1. Long lower wick (at least 2x body size).
    2. Small body (less than 1/3 of total candle range).
    3. Tiny upper wick (no more than 1/3 of body size).
    """
    if None in [o, h, l, c]:
        return False
    body = abs(c - o)
    candle_range = h - l

    if body == 0 or candle_range == 0:
        return False

    lower_wick = min(o, c) - l
    upper_wick = h - max(o, c)

    is_long_lower_wick = lower_wick >= 2 * body
    is_small_body = body <= candle_range * 0.33
    is_small_upper_wick = upper_wick <= body * 0.33

    return is_long_lower_wick and is_small_body and is_small_upper_wick


# --- Bearish Pin Bar ---
def is_bearish_pin_bar(o, h, l, c):
    """
    Strict Bearish pin bar:
    1. Long upper wick (at least 2x body size).
    2. Small body (less than 1/3 of total candle range).
    3. Tiny lower wick (no more than 1/3 of body size).
    """
    if None in [o, h, l, c]:
        return False
    body = abs(c - o)
    candle_range = h - l

    if body == 0 or candle_range == 0:
        return False

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    is_long_upper_wick = upper_wick >= 2 * body
    is_small_body = body <= candle_range * 0.33
    is_small_lower_wick = lower_wick <= body * 0.33

    return is_long_upper_wick and is_small_body and is_small_lower_wick

# --- Morning Star ---
def is_morning_star(c1, c2, c3):
    """Morning star: strong bearish → indecision → strong bullish."""
    try:
        return (c1.close < c1.open and
                abs(c1.close - c1.open) > abs(c2.close - c2.open) and
                c3.close > c3.open and
                c3.close > ((c1.open + c1.close) / 2))
    except Exception:
        return False


# --- Evening Star ---
def is_evening_star(c1, c2, c3):
    """Evening star: strong bullish → indecision → strong bearish."""
    try:
        return (c1.close > c1.open and
                abs(c1.close - c1.open) > abs(c2.close - c2.open) and
                c3.close < c3.open and
                c3.close < ((c1.open + c1.close) / 2))
    except Exception:
        return False


# --- Bullish Rectangle ---
def is_bullish_rectangle(candles):
    """Simple bullish rectangle: sideways then breakout up."""
    try:
        closes = [c.close for c in candles]
        return closes[-1] > max(closes[:-1])
    except Exception:
        return False


# --- Bearish Rectangle ---
def is_bearish_rectangle(candles):
    """Simple bearish rectangle: sideways then breakout down."""
    try:
        closes = [c.close for c in candles]
        return closes[-1] < min(closes[:-1])
    except Exception:
        return False

# --- CRT (Candle Range Theory) / Power of 3 ---
def is_crt_pattern(open_p, high, low, close_p, min_momentum=0.5, min_close_pos=0.3):
    """
    Detects a generic CRT expansion candle (large body, closing near high/low).
    """
    if None in [open_p, high, low, close_p]: return None
    
    range_len = high - low
    if range_len == 0: return None
    
    body = abs(close_p - open_p)
    
    # 1. Momentum Check (Body is large relative to range)
    if (body / range_len) < min_momentum: return None
    
    # 2. Bullish CRT
    if close_p > open_p:
        # Close must be in the top % of the wick
        if (high - close_p) <= (range_len * min_close_pos):
            return "buy"
            
    # 3. Bearish CRT
    elif close_p < open_p:
        # Close must be in the bottom % of the wick
        if (close_p - low) <= (range_len * min_close_pos):
            return "sell"
            
    return None

def is_crt_pattern_mtf(m1_c2, m1_c3, htf_high, htf_low, min_momentum=0.25):
    """
    Multi-Timeframe CRT:
    Detects if M1 candle triggers a reversal at HTF Structure (High/Low).
    """
    # Simple logic: Did we sweep the HTF level and close back inside?
    
    # Bearish Sweep (Sweep HTF High)
    if m1_c3.high > htf_high and m1_c3.close < htf_high:
        if m1_c3.close < m1_c3.open: # Bearish candle
            return {
                "pattern": "MTF_CRT_Bearish_Sweep", 
                "side": "sell", 
                "entry_trigger": m1_c3.close,
                "sl": m1_c3.high,
                "tp": m1_c3.close - (m1_c3.high - m1_c3.close) * 2
            }

    # Bullish Sweep (Sweep HTF Low)
    if m1_c3.low < htf_low and m1_c3.close > htf_low:
        if m1_c3.close > m1_c3.open: # Bullish candle
            return {
                "pattern": "MTF_CRT_Bullish_Sweep", 
                "side": "buy", 
                "entry_trigger": m1_c3.close,
                "sl": m1_c3.low,
                "tp": m1_c3.close + (m1_c3.close - m1_c3.low) * 2
            }
            
    return None