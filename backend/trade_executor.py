# === trade_executor.py ===
import MetaTrader5 as mt5
import time
from telegram_notifier import send_telegram_message
from symbol_info_helper import get_lot_constraints # <-- 1. ADDED IMPORT

# ==========================================================
# === NEW HELPER FUNCTION ===
# ==========================================================
def get_position_by_ticket(ticket):
    """
    Fetches a single MT5 position object by its ticket number.
    """
    try:
        position = mt5.positions_get(ticket=ticket)
        if position and len(position) > 0:
            return position[0] # Return the first (and only) position
    except Exception as e:
        print(f"[Executor] Error getting position by ticket {ticket}: {e}")
    return None

# ==========================================================
# === NEW ENHANCEMENT #2 FUNCTION ===
# ==========================================================
def close_partial_and_move_sl_to_be(ticket, partial_close_percent=0.5):
    """
    Closes a percentage of a position and moves the SL to BE for the remainder.
    
    Args:
        ticket (int): The ticket of the position to modify.
        partial_close_percent (float): e.g., 0.5 for 50%.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    position = get_position_by_ticket(ticket)
    if not position:
        print(f"[Executor] Partial close failed: Could not find position {ticket}")
        return False

    symbol = position.symbol
    volume = position.volume
    side = position.type # 0 = BUY, 1 = SELL
    price_open = position.price_open
    
    # 1. Calculate partial volume to close
    try:
        min_lot, max_lot, lot_step = get_lot_constraints(symbol)
        volume_to_close = volume * partial_close_percent
        
        # Round to the nearest valid lot step
        volume_to_close = round(volume_to_close / lot_step) * lot_step
        
        # Clamp to min/max lot and ensure it's a valid volume
        volume_to_close = max(min_lot, min(max_lot, volume_to_close))
        
        if volume_to_close >= volume or volume_to_close <= 0:
            print(f"[Executor] Partial close failed: Invalid close volume {volume_to_close} for total {volume}")
            return False
            
    except Exception as e:
        print(f"[Executor] Partial close failed: Lot calculation error: {e}")
        return False

    # 2. Build and send the partial close request
    close_side = mt5.ORDER_TYPE_SELL if side == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = mt5.symbol_info_tick(symbol).bid if side == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask

    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": symbol,
        "volume": volume_to_close,
        "type": close_side,
        "price": price,
        "deviation": 20,
        "magic": position.magic,
        "comment": "Partial TP1",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    try:
        close_result = mt5.order_send(close_request)
        if close_result is None or close_result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[Executor] Partial close order send failed: {close_result.retcode if close_result else 'None'}")
            return False
    except Exception as e:
        print(f"[Executor] Partial close exception: {e}")
        return False

    # 3. If partial close was successful, move SL to Breakeven
    print(f"[Executor] Successfully closed {volume_to_close} lots for {ticket}.")
    
    # Wait a moment for the position to update
    time.sleep(0.5) 

    # Find the *remaining* position (it might have a new ticket, but usually keeps the old one)
    # Re-fetch to ensure we are modifying the correct remaining position
    remaining_position = get_position_by_ticket(ticket)
    if not remaining_position:
        print(f"[Executor] Could not find remaining position for {ticket} to move SL.")
        return True # Partial close worked, so return True

    modify_request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "sl": price_open, # Move SL to the original open price
        "tp": remaining_position.tp, # Keep the original final TP
    }

    try:
        modify_result = mt5.order_send(modify_request)
        if modify_result and modify_result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[Executor] Successfully moved SL to BE for {ticket}.")
            send_telegram_message(f"🛡️ {symbol} trade is now RISK-FREE. (SL moved to BE)")
        else:
            print(f"[Executor] Warning: Failed to move SL to BE: {modify_result.retcode if modify_result else 'None'}")
            
    except Exception as e:
        print(f"[Executor] Warning: Move SL to BE exception: {e}")

    return True # Main goal (partial close) was successful


def place_order(symbol, side, lot, magic, comment="", sl=None, tp=None):
    """
    Places a market order with diagnostics, retry logic, and automatic SL/TP correction
    using the broker's minimum stop level.
    """

    import MetaTrader5 as mt5
    import time
    from telegram_notifier import send_telegram_message

    def send_request(_sl=None, _tp=None):
        """Internal helper to build and send an order request once."""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"[Executor ERROR] No tick data for {symbol}. Market may be closed.")
            send_telegram_message(f"❌ Order Failed: No tick data for {symbol} (market closed or unavailable)")
            return None

        order_type = mt5.ORDER_TYPE_BUY if side.lower() == "buy" else mt5.ORDER_TYPE_SELL
        price = tick.ask if side.lower() == "buy" else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Attach SL/TP if valid
        if _sl is not None and _tp is not None:
            request["sl"] = float(_sl)
            request["tp"] = float(_tp)

        try:
            result = mt5.order_send(request)
            return result
        except Exception as e:
            print(f"[Executor EXCEPTION] order_send() exception: {e}")
            return None

    # --- Ensure MT5 initialized ---
    if not mt5.initialize():
        err = mt5.last_error()
        print(f"[Executor ERROR] MT5 not initialized: {err}")
        send_telegram_message(f"❌ Order Failed: MT5 not initialized {err}")
        return None

    # --- Validate symbol ---
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"[Executor ERROR] symbol_info() failed for {symbol}")
        send_telegram_message(f"❌ Order Failed: No symbol info for {symbol}")
        return None

    if not info.visible:
        print(f"[Executor] {symbol} not visible — enabling...")
        mt5.symbol_select(symbol, True)

    # --- Lot validation ---
    if lot is None or lot <= 0:
        print(f"[Executor ERROR] Invalid lot size: {lot}")
        send_telegram_message(f"❌ Order Failed: Invalid lot size {lot} for {symbol}")
        return None

    # --- Auto-correct SL/TP distances ---
    if sl is not None and tp is not None:
        point = info.point
        min_stop = info.trade_stops_level * point
        price = mt5.symbol_info_tick(symbol).ask if side == "buy" else mt5.symbol_info_tick(symbol).bid

        # Ensure SL/TP are on correct sides
        if side == "buy":
            if sl >= price:
                sl = price - (min_stop * 1.5)
            if tp <= price or abs(tp - price) < min_stop:
                tp = price + (min_stop * 1.5)
        else:  # sell
            if sl <= price:
                sl = price + (min_stop * 1.5)
            if tp >= price or abs(price - tp) < min_stop:
                tp = price - (min_stop * 1.5)

        print(f"[Executor] Adjusted SL/TP for {symbol}: SL={sl:.3f}, TP={tp:.3f}, min_stop={min_stop:.6f}")

    # === ATTEMPT #1 ===
    result = send_request(sl, tp)

    if result is None or result.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
        err = mt5.last_error()
        print(f"[Executor WARN] {symbol} {side.upper()} failed: retcode={getattr(result, 'retcode', None)} | MT5 Error: {err} — retrying...")
        send_telegram_message(f"⚠️ {symbol} {side.upper()} order failed, retrying... MT5 Error: {err}")
        time.sleep(1.5)
    else:
        print(f"[Executor] ✅ Order successful for {symbol} ({side.upper()}), Ticket={result.order}")
        send_telegram_message(f"✅ Order Placed: {symbol} {side.upper()} | Ticket {result.order}")
        return result

    # === ATTEMPT #2 (Retry) ===
    result2 = send_request(sl, tp)
    if result2 is None or result2.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
        print(f"[Executor ERROR] Retry failed for {symbol}: retcode={getattr(result2, 'retcode', None)}")
        send_telegram_message(f"❌ Retry Failed {symbol} {side.upper()} | Retcode={getattr(result2, 'retcode', None)}")
        return None

    print(f"[Executor] ✅ Order successful on retry for {symbol} ({side.upper()}) Ticket={result2.order}")
    send_telegram_message(f"✅ Order Placed on Retry: {symbol} {side.upper()} | Ticket {result2.order}")
    return result2


    
def modify_position_sltp(ticket, sl, tp):
    """
    Safely modifies SL/TP for an existing position.
    - Checks broker's minimum stop distance (trade_stops_level)
    - Ensures SL/TP are on the correct side of the market
    - Automatically adjusts invalid values to prevent rejection
    """

    import MetaTrader5 as mt5
    from telegram_notifier import send_telegram_message
    import time

    position = None
    try:
        pos = mt5.positions_get(ticket=ticket)
        if pos and len(pos) > 0:
            position = pos[0]
    except Exception as e:
        print(f"[Executor ERROR] Unable to fetch position {ticket}: {e}")
        send_telegram_message(f"❌ Modify SL/TP failed: Unable to fetch position {ticket}")
        return False

    if position is None:
        print(f"[Executor ERROR] No position found for ticket {ticket}")
        send_telegram_message(f"❌ Modify SL/TP failed: No position found {ticket}")
        return False

    symbol = position.symbol
    side = position.type  # 0=BUY, 1=SELL
    info = mt5.symbol_info(symbol)

    if info is None:
        print(f"[Executor ERROR] symbol_info() failed for {symbol}")
        send_telegram_message(f"❌ Modify SL/TP failed: No symbol info for {symbol}")
        return False

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"[Executor ERROR] No tick data for {symbol}")
        send_telegram_message(f"❌ Modify SL/TP failed: No tick data for {symbol}")
        return False

    # --- Auto-correct SL/TP using broker rules ---
    point = info.point
    min_stop = info.trade_stops_level * point
    price = tick.ask if side == mt5.ORDER_TYPE_BUY else tick.bid

    # Adjust SL/TP to valid values
    if side == mt5.ORDER_TYPE_BUY:
        if sl >= price:
            sl = price - (min_stop * 1.5)
        if tp <= price or abs(tp - price) < min_stop:
            tp = price + (min_stop * 1.5)
    else:  # SELL
        if sl <= price:
            sl = price + (min_stop * 1.5)
        if tp >= price or abs(price - tp) < min_stop:
            tp = price - (min_stop * 1.5)

    print(f"[Executor] Adjusted modify SL/TP for {symbol}: SL={sl:.3f}, TP={tp:.3f}, min_stop={min_stop:.6f}")

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "sl": float(sl),
        "tp": float(tp),
    }

    try:
        result = mt5.order_send(request)
        if result is None:
            print(f"[Executor ERROR] Modify SL/TP failed for {ticket}: result is None")
            send_telegram_message(f"❌ Modify SL/TP failed: No result for {symbol}")
            return False
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[Executor ERROR] Modify SL/TP failed for {ticket}, retcode={result.retcode}")
            send_telegram_message(f"❌ Modify SL/TP failed {symbol} | Retcode={result.retcode}")
            return False

        print(f"[Executor] ✅ Successfully modified SL/TP for {symbol} (Ticket={ticket})")
        send_telegram_message(f"✅ SL/TP Updated: {symbol} | SL={sl:.3f}, TP={tp:.3f}")
        return True

    except Exception as e:
        print(f"[Executor EXCEPTION] Modify SL/TP exception for {ticket}: {e}")
        send_telegram_message(f"❌ Modify SL/TP exception: {symbol} | {e}")
        return False


def place_dynamic_order(symbol, side, lot, sl_pips, tp_pips, magic, comment=""):
    """
    Places an order with SL/TP defined in pips.
    """
    point = mt5.symbol_info(symbol).point
    price = mt5.symbol_info_tick(symbol).ask if side == "buy" else mt5.symbol_info_tick(symbol).bid
    
    if side == "buy":
        sl = price - (sl_pips * point)
        tp = price + (tp_pips * point)
    else:
        sl = price + (sl_pips * point)
        tp = price - (tp_pips * point)
        
    return place_order(symbol, side, lot, sl, tp, magic, comment)


def trail_sl(symbol, magic, trail_pips=150):
    """
    Trails the stop loss for all open positions on the symbol.
    """
    positions = mt5.positions_get(symbol=symbol)
    if positions is None or len(positions) == 0:
        return

    point = mt5.symbol_info(symbol).point
    trail_distance = trail_pips * point

    for pos in positions:
        if pos.magic != magic:
            continue

        price_open = pos.price_open
        sl = pos.sl
        tp = pos.tp
        
        if pos.type == mt5.ORDER_TYPE_BUY:
            price = mt5.symbol_info_tick(symbol).bid
            new_sl = price - trail_distance
            if new_sl > (price_open + point) and new_sl > sl:
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": new_sl,
                    "tp": tp,
                }
                mt5.order_send(request)
                
        elif pos.type == mt5.ORDER_TYPE_SELL:
            price = mt5.symbol_info_tick(symbol).ask
            new_sl = price + trail_distance
            if new_sl < (price_open - point) and new_sl < sl:
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": new_sl,
                    "tp": tp,
                }
                mt5.order_send(request)

def move_to_breakeven(symbol, magic):
    """
    Moves SL to breakeven for profitable trades.
    NOTE: This is the old function. We will replace its call
    in scalper_strategy_engine.py with our new partial TP logic.
    """
    positions = mt5.positions_get(symbol=symbol)
    if positions is None or len(positions) == 0:
        return

    point = mt5.symbol_info(symbol).point

    for pos in positions:
        if pos.magic != magic:
            continue
            
        price_open = pos.price_open
        sl = pos.sl
        
        # Check if SL is already at or past breakeven
        if (pos.type == mt5.ORDER_TYPE_BUY and sl >= price_open) or \
           (pos.type == mt5.ORDER_TYPE_SELL and sl <= price_open):
            continue

        if pos.type == mt5.ORDER_TYPE_BUY:
            price = mt5.symbol_info_tick(symbol).bid
            profit_pips = (price - price_open) / point
            # If 1:1 R/R is assumed, we check if profit > SL pips
            # This logic is simplified; our new function is more robust
            if profit_pips > 0 and (price_open - sl) > 0 and (price - price_open) > (price_open - sl):
                request = {"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": price_open}
                mt5.order_send(request)

        elif pos.type == mt5.ORDER_TYPE_SELL:
            price = mt5.symbol_info_tick(symbol).ask
            profit_pips = (price_open - price) / point
            if profit_pips > 0 and (sl - price_open) > 0 and (price_open - price) > (sl - price_open):
                request = {"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": price_open}
                mt5.order_send(request)