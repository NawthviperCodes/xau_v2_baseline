import MetaTrader5 as mt5
from telegram_notifier import send_telegram_message

FALLBACK_STOPS_LEVEL = 2000  # in points
TRAILING_TRIGGER = 3000      # trigger trailing after 3000 points profit
TRAILING_STEP = 1000         # trail SL by 1000 points step


def place_order(symbol, order_type, lot, sl_price, tp_price, magic_number, comment="auto-trade"):
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        msg = f"[ERROR] Symbol info not found for {symbol}."
        print(msg)
        send_telegram_message(msg)
        return None

    stops_level = getattr(symbol_info, "stops_level", FALLBACK_STOPS_LEVEL) * symbol_info.point
    point = symbol_info.point

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        msg = f"[ERROR] Failed to get tick for {symbol}."
        print(msg)
        send_telegram_message(msg)
        return None

    price = tick.ask if order_type == "buy" else tick.bid
    deviation = 20

    # Ensure SL and TP are not too close
    min_sl_distance = stops_level * 1.2
    min_tp_distance = stops_level * 1.2
    
    # Enforce safer minimum distance for VIX75
    if symbol == "Volatility 75 Index":
        min_sl_distance = max(min_sl_distance, 5000 * point)
        min_tp_distance = max(min_tp_distance, 5000 * point)

    if order_type == "buy" and (price - sl_price) < min_sl_distance:
        sl_price = price - min_sl_distance
        print(f"[WARN] Adjusted SL for BUY {symbol} to {sl_price:.2f} due to stops_level.")
    elif order_type == "sell" and (sl_price - price) < min_sl_distance:
        sl_price = price + min_sl_distance
        print(f"[WARN] Adjusted SL for SELL {symbol} to {sl_price:.2f} due to stops_level.")

    if order_type == "buy" and (tp_price - price) < min_tp_distance:
        tp_price = price + min_tp_distance
        print(f"[WARN] Adjusted TP for BUY {symbol} to {tp_price:.2f} due to stops_level.")
    elif order_type == "sell" and (price - tp_price) < min_tp_distance:
        tp_price = price - min_tp_distance
        print(f"[WARN] Adjusted TP for SELL {symbol} to {tp_price:.2f} due to stops_level.")

    print(f"[DEBUG] {symbol} {order_type.upper()} | Lot: {lot} | SL: {sl_price:.5f} | TP: {tp_price:.5f} | Comment: {comment}")
    print(f"[DEBUG] SL distance: {abs(price - sl_price):.2f}, TP distance: {abs(tp_price - price):.2f}")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if order_type == "buy" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": deviation,
        "magic": magic_number,
        "comment": comment,  # trade_id injected here
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        error_msg = f"❌ Order failed for {symbol}. Retcode: {getattr(result, 'retcode', 'N/A')} | Comment: {getattr(result, 'comment', 'No result')}"
        print(error_msg)
        send_telegram_message(error_msg)
        return None

    print(f"[SUCCESS] Order placed for {symbol} | Ticket: {result.order} | Retcode: {result.retcode}")
    return result


def place_dynamic_order(symbol, order_type, sl_price, tp_price, magic_number, lot=None, comment="auto-trade"):
    account = mt5.account_info()
    if not account:
        msg = "[ERROR] Failed to get account info."
        print(msg)
        send_telegram_message(msg)
        return None

    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        msg = f"[ERROR] Symbol info not found for {symbol}."
        print(msg)
        send_telegram_message(msg)
        return None

    stops_level = getattr(symbol_info, "stops_level", FALLBACK_STOPS_LEVEL) * symbol_info.point
    point = symbol_info.point
    contract_size = symbol_info.trade_contract_size

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        msg = f"[ERROR] Failed to get tick for {symbol}."
        print(msg)
        send_telegram_message(msg)
        return None

    price = tick.ask if order_type == "buy" else tick.bid
    sl_distance = abs(price - sl_price)
    if sl_distance < stops_level * 1.2:
        sl_distance = stops_level * 1.2
        sl_price = price - sl_distance if order_type == "buy" else price + sl_distance
        print(f"[WARN] Adjusted SL distance for {symbol} to {sl_distance:.2f} points.")

    balance = account.balance

    if lot is None:
        # Risk-based dynamic lot sizing
        if balance <= 20:
            risk_percent = 0.005
            max_lot = 0.005
        elif balance <= 100:
            risk_percent = 0.01
            max_lot = 0.01
        else:
            risk_percent = 0.02
            max_lot = 0.1

        risk_amount = balance * risk_percent
        lot = risk_amount / (sl_distance * contract_size)
        lot = min(max_lot, lot)
        lot = max(lot, 0.001)

        # Adjust decimal places based on instrument type
        lot = round(lot, 2 if symbol.endswith("USD") else 3)

    print(f"[DEBUG] {symbol} {order_type.upper()} | Dynamic Lot: {lot} | SL: {sl_price:.5f} | TP: {tp_price:.5f} | Comment: {comment}")

    return place_order(symbol, order_type, lot, sl_price, tp_price, magic_number, comment=comment)


def trail_sl(symbol, magic, atr_multiplier_trigger=1.5, atr_multiplier_step=1.0):
    """
    ATR-based trailing stop for VIX75.
    - Triggers when profit >= atr_multiplier_trigger * ATR
    - SL is trailed to 1 * ATR behind current price
    - Sends Telegram alert only on first activation
    """
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return

    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return

    point = symbol_info.point
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return

    # Calculate ATR from last 50 M1 candles
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 50)
    if rates is None or len(rates) < 20:
        return

    import pandas as pd
    df = pd.DataFrame(rates)
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    if pd.isna(atr):
        return

    for pos in positions:
        if pos.magic != magic:
            continue

        direction = 1 if pos.type == mt5.ORDER_TYPE_BUY else -1
        current_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        entry = pos.price_open
        profit_points = (current_price - entry) * direction / point

        # Only activate once profit >= 1.5 * ATR
        if profit_points * point < atr * atr_multiplier_trigger:
            continue

        # Trail SL = current price - (1 ATR)
        new_sl = current_price - direction * atr_multiplier_step * atr

        # Update only if SL improves
        if (direction == 1 and (pos.sl == 0 or new_sl > pos.sl)) or \
           (direction == -1 and (pos.sl == 0 or new_sl < pos.sl)):

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": pos.ticket,
                "sl": new_sl,
                "tp": pos.tp,
            }
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                msg = f"🔐 Trailing SL updated for {symbol} at {new_sl:.2f}"
                print(msg)

                # ✅ Telegram only when first activated (no SL before)
                if pos.sl == 0:
                    send_telegram_message(msg)
