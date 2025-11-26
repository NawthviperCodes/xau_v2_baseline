# === main.py (Fixed & Threading Compatible) ===
import MetaTrader5 as mt5
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

# Import the NEW threaded worker
from scalper_strategy_engine import process_symbol_cycle, SYMBOLS, TIMEFRAME_ENTRY, MAGIC
from emergency_control import check_emergency_stop, set_risk_limits
from performance_tracker import send_daily_summary
from trade_executor import trail_sl as apply_trailing_stop
from telegram_notifier import send_telegram_message

# Global variable for summary state
SUMMARY_SENT = False

def run_bot_realtime(strategy_mode, fixed_lot, daily_loss_limit, drawdown_limit, stopper):
    """
    Thread-aware Main Loop.
    Manages the ThreadPoolExecutor while respecting the 'stopper' signal.
    """
    global SUMMARY_SENT

    print("Checking MT5 connection for bot thread...")
    if not mt5.terminal_info():
        print("[ERROR] MT5 not connected. Cannot start bot logic.")
        return

    set_risk_limits(daily_loss_limit, drawdown_limit)
    print(f"[Risk Manager] Active limits → Daily Loss: ${daily_loss_limit}, Max Drawdown: ${drawdown_limit}")

    account_info = mt5.account_info()
    if account_info:
        print(f"Bot logic started for Account: {account_info.login}")
        print(f"Strategy: '{strategy_mode}', Lot Size: {fixed_lot}")
        send_telegram_message(f"🚀 Bot Started | Strat: {strategy_mode} | Lot: {fixed_lot}")
    
    # Initialize Thread Pool
    # We use max_workers=len(SYMBOLS) to ensure true parallelism
    executor = ThreadPoolExecutor(max_workers=len(SYMBOLS))
    print(f"✅ Thread Pool Initialized for {len(SYMBOLS)} symbols.")

    try:
        while not stopper["stop"]:
            # 1. Emergency Stop Check
            equity = mt5.account_info().equity
            reason = check_emergency_stop(equity)
            if reason:
                print(f"[EMERGENCY] Bot stopped: {reason}")
                send_telegram_message(f"❌ Bot stopped: {reason}")
                stopper["stop"] = True 
                break

            # 2. Launch Parallel Cycles for All Symbols
            futures = []
            for sym in SYMBOLS:
                # Submit tasks to the thread pool
                # We pass strategy and lot size to the engine
                futures.append(executor.submit(process_symbol_cycle, sym, strategy_mode, fixed_lot))

            # 3. Wait for all threads to finish this "tick"
            # This keeps the loop synchronized so we don't spam CPU
            for f in futures:
                try:
                    f.result() # Raises exceptions if any occurred in threads
                except Exception as e:
                    print(f"[THREAD ERROR] {e}")

            # 4. Daily Summary Logic
            now = datetime.now(timezone.utc)
            if 23 <= now.hour < 24 and 58 <= now.minute <= 59 and not SUMMARY_SENT:
                send_daily_summary()
                SUMMARY_SENT = True
            if now.hour == 0 and now.minute == 0:
                SUMMARY_SENT = False

            # 5. Loop Nap (Prevent CPU 100%)
            time.sleep(1.0) 

    except Exception as e:
        print(f"An error occurred in the main bot loop: {e}")
    finally:
        executor.shutdown(wait=False) # Kill threads
        print("Bot logic loop has ended.")
        send_telegram_message("🛑 Bot loop has been stopped.")