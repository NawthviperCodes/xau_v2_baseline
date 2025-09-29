import csv
import os
from datetime import datetime
import uuid

# Unified log file (single source of truth)
LOG_FILE = "trades_history_local.csv"

HEADER = [
    "trade_id", "timestamp", "symbol", "strategy", "side", "entry_reason", "zone_price",
    "entry_price", "sl", "tp", "lot_size", "exit_price", "exit_time", "profit", "result"
]

def log_pending_trade(strategy, side, reason, zone, entry, sl, tp, lot, symbol="", trade_id=None):
    """Log a newly opened trade into the CSV.
       trade_id should be the MT5 ticket. Falls back to uuid if not provided (e.g. DRY_RUN).
    """
    trade_id = str(trade_id) if trade_id else str(uuid.uuid4())[:8]

    row = {
        "trade_id": trade_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "strategy": strategy,
        "side": side,
        "entry_reason": reason,
        "zone_price": zone,
        "entry_price": entry,
        "sl": sl,
        "tp": tp,
        "lot_size": lot,
        "exit_price": "",
        "exit_time": "",
        "profit": "",
        "result": ""
    }

    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    return trade_id


def get_contract_size(symbol):
    """Return contract size approximation based on instrument."""
    symbol = (symbol or "").upper()
    if symbol.startswith("XAU"):  # Gold
        return 100  # 1 lot = 100 oz
    if symbol.startswith("XAG"):  # Silver
        return 5000  # 1 lot = 5000 oz
    if symbol.endswith("USD") or symbol.startswith("USD"):  # Forex majors/minors
        return 100000  # standard forex contract size
    if symbol.startswith("US30") or symbol.startswith("DJI"):
        return 1  # index CFD per lot
    if symbol.startswith("NAS") or symbol.startswith("NDX"):
        return 20  # Nasdaq CFD approx.
    if symbol.startswith("SPX") or symbol.startswith("S&P"):
        return 50  # S&P CFD approx.
    # default
    return 100000


def calculate_profit(entry_price, exit_price, side, lot_size, symbol="", contract_size=None):
    """Approximate profit calculation in account currency."""
    try:
        entry_price = float(entry_price)
        exit_price = float(exit_price)
        lot_size = float(lot_size)
    except:
        return 0.0

    if contract_size is None:
        contract_size = get_contract_size(symbol)

    points = (exit_price - entry_price)
    if side == "sell":
        points = -points
    profit = points * lot_size * contract_size
    return profit


def update_trade_result(
    trade_id=None, entry_price=None, side=None, lot_size=None, symbol="",
    exit_price=None, profit=None, exit_time=None, result=None
):
    """Update an existing trade in the CSV when it closes."""
    if not os.path.exists(LOG_FILE):
        return

    rows = []
    updated = False

    with open(LOG_FILE, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # --- Primary match: by trade_id (MT5 ticket) ---
            if trade_id and row.get("trade_id") == str(trade_id) and row.get("exit_price") in [None, "", "nan"]:
                row['exit_price'] = str(exit_price)
                row['exit_time'] = exit_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                calc_profit = profit if profit is not None else calculate_profit(
                    row['entry_price'], exit_price, row['side'], row['lot_size'], row.get('symbol', symbol)
                )
                row['profit'] = str(calc_profit)
                row['result'] = result or ("win" if float(calc_profit) > 0 else ("loss" if float(calc_profit) < 0 else "breakeven"))
                updated = True

            # --- Backup match: if no ticket, match on symbol + side + entry_price tolerance ---
            elif (not trade_id or row.get("trade_id") in [None, "", "nan"]) and row.get("exit_price") in [None, "", "nan"]:
                try:
                    if row.get("symbol") == symbol and row.get("side") == side:
                        if abs(float(row['entry_price']) - float(entry_price)) < 0.001:  # tolerance
                            row['exit_price'] = str(exit_price)
                            row['exit_time'] = exit_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            calc_profit = profit if profit is not None else calculate_profit(
                                row['entry_price'], exit_price, row['side'], row['lot_size'], row.get('symbol', symbol)
                            )
                            row['profit'] = str(calc_profit)
                            row['result'] = result or ("win" if float(calc_profit) > 0 else ("loss" if float(calc_profit) < 0 else "breakeven"))
                            updated = True
                except Exception:
                    pass

            rows.append(row)

    if updated:
        with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HEADER)
            writer.writeheader()
            writer.writerows(rows)
