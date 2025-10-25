# === main.py (Adapted for Web Dashboard) ===
import MetaTrader5 as mt5
import time
from scalper_strategy_engine import monitor_and_trade, SYMBOLS, TIMEFRAME_ENTRY
from emergency_control import check_emergency_stop, set_risk_limits  # ✅ Added setter
from performance_tracker import send_daily_summary
from symbol_info_helper import print_symbol_lot_info
from trade_executor import trail_sl as apply_trailing_stop
from datetime import datetime, timezone
from scalper_strategy_engine import send_startup_intro

# Global variable to check if the summary has been sent for the day
SUMMARY_SENT = False

def run_bot_realtime(strategy_mode, fixed_lot, daily_loss_limit, drawdown_limit):
    """
    This is the main bot loop, now accepting strategy and lot size as arguments.
    """
    global SUMMARY_SENT

    print("Checking MT5 connection for bot thread...")
    # The connection should already be initialized by the api_server
    if not mt5.terminal_info():
        print("[ERROR] MT5 not connected. Cannot start bot logic.")
        return
    # ✅ Apply dynamic risk limits from the dashboard
    set_risk_limits(daily_loss_limit, drawdown_limit)
    print(f"[Risk Manager] Active limits → Daily Loss: ${daily_loss_limit}, Max Drawdown: ${drawdown_limit}")

    account_info = mt5.account_info()
    if account_info:
        print(f"Bot logic started for Account: {account_info.login}")
        print(f"Strategy: '{strategy_mode}', Lot Size: {fixed_lot}")
    
    # send_startup_intro() # You can uncomment this if you want the intro message every time the bot starts

    last_candle_time = None

    try:
        # We need a way to stop this loop from the outside.
        # A global 'bot_running' flag checked here would be a good approach.
        # For now, it will run until the server is stopped.
        while True: # In a real app, you'd check a global flag here to stop the bot
            equity = mt5.account_info().equity
            reason = check_emergency_stop(equity)
            if reason:
                print(f"[EMERGENCY] Bot stopped: {reason}")
                from telegram_notifier import send_telegram_message
                send_telegram_message(f"❌ Bot stopped: {reason}")
                # We don't shut down MT5 here, as the server might still need it.
                return

            # Sync to new candle on the main timeframe (M1)
            rates = mt5.copy_rates_from_pos(SYMBOLS[0], TIMEFRAME_ENTRY, 0, 1)
            if not rates:
                time.sleep(0.1)
                continue
            
            current_candle_time = rates[0]['time']

            if current_candle_time != last_candle_time:
                last_candle_time = current_candle_time
                print(f"New Candle ({datetime.fromtimestamp(current_candle_time).strftime('%H:%M:%S')}). Checking symbols...")
                for sym in SYMBOLS:
                    try:
                        monitor_and_trade(symbol=sym, strategy_mode=strategy_mode, fixed_lot=fixed_lot)
                        apply_trailing_stop(sym, magic=12345)
                    except Exception as e:
                        print(f"[ERROR] Strategy engine failed for {sym}: {e}")

                # Daily summary logic
                now = datetime.now(timezone.utc)
                if 23 <= now.hour < 24 and 58 <= now.minute <= 59 and not SUMMARY_SENT:
                    send_daily_summary()
                    SUMMARY_SENT = True
                if now.hour == 0 and now.minute == 0:
                    SUMMARY_SENT = False

            time.sleep(0.2)

    except Exception as e:
        print(f"An error occurred in the main bot loop: {e}")
    finally:
        print("Bot logic loop has ended.")

# The if __name__ == "__main__": block is no longer needed
# because this script is now imported and run by api_server.py,
# not run directly by the user.
