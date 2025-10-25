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
