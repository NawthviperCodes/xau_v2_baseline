from flask import Flask, request, jsonify
from flask_cors import CORS
import MetaTrader5 as mt5
import threading
import traceback # <-- ADD THIS IMPORT AT THE TOP OF THE FILE
import time
from datetime import datetime, timedelta
# This assumes backtester.py exists. If not, this line can be commented out if not used.
# from backtester import run_backtest 

# --- Global State ---
bot_thread = None
bot_running = False
bot_stopper = None # <-- ADD THIS

# Initialize Flask App
app = Flask(__name__)
CORS(app) 

# --- Helper Functions ---
def run_main_bot_logic(strategy, lot_size, max_daily_loss, max_drawdown, stopper):
    """
    Runs the bot's main loop in a background thread.
    (UPDATED with full error logging)
    """
    global bot_running
    try:
        # This import will now work because your main.py file exists
        print("[BOT THREAD] Attempting to import 'run_bot_realtime' from 'main'...")
        from main import run_bot_realtime 
        print("[BOT THREAD] Import successful. Starting bot logic...")
        
        # Pass all args AND the stopper object to the bot loop
        run_bot_realtime(
            strategy_mode=strategy,
            fixed_lot=lot_size,
            daily_loss_limit=max_daily_loss,
            drawdown_limit=max_drawdown,
            stopper=stopper
        )
        
    except ImportError as e:
        # --- THIS IS THE NEW, DETAILED ERROR BLOCK ---
        print("\n" + "="*50)
        print("--- CRITICAL IMPORT ERROR ---")
        print(f"ERROR: Could not import 'run_bot_realtime' from 'main'.")
        print(f"This *usually* means 'main.py' (or a file it imports, like 'scalper_strategy_engine.py')")
        print(f"is missing one of *its* dependencies.")
        print("\n--- ROOT CAUSE (Full Traceback) ---")
        print(traceback.format_exc())
        print("="*50 + "\n")
        # --- END OF NEW BLOCK ---
        
    except Exception as e:
        print(f"\n--- UNEXPECTED BOT THREAD ERROR ---")
        print(f"An error occurred in the bot thread: {e}")
        print(traceback.format_exc())
        print("="*50 + "\n")
        
    finally:
        bot_running = False # Bot loop finished, update API state
        print("Bot thread has finished.")

# --- API Endpoints ---

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    try:
        # MT5 login is an integer
        token = int(data.get('token'))
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid Account ID format. It must be a number."}), 400
        
    server = data.get('server')

    if not token:
        return jsonify({"status": "error", "message": "Account ID is required."}), 400

    print(f"Attempting to login to account {token} on server: {server}...")
    
    initialized = mt5.initialize(login=token, server=server)

    if initialized:
        account_info = mt5.account_info()
        if account_info:
            print("MT5 Initialized Successfully!")
            response = {"status": "success", "message": "Login successful!", "user": { "accountId": account_info.login, "balance": account_info.balance, "equity": account_info.equity, "server": account_info.server }}
            return jsonify(response)
        else:
            print("MT5 Initialization failed to get account info.")
            mt5.shutdown()
            return jsonify({"status": "error", "message": "Login failed. Could not retrieve account info."}), 401
    else:
        print(f"MT5 Initialization failed. Error: {mt5.last_error()}")
        return jsonify({"status": "error", "message": f"Login failed. Error: {mt5.last_error()}"}), 401


@app.route('/start-bot', methods=['POST'])
def start_bot():
    global bot_thread, bot_running, bot_stopper # <-- ADD 'bot_stopper'
    if bot_running:
        return jsonify({"status": "error", "message": "Bot is already running."}), 400

    data = request.json
    strategy = data.get('strategy')
    lot_size = data.get('lotSize')
    max_daily_loss = data.get('maxDailyLoss', 200.0)
    max_drawdown = data.get('maxDrawdown', 300.0)

    print(f"Received request to start bot with strategy: {strategy}, lot: {lot_size}, max loss: {max_daily_loss}, max DD: {max_drawdown}")
    
    bot_running = True
    # Create a mutable 'stopper' object (a dictionary)
    bot_stopper = {"stop": False} 
    
    # Pass the stopper object to the bot thread
    bot_thread = threading.Thread(target=run_main_bot_logic, args=(strategy, lot_size, max_daily_loss, max_drawdown, bot_stopper))
    bot_thread.start()
    
    return jsonify({"status": "success", "message": f"Bot started with {strategy} strategy."})


@app.route('/stop-bot', methods=['POST'])
def stop_bot():
    global bot_running, bot_stopper # <-- ADD 'bot_stopper'
    if not bot_running:
        return jsonify({"status": "error", "message": "Bot is not running."}), 400
    
    print("Received request to stop bot.")
    
    # Set the flag inside the mutable 'stopper' object
    # The bot thread will see this change and stop itself
    if bot_stopper:
        bot_stopper["stop"] = True 
    
    return jsonify({"status": "success", "message": "Bot stop signal sent."})


@app.route('/get-positions', methods=['GET'])
def get_positions():
    if not mt5.terminal_info():
        return jsonify({"status": "error", "message": "MT5 connection lost."}), 500
    
    positions = mt5.positions_get()
    if positions is None: return jsonify({"status": "error", "message": "Failed to get positions."}), 500

    live_trades = [{"id": pos.ticket, "symbol": pos.symbol, "side": "Buy" if pos.type == 0 else "Sell", "lot": pos.volume, "entry": pos.price_open, "pnl": pos.profit} for pos in positions]
    return jsonify({"status": "success", "trades": live_trades})


@app.route('/get-account-info', methods=['GET'])
def get_account_info():
    if not mt5.terminal_info(): return jsonify({"status": "error", "message": "MT5 connection not available."}), 500
    account_info = mt5.account_info()
    if account_info is None: return jsonify({"status": "error", "message": "Failed to get account info."}), 500
    info = {"balance": account_info.balance, "equity": account_info.equity, "profit": account_info.profit}
    return jsonify({"status": "success", "info": info})


@app.route('/get-account-history', methods=['GET'])
def get_account_history():
    """
    Analyzes historical deals to provide total P/L, deposits,
    a SMOOTHED performance chart, and a list of closed trades.
    """
    if not mt5.terminal_info():
        return jsonify({"status": "error", "message": "MT5 connection not available."}), 500

    from_date = datetime.now() - timedelta(hours=24)
    deals = mt5.history_deals_get(from_date, datetime.now())
        
    if deals is None or len(deals) == 0:
        # Return a clean empty state
        return jsonify({
            "status": "success",
            "data": {
                "totalProfitLoss": 0, "percentageGain": 0, "chartData": [], "closedTrades": []
            }
        })

    # --- Data Smoothing Logic ---
    initial_balance = 0
    # Find the very first deposit to start our balance calculation
    for deal in deals:
        if deal.type == mt5.DEAL_TYPE_BALANCE:
            initial_balance = deal.profit
            break
    
    if initial_balance == 0: # Fallback if no initial deposit is found
        # Try to infer from the earliest deal
        if deals:
             account_info = mt5.account_info()
             if account_info:
                 initial_balance = account_info.balance - sum(d.profit for d in deals if d.entry != mt5.DEAL_ENTRY_INOUT)


    running_balance = initial_balance
    chart_data = [{'time': deals[0].time * 1000, 'balance': initial_balance}]
    total_profit_loss = 0
    closed_trades_list = []

    # Process deals chronologically (oldest to newest)
    sorted_deals = sorted(deals, key=lambda d: d.time)

    for deal in sorted_deals:
        # ONLY include profits/losses from actual trades in the chart
        if deal.entry == mt5.DEAL_ENTRY_OUT: # A closed trade
            total_profit_loss += deal.profit
            running_balance += deal.profit # Update balance with trade P/L
            chart_data.append({'time': deal.time * 1000, 'balance': round(running_balance, 2)})

            # Also add it to our list of closed trades
            closed_trades_list.append({
                "ticket": deal.order,
                "symbol": deal.symbol,
                "type": "Buy" if deal.type == mt5.DEAL_TYPE_BUY else "Sell",
                "volume": deal.volume,
                "profit": deal.profit,
                "close_time": datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M')
            })

    # Calculate final stats
    net_deposits = sum(d.profit for d in deals if d.type == mt5.DEAL_TYPE_BALANCE)
    percentage_gain = (total_profit_loss / net_deposits * 100) if net_deposits > 0 else 0
    
    # Reverse for display (newest first)
    closed_trades_list.reverse()

    return jsonify({
        "status": "success",
        "data": {
            "totalProfitLoss": total_profit_loss,
            "percentageGain": percentage_gain,
            "chartData": chart_data,
            "closedTrades": closed_trades_list
        }
    })
    
# ✅ --- NEW ENDPOINT FOR CONTACT FORM ---
@app.route('/send-message', methods=['POST'])
def send_message():
    """
    Handles submissions from the landing page contact form.
    In a real app, this would send an email. For now, we just print it.
    """
    data = request.json
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')

    if not all([name, email, message]):
        return jsonify({"status": "error", "message": "All fields are required."}), 400

    # --- IMPORTANT ---
    # In a production environment, you would integrate an email service here.
    # For example, using SendGrid, Mailgun, or Python's smtplib.
    # For this example, we will just print the data to the server console.
    print("\n--- NEW CONTACT MESSAGE ---")
    print(f"Name: {name}")
    print(f"Email: {email}")
    print(f"Message: {message}")
    print("---------------------------\n")

    # We simulate a successful send
    return jsonify({"status": "success", "message": "Message received!"})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
