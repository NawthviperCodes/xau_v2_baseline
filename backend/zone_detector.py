# === zone_detector.py (Forex: Strict + Fast Zones) ===
import pandas as pd
from ta.volatility import AverageTrueRange # <-- ADDED FOR QUALITY CHECK


def detect_zones(df, lookback=100, zone_size=5):
    """
    Detect strong supply and demand zones (pivot-based).
    Works best for longer-term structure levels.
    
    ✅ ENHANCEMENT (Zone Quality):
    - Now includes a "Strength of Departure" filter.
    - A zone is only valid if price moves at least (DEPARTURE_ATR_MULTIPLIER) * ATR
      away from it within (N_CANDLES_FOR_DEPARTURE) candles.
    """
    demand_zones = []
    supply_zones = []

    if df is None or len(df) < (zone_size * 2 + 1) or len(df) < 20: # Need 20 for ATR
        return demand_zones, supply_zones

    # === NEW: Calculate ATR for quality check ===
    try:
        atr = AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
    except Exception as e:
        print(f"[zone_detector] ATR calculation failed: {e}")
        return demand_zones, supply_zones # Return empty if ATR fails

    # === NEW: Quality Check Parameters ===
    N_CANDLES_FOR_DEPARTURE = 3
    DEPARTURE_ATR_MULTIPLIER = 2.0 # Must move 2x ATR to be considered "explosive"

    # Ensure ATR calculation is complete before iterating
    df = df.copy()
    df['atr'] = atr
    
    # Start loop later to ensure ATR has valid data
    start_index = max(zone_size, 14) # Start after ATR calculation period

    for i in range(start_index, len(df) - zone_size - N_CANDLES_FOR_DEPARTURE):
        candle = df.iloc[i]
        prev_candles = df.iloc[i - zone_size:i]
        next_candles = df.iloc[i + 1:i + 1 + zone_size]
        
        atr_at_pivot = candle['atr']
        if pd.isna(atr_at_pivot) or atr_at_pivot == 0:
            continue # Skip if ATR is invalid

        # === 1. Find Strict Demand Zone (pivot low) ===
        if (
            all(candle.low < x.low for x in prev_candles.itertuples()) and
            all(candle.low < x.low for x in next_candles.itertuples())
        ):
            # === 2. Quality Check: Strength of Departure ===
            departure_candles = df.iloc[i + 1 : i + 1 + N_CANDLES_FOR_DEPARTURE]
            max_high_after_pivot = departure_candles['high'].max()
            
            # Check if price moved up explosively
            if (max_high_after_pivot - candle.low) > (atr_at_pivot * DEPARTURE_ATR_MULTIPLIER):
                demand_zones.append({
                    "type": "demand",
                    "price": float(candle.low),
                    "time": candle.time
                })

        # === 1. Find Strict Supply Zone (pivot high) ===
        if (
            all(candle.high > x.high for x in prev_candles.itertuples()) and
            all(candle.high > x.high for x in next_candles.itertuples())
        ):
            # === 2. Quality Check: Strength of Departure ===
            departure_candles = df.iloc[i + 1 : i + 1 + N_CANDLES_FOR_DEPARTURE]
            min_low_after_pivot = departure_candles['low'].min()
            
            # Check if price moved down explosively
            if (candle.high - min_low_after_pivot) > (atr_at_pivot * DEPARTURE_ATR_MULTIPLIER):
                supply_zones.append({
                    "type": "supply",
                    "price": float(candle.high),
                    "time": candle.time
                })

    return demand_zones, supply_zones


def detect_fast_zones(df, point=0.0001, min_cluster=2, lookback=15):
    """
    Detect fast supply/demand zones for Forex pairs.
    - ATR-adaptive proximity
    - Wick rejection requirement
    - Cluster confirmation
    """
    fast_demand, fast_supply = [], []

    if df is None or len(df) < lookback:
        return fast_demand, fast_supply

    # --- ATR-proxy: rolling mean of absolute close diffs ---
    atr_points = df['close'].diff().abs().rolling(14).mean().iloc[-1]
    if pd.isna(atr_points) or atr_points == 0:
        atr_points = point * 20  # fallback minimum

    proximity = max(atr_points * 1.5, point * 15)  # adaptive band
    recent = df.tail(lookback)

    # === Demand zones (support clusters) ===
    lows = recent['low']
    min_low = lows.min()
    low_clusters = [p for p in lows if abs(p - min_low) <= proximity]

    if len(low_clusters) >= min_cluster:
        last_candle = recent.iloc[-1]
        lower_wick = (last_candle['close'] - last_candle['low']) > atr_points * 0.5
        if lower_wick:
            fast_demand.append({
                "type": "fast_demand",
                "price": float(min_low),
                "time": last_candle.time
            })

    # === Supply zones (resistance clusters) ===
    highs = recent['high']
    max_high = highs.max()
    high_clusters = [p for p in highs if abs(p - max_high) <= proximity]

    if len(high_clusters) >= min_cluster:
        last_candle = recent.iloc[-1]
        upper_wick = (last_candle['high'] - last_candle['close']) > atr_points * 0.5
        if upper_wick:
            fast_supply.append({
                "type": "fast_supply",
                "price": float(max_high),
                "time": last_candle.time
            })

    return fast_demand, fast_supply


def update_zones(zones, current_price, atr, point=0.0001):
    """
    Expire or flip zones when price breaks through them.
    - If price breaks demand zone by > 1.5 * ATR → flips to supply
    - If price breaks supply zone by > 1.5 * ATR → flips to demand
    """
    new_zones = []
    for zone in zones:
        zone_price = zone['price']
        ztype = zone['type']

        if ztype == "fast_demand":
            if current_price < zone_price - 1.5 * atr:
                # flip to supply
                new_zones.append({"type": "fast_supply", "price": zone_price, "time": zone.get("time")})
            else:
                new_zones.append(zone)

        elif ztype == "fast_supply":
            if current_price > zone_price + 1.5 * atr:
                # flip to demand
                new_zones.append({"type": "fast_demand", "price": zone_price, "time": zone.get("time")})
            else:
                new_zones.append(zone)

        else:
            # keep strict zones unchanged
            new_zones.append(zone)

    return new_zones