# === main.py (Adapted for Web Dashboard) ===
import MetaTrader5 as mt5
import time
from scalper_strategy_engine import monitor_and_trade, SYMBOLS, TIMEFRAME_ENTRY, MAGIC
from emergency_control import check_emergency_stop, set_risk_limits
from performance_tracker import send_daily_summary
from symbol_info_helper import print_symbol_lot_info
from trade_executor import trail_sl as apply_trailing_stop
from datetime import datetime, timezone
from scalper_strategy_engine import send_startup_intro
from telegram_notifier import send_telegram_message # <-- Import at top

# Global variable to check if the summary has been sent for the day
SUMMARY_SENT = False

def run_bot_realtime(strategy_mode, fixed_lot, daily_loss_limit, drawdown_limit, stopper):
    """
    This is the main bot loop, now accepting strategy, lot size, and a 'stopper' object.
    The 'stopper' is a dictionary like {"stop": False} controlled by api_server.py.
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
    
    last_candle_time = None

    try:
        # ✅ This loop will now check the 'stopper' object
        while not stopper["stop"]:
            equity = mt5.account_info().equity
            reason = check_emergency_stop(equity)
            if reason:
                print(f"[EMERGENCY] Bot stopped: {reason}")
                send_telegram_message(f"❌ Bot stopped: {reason}")
                stopper["stop"] = True # Tell the API server we stopped
                return # Exit the function

            # Sync to new candle on the main timeframe (M1)
            rates = mt5.copy_rates_from_pos(SYMBOLS[0], TIMEFRAME_ENTRY, 0, 1)
            if not rates:
                time.sleep(0.1)
                continue
            
            current_candle_time = rates[0]['time']

            if current_candle_time != last_candle_time:
                last_candle_time = current_candle_time
                print(f"New Candle ({datetime.fromtimestamp(current_candle_time).strftime('%H:%M:%S')}). Checking symbols...")
                
                # Check stopper *before* starting the symbol loop
                if stopper["stop"]:
                    print("Stop signal received, breaking loop before symbols.")
                    break
                    
                for sym in SYMBOLS:
                    # Check stopper *before* each symbol
                    if stopper["stop"]:
                        print(f"Stop signal received, stopping before {sym}.")
                        break
                        
                    try:
                        monitor_and_trade(symbol=sym, strategy_mode=strategy_mode, fixed_lot=fixed_lot)
                        # ✅ Use the correct MAGIC ID from your config
                        apply_trailing_stop(sym, magic=MAGIC) 
                    except Exception as e:
                        print(f"[ERROR] Strategy engine failed for {sym}: {e}")
                
                # Daily summary logic
                now = datetime.now(timezone.utc)
                if 23 <= now.hour < 24 and 58 <= now.minute <= 59 and not SUMMARY_SENT:
                    send_daily_summary()
                    SUMMARY_SENT = True
                if now.hour == 0 and now.minute == 0:
                    SUMMARY_SENT = False

            time.sleep(0.2) # Poll for new candle time

    except Exception as e:
        print(f"An error occurred in the main bot loop: {e}")
    finally:
        print("Bot logic loop has ended.")
        send_telegram_message("🛑 Bot loop has been stopped.")