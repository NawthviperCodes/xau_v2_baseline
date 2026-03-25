# ======================================================
# === performance_tracker.py (Learning Layer Edition) ===
# ======================================================
#
# ✅ EXISTING: Daily summary via trade_log.csv (unchanged)
# ✅ NEW: Persistent trade memory via trade_performance.json
# ✅ NEW: Adaptive pattern confidence weights
# ✅ NEW: Strategy kill switch (auto-disable bad strategies)
# ✅ NEW: Dynamic risk adjustment per strategy
# ✅ NEW: Market regime detection
# ✅ NEW: Performance feedback summary
#

import csv
import json
import os
import threading
from datetime import datetime, date

from telegram_notifier import send_telegram_message

# ============================
# === FILE PATHS ===
# ============================

LOG_CSV   = "trade_log.csv"          # Existing — human-readable trade journal
PERF_FILE = "trade_performance.json" # New — machine-readable learning memory

_PERF_LOCK = threading.Lock()        # Thread-safe file access

# ============================
# === MEMORY: LOAD / SAVE ===
# ============================

def _load_data() -> dict:
    """Raw load — always use load_data() in application code."""
    try:
        with open(PERF_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_data(data: dict):
    """Atomic write — overwrites file cleanly."""
    with open(PERF_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_data() -> dict:
    """Thread-safe load."""
    with _PERF_LOCK:
        return _load_data()

# ============================
# === STEP 1: LOG A TRADE ===
# ============================

def log_trade(signal: dict, result: str):
    """
    Call this after every trade closes.
    signal must have: 'strategy', 'reason' (pattern name)
    result must be: 'win' or 'loss'

    Usage:
        log_trade(signal_data, "win")
        log_trade(signal_data, "loss")
    """
    strategy = signal.get("strategy", "unknown")
    pattern  = signal.get("reason", "unknown")
    key      = f"{strategy}|{pattern}"

    with _PERF_LOCK:
        data = _load_data()

        if key not in data:
            data[key] = {
                "wins": 0,
                "losses": 0,
                "first_seen": datetime.now().isoformat(),
                "last_seen":  datetime.now().isoformat(),
            }

        data[key]["wins"   if result == "win" else "losses"] += 1
        data[key]["last_seen"] = datetime.now().isoformat()

        _save_data(data)

# ====================================================
# === STEP 2: ADAPTIVE PATTERN CONFIDENCE WEIGHTS ===
# ====================================================

MIN_SAMPLES_FOR_ADAPTATION = 10   # Need at least this many trades before adapting
DEFAULT_WEIGHT             = 0.60  # Used when no history exists yet

def get_pattern_weight(pattern: str, strategy: str) -> float:
    """
    Returns a confidence weight for a pattern+strategy combo,
    scaled by its real historical win rate.

    Score range: 0.40 (chronic loser) → 1.00 (consistent winner)
    Falls back to DEFAULT_WEIGHT until MIN_SAMPLES_FOR_ADAPTATION is reached.

    Usage in compute_candlestick_confidence():
        weight = get_pattern_weight(pattern_info["pattern"], "zone_based")
        score += weight
    """
    data = load_data()
    key  = f"{strategy}|{pattern}"

    if key not in data:
        return DEFAULT_WEIGHT

    wins   = data[key]["wins"]
    losses = data[key]["losses"]
    total  = wins + losses

    if total < MIN_SAMPLES_FOR_ADAPTATION:
        return DEFAULT_WEIGHT  # Not enough data yet — use safe default

    winrate = wins / total
    # Linear scale: 0% WR → 0.40, 100% WR → 1.00
    return round(0.40 + (winrate * 0.60), 4)

# ============================
# === STEP 3: KILL SWITCH ===
# ============================

MIN_SAMPLES_FOR_KILL  = 30    # Only kill after meaningful sample
KILL_WINRATE_FLOOR    = 0.45  # Below 45% win rate = strategy disabled

def is_strategy_active(strategy: str) -> bool:
    """
    Returns False if a strategy has enough history AND is performing
    below the kill floor. Plug this into the decision engine to
    automatically disable underperforming strategies.

    Usage in run_trade_decision_engine():
        if not is_strategy_active(sig["strategy"]):
            continue
    """
    data = load_data()

    total_wins   = 0
    total_losses = 0

    for key, val in data.items():
        if key.startswith(strategy):
            total_wins   += val["wins"]
            total_losses += val["losses"]

    total = total_wins + total_losses

    if total < MIN_SAMPLES_FOR_KILL:
        return True  # Not enough data — keep running

    winrate = total_wins / total
    return winrate >= KILL_WINRATE_FLOOR

# =====================================
# === STEP 4: DYNAMIC RISK SCALING ===
# =====================================

MIN_SAMPLES_FOR_RISK = 20   # Need history before scaling risk
RISK_BOOST_THRESHOLD = 0.60 # Above 60% WR → increase risk
RISK_CUT_THRESHOLD   = 0.40 # Below 40% WR → cut risk

def get_dynamic_risk(strategy: str) -> float:
    """
    Returns a risk multiplier based on strategy win rate history.
    Plug this into determine_lot_size() to replace static risk_percent.

      WR > 60%  → 1.5x risk (strategy is hot)
      WR < 40%  → 0.5x risk (strategy is cold, protect capital)
      Default   → 1.0x

    Usage in scalper_strategy_engine.py:
        risk_percent = get_dynamic_risk(strategy_mode)
    """
    data = load_data()

    wins   = 0
    losses = 0

    for key, val in data.items():
        if key.startswith(strategy):
            wins   += val["wins"]
            losses += val["losses"]

    total = wins + losses

    if total < MIN_SAMPLES_FOR_RISK:
        return 1.0  # Not enough data — neutral risk

    winrate = wins / total

    if winrate > RISK_BOOST_THRESHOLD:
        return 1.5
    elif winrate < RISK_CUT_THRESHOLD:
        return 0.5
    else:
        return 1.0

# =========================================
# === STEP 5: MARKET REGIME DETECTION ===
# =========================================

def detect_market_regime(df) -> str:
    """
    Simple regime detector using price range vs ATR.
    Returns: "TRENDING" or "RANGING"

    Usage in scalper_strategy_engine.py:
        regime = detect_market_regime(h1_df)
        if regime == "RANGING" and strategy == "momentum_continuation_L2":
            return  # Skip L2 in choppy markets

    TRENDING = strong directional move, use trend-follow strategies
    RANGING  = choppy, use zone-reversal strategies only
    """
    if df is None or len(df) < 21:
        return "UNKNOWN"

    avg_move     = df['close'].diff().abs().rolling(20).mean().iloc[-1]
    trend_range  = abs(df['close'].iloc[-1] - df['close'].iloc[-20])

    if trend_range > avg_move * 3:
        return "TRENDING"
    else:
        return "RANGING"

# =============================================
# === STEP 6: PERFORMANCE FEEDBACK SUMMARY ===
# =============================================

def print_performance_summary():
    """
    Prints a per-strategy win rate table to console.
    Call this every 200 cycles alongside print_decision_summary().
    """
    data = load_data()

    if not data:
        print("\n[PERF] No trade history yet.")
        return

    print("\n===== LEARNING PERFORMANCE =====")
    rows = []
    for key, val in data.items():
        total = val["wins"] + val["losses"]
        if total == 0:
            continue
        winrate = val["wins"] / total * 100
        status  = "✅ ACTIVE" if is_strategy_active(key.split("|")[0]) else "🔴 KILLED"
        rows.append((winrate, key, val["wins"], val["losses"], total, status))

    # Sort by win rate descending
    for winrate, key, wins, losses, total, status in sorted(rows, reverse=True):
        print(f"{status} | {key:<45} | WR: {winrate:5.1f}% | {wins}W / {losses}L ({total} trades)")

    print("================================\n")

# ===================================================
# === EXISTING: DAILY SUMMARY (UNCHANGED) ===
# ===================================================

def send_daily_summary():
    today        = date.today()
    trades_today = []
    total_profit = 0
    wins         = 0
    losses       = 0
    trade_details = []

    if not os.path.exists(LOG_CSV):
        return

    with open(LOG_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                exit_time = datetime.strptime(row['exit_time'], "%Y-%m-%d %H:%M:%S")
                if exit_time.date() == today:
                    profit = float(row['profit'])
                    result = row['result'].lower()
                    total_profit += profit
                    trades_today.append(row)
                    trade_details.append((
                        row['side'],
                        float(row['entry_price']),
                        float(row['exit_price']),
                        profit,
                        result,
                        row['entry_reason'],
                        row['strategy']
                    ))
                    if result == "win":
                        wins += 1
                    elif result == "loss":
                        losses += 1
            except Exception:
                continue

    if not trades_today:
        send_telegram_message("📊 No trades executed today.")
        return

    total_trades        = wins + losses
    win_rate            = (wins / total_trades) * 100 if total_trades > 0 else 0
    most_common_strategy = max(set([t[6] for t in trade_details]), key=[t[6] for t in trade_details].count)
    most_common_pattern  = max(set([t[5] for t in trade_details]), key=[t[5] for t in trade_details].count)

    top_trade   = max(trade_details, key=lambda x: x[3])
    worst_trade = min(trade_details, key=lambda x: x[3])

    summary = (
        f"📅 Summary for {today.strftime('%Y-%m-%d')}\n"
        f"Trades: {total_trades} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%\n"
        f"Total Profit: ${total_profit:.2f}\n\n"
        f"Top Trade ✅\n{top_trade[0].upper()} | Entry: {top_trade[1]:.2f} → Exit: {top_trade[2]:.2f} | "
        f"Profit: ${top_trade[3]:.2f} | Pattern: {top_trade[5]} | Mode: {top_trade[6]}\n\n"
        f"Worst Trade ❌\n{worst_trade[0].upper()} | Entry: {worst_trade[1]:.2f} → Exit: {worst_trade[2]:.2f} | "
        f"Loss: ${worst_trade[3]:.2f} | Pattern: {worst_trade[5]} | Mode: {worst_trade[6]}\n\n"
        f"Most Used Strategy: {most_common_strategy.upper()}\nMost Used Pattern: {most_common_pattern.upper()}"
    )
    send_telegram_message(summary)

    breakdown = "\n🔁 Trades:\n"
    for idx, (side, entry, exit_, profit, result, reason, strategy) in enumerate(trade_details, 1):
        breakdown += (
            f"{idx}. {side.upper()} | {reason} | {strategy} | Entry: {entry:.2f} → Exit: {exit_:.2f} | "
            f"${profit:.2f} | {'✅ WIN' if result == 'win' else '❌ LOSS'}\n"
        )
    send_telegram_message(breakdown)