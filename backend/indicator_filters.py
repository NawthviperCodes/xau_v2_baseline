def macd_cross(macd_line, signal_line):
    """
    Returns dict with 'buy' and 'sell' keys.
    buy = bullish crossover, sell = bearish crossover.
    """
    if len(macd_line) < 2 or len(signal_line) < 2:
        return {"buy": False, "sell": False}  # not enough data

    return {
        "buy": macd_line[-2] < signal_line[-2] and macd_line[-1] > signal_line[-1],   # bullish
        "sell": macd_line[-2] > signal_line[-2] and macd_line[-1] < signal_line[-1]    # bearish
    }

def rsi_filter(rsi_values, side):
    """
    VIX75 UPGRADE: This filter now checks for MOMENTUM, not reversal.
    This aligns with the new H4 trend-following bias.
    
    Returns True if RSI confirms the trade direction (momentum).
    For buy: RSI > 50 (bullish momentum).
    For sell: RSI < 50 (bearish momentum).
    """
    if len(rsi_values) < 1:
        return False
        
    last_rsi = rsi_values[-1]

    if side == "buy":
        # Price is in a bullish momentum regime
        return last_rsi > 50
    else: # sell
        # Price is in a bearish momentum regime
        return last_rsi < 50

def vwap_filter(price, vwap_value, side):
    """
    Confirms if price is in the direction of VWAP.
    Buy: price > VWAP, Sell: price < VWAP
    """
    if side == "buy":
        return price > vwap_value
    else:
        return price < vwap_value