# ==========================================
# zone_detector.py (Final Upgraded Version)
# High-Performance Institutional Zone Engine
# ==========================================

import numpy as np
import pandas as pd
from numba import jit
from ta.volatility import AverageTrueRange


# ==========================================================
# STRICT ZONE DETECTION (Numba Accelerated)
# ==========================================================

def detect_zones(df, lookback=100, zone_size=5):
    """
    Institutional-grade Supply/Demand Zone Detection
    - Numba-accelerated pivot detection
    - Wick + Body zone construction (full institutional model)
    - ATR-based departure validation
    - Ghost-zone auto-removal
    """

    if df is None or len(df) < zone_size * 2 + 20:
        return [], []

    # ----------- ATR -------------
    try:
        atr_indicator = AverageTrueRange(df['high'], df['low'], df['close'], window=14)
        atr_values = atr_indicator.average_true_range().fillna(0).values
    except Exception:
        atr_values = np.zeros(len(df))

    # ----------- Prepare Numpy Arrays ------------
    highs   = df['high'].values.astype(np.float64)
    lows    = df['low'].values.astype(np.float64)
    opens   = df['open'].values.astype(np.float64)
    closes  = df['close'].values.astype(np.float64)
    times   = df['time'].astype(np.int64).values // 10**9

    # ----------- Run the Numba detector ----------
    demand_rows, supply_rows = _find_zones_numba(
        highs, lows, opens, closes, atr_values, times,
        zone_size=zone_size
    )

    # ----------- Convert back to dict ------------
    demand_zones = []
    for row in demand_rows:
        wick_low, body_top, t = row
        demand_zones.append({
            "type": "demand",
            "price": float(wick_low),
            "bottom": float(wick_low),
            "top": float(body_top),
            "time": pd.to_datetime(t, unit='s')
        })

    supply_zones = []
    for row in supply_rows:
        wick_high, body_bottom, t = row
        supply_zones.append({
            "type": "supply",
            "price": float(wick_high),
            "top": float(wick_high),
            "bottom": float(body_bottom),
            "time": pd.to_datetime(t, unit='s')
        })

    return demand_zones, supply_zones



# ==========================================================
# Numba Core Logic
# ==========================================================

@jit(nopython=True)
def _find_zones_numba(highs, lows, opens, closes, atr, times, zone_size):
    """
    Strict institutional zone logic:
    - Pivot wick detection
    - Body-based zone boundaries
    - ATR × multiplier departure validation
    - Ghost-zone validation (broken zone removal)
    """

    n = len(closes)
    demand_raw = []
    supply_raw = []

    N_DEPARTURE = 3
    ATR_MULT = 1.5

    start = max(zone_size, 20)

    for i in range(start, n - zone_size - N_DEPARTURE):

        h = highs[i]
        l = lows[i]
        o = opens[i]
        c = closes[i]
        a = atr[i]
        t = times[i]

        if a <= 0:
            continue

        # -------------------- PIVOT LOW DETECTION --------------------
        pivot_low = True
        for j in range(1, zone_size + 1):
            if lows[i - j] <= l or lows[i + j] <= l:
                pivot_low = False
                break

        if pivot_low:
            # Evaluate departure strength
            max_dep = highs[i+1]
            for k in range(2, N_DEPARTURE + 1):
                if highs[i+k] > max_dep:
                    max_dep = highs[i+k]

            if (max_dep - l) >= (a * ATR_MULT):
                # Body top (upper body of pivot candle)
                body_top = o if c < o else c
                demand_raw.append((l, body_top, t, i))

        # -------------------- PIVOT HIGH DETECTION --------------------
        pivot_high = True
        for j in range(1, zone_size + 1):
            if highs[i - j] >= h or highs[i + j] >= h:
                pivot_high = False
                break

        if pivot_high:
            min_dep = lows[i+1]
            for k in range(2, N_DEPARTURE + 1):
                if lows[i+k] < min_dep:
                    min_dep = lows[i+k]

            if (h - min_dep) >= (a * ATR_MULT):
                # Body bottom (lower body of pivot candle)
                body_bottom = o if c > o else c
                supply_raw.append((h, body_bottom, t, i))


    # =========== Ghost-Zone Validation ===========
    demand_final = []
    for z in demand_raw:
        wick_low, body_top, t, idx = z
        broken = False
        for k in range(idx+1, n):
            if closes[k] < wick_low:  # demand invalidated
                broken = True
                break
        if not broken:
            demand_final.append((wick_low, body_top, t))

    supply_final = []
    for z in supply_raw:
        wick_high, body_bottom, t, idx = z
        broken = False
        for k in range(idx+1, n):
            if closes[k] > wick_high:  # supply invalidated
                broken = True
                break
        if not broken:
            supply_final.append((wick_high, body_bottom, t))

    return demand_final, supply_final



# ==========================================================
# FAST ZONES (kept, upgraded, safe)
# ==========================================================

def detect_fast_zones(df, point=0.0001, min_cluster=2, lookback=15):

    fast_demand, fast_supply = [], []
    if df is None or len(df) < lookback:
        return [], []

    recent = df.tail(lookback)

    # Robust ATR proxy
    atr_points = (
        recent['close'].diff().abs().rolling(14).mean().iloc[-1]
        if len(recent) >= 14 else None
    )
    if pd.isna(atr_points) or atr_points is None:
        atr_points = point * 20

    proximity = max(atr_points * 1.5, point * 15)

    lows = recent['low'].values
    highs = recent['high'].values

    min_low  = np.min(lows)
    max_high = np.max(highs)

    low_count  = np.sum(np.abs(lows  - min_low)  <= proximity)
    high_count = np.sum(np.abs(highs - max_high) <= proximity)

    last_c = recent['close'].iloc[-1]
    last_l = recent['low'].iloc[-1]
    last_h = recent['high'].iloc[-1]

    # ----------- Fast Demand ------------
    if low_count >= min_cluster:
        if (last_c - last_l) > atr_points * 0.5:
            fast_demand.append({
                "type": "fast_demand",
                "price": float(min_low),
                "time": recent.index[-1]
            })

    # ----------- Fast Supply ------------
    if high_count >= min_cluster:
        if (last_h - last_c) > atr_points * 0.5:
            fast_supply.append({
                "type": "fast_supply",
                "price": float(max_high),
                "time": recent.index[-1]
            })

    return fast_demand, fast_supply



# ==========================================================
# UPDATE / FLIP ZONES (kept, cleaned, safer)
# ==========================================================

def update_zones(zones, current_price, atr, point=0.0001):
    """
    Preserves compatibility with strategy engine.
    Optional place to implement zone weakening or flip logic.
    """

    cleaned = []
    for z in zones:

        # Demand flip check
        if z["type"] == "demand":
            if current_price < (z["bottom"] - atr * 0.5):
                continue  # zone invalidated

        # Supply flip check
        if z["type"] == "supply":
            if current_price > (z["top"] + atr * 0.5):
                continue

        cleaned.append(z)

    return cleaned
