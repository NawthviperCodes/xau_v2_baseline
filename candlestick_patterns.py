# === candlestick_patterns.py ===
"""
Candlestick pattern detection functions.
Supports body-only and wick-engulfing confirmations.
"""

# --- Bullish Engulfing ---
def is_bullish_engulfing(o1, h1, l1, c1, o2, h2, l2, c2, require_wick=False):
    """
    Bullish engulfing:
    - Candle 2 (o2→c2) completely engulfs Candle 1 (o1→c1).
    - If require_wick=True → must also engulf high/low (wick engulf).
    """
    if None in [o1, h1, l1, c1, o2, h2, l2, c2]:
        return False

    # Body engulf check
    body_engulf = (o2 < c1) and (c2 > o1) and (abs(c2 - o2) > abs(c1 - o1))
    if not body_engulf:
        return False

    if require_wick:
        return (h2 > h1) and (l2 < l1)
    return True


# --- Bearish Engulfing ---
def is_bearish_engulfing(o1, h1, l1, c1, o2, h2, l2, c2, require_wick=False):
    """
    Bearish engulfing:
    - Candle 2 (o2→c2) completely engulfs Candle 1 (o1→c1).
    - If require_wick=True → must also engulf high/low (wick engulf).
    """
    if None in [o1, h1, l1, c1, o2, h2, l2, c2]:
        return False

    # Body engulf check
    body_engulf = (o2 > c1) and (c2 < o1) and (abs(c2 - o2) > abs(c1 - o1))
    if not body_engulf:
        return False

    if require_wick:
        return (h2 > h1) and (l2 < l1)
    return True


# --- Bullish Pin Bar ---
def is_bullish_pin_bar(o, h, l, c):
    """Bullish pin bar: long lower wick, small body near top."""
    if None in [o, h, l, c]:
        return False
    body = abs(c - o)
    candle_range = h - l
    lower_wick = min(o, c) - l
    return candle_range > 0 and (lower_wick >= 2 * body)


# --- Bearish Pin Bar ---
def is_bearish_pin_bar(o, h, l, c):
    """Bearish pin bar: long upper wick, small body near bottom."""
    if None in [o, h, l, c]:
        return False
    body = abs(c - o)
    candle_range = h - l
    upper_wick = h - max(o, c)
    return candle_range > 0 and (upper_wick >= 2 * body)


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
