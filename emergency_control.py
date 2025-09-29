# === emergency_control.py ===

from datetime import datetime, timezone
import MetaTrader5 as mt5

# === Configurable Risk Limits (for $10 account) ===
MAX_DAILY_LOSS = -99999    # Stop if daily loss > $2
MAX_DRAWDOWN = -99999      # Stop if drawdown > $3

# === Session Tracker ===
session_state = {
    "start_equity": None,
    "max_equity": None,
    "last_check_date": datetime.now(timezone.utc).date()
}

DEBUG_PRINT = True  # Set True for console debug

# Track last printed values to avoid spamming console
_last_print = {"pnl": None, "dd": None}


def update_equity_stats(current_equity):
    today = datetime.now(timezone.utc).date()

    # Reset daily if date has changed
    if today != session_state["last_check_date"]:
        session_state["start_equity"] = current_equity
        session_state["max_equity"] = current_equity
        session_state["last_check_date"] = today

    # Init on startup
    if session_state["start_equity"] is None:
        session_state["start_equity"] = current_equity
    if session_state["max_equity"] is None:
        session_state["max_equity"] = current_equity

    # Track highest equity reached
    if current_equity > session_state["max_equity"]:
        session_state["max_equity"] = current_equity

    daily_profit = current_equity - session_state["start_equity"]
    drawdown = current_equity - session_state["max_equity"]

    return daily_profit, drawdown


def check_emergency_stop(current_equity):
    global _last_print
    daily_profit, drawdown = update_equity_stats(current_equity)

    if DEBUG_PRINT:
        pnl_r = round(daily_profit, 2)
        dd_r = round(drawdown, 2)
        if _last_print["pnl"] != pnl_r or _last_print["dd"] != dd_r:
            print(f"[Risk Monitor] Daily PnL: {pnl_r:.2f} | Drawdown: {dd_r:.2f}")
            _last_print = {"pnl": pnl_r, "dd": dd_r}

    if daily_profit < MAX_DAILY_LOSS:
        return "Daily Loss Limit Exceeded"
    if drawdown < MAX_DRAWDOWN:
        return "Max Drawdown Exceeded"
    return None
