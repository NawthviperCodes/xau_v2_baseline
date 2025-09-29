# Nawthviper Forex Scalper Bot

🚀 **Nawthviper Forex Scalper Bot** is an advanced, fully-automated trading system built for **MetaTrader 5 (MT5)**.  
It focuses on **Forex Majors** (GBPUSD, EURUSD, USDJPY, USDCHF, USDCAD, XAUUSD) using a combination of:

- 📊 **Candlestick Pattern Recognition**  
- 🔥 **Candle Range Theory (CRT)**  
- 📈 **Indicator Confluence** (ADX, MACD, RSI, VWAP, ATR)  
- 🕒 **Session-based Filtering** (London, New York, Asia)  
- 📉 **Zone Detection** (Demand & Supply zones for precision entries)  

The bot is designed to capture high-probability trades with strict risk management, making it suitable for both **scalping** and **trend-following** strategies.

---

## ✨ Features

- ✅ **Dual Strategy Modes**:  
  - *Trend-Follow (Safe)* → conservative entries  
  - *Aggressive Scalper* → faster, higher-risk setups  

- ✅ **Dynamic Risk Management**  
  - Risk-based lot sizing (% equity risk per trade)  
  - Automatic Stop Loss (SL) & Take Profit (TP) calculation  
  - Trailing Stop for secured profits  

- ✅ **Smart Filters**  
  - News filter: avoids high-impact news events  
  - Adaptive ADX: avoids flat/ranging markets  
  - Session filter: trades only during optimal market hours  

- ✅ **Trade Management**  
  - Auto-close weaker trades when stronger opposite signals appear  
  - Tracks open/closed trades in CSV logs  
  - Daily performance summary  

- ✅ **Notifications**  
  - Sends trade alerts & summaries to **Telegram**  

---

## 📂 Project Structure

main.py # GUI launcher & real-time loop
scalper_strategy_engine.py # Strategy engine (sessions, signals, trade logic)
trade_decision_engine.py # Candlestick + indicator confluence + CRT
symbol_info_helper.py # Broker symbol/lot metadata
trade_executor.py # Order placement & trailing stop logic
performance_tracker.py # Daily summary reporting
emergency_control.py # Safety checks (equity stop)
telegram_notifier.py # Telegram integration


---

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/NawthviperCodes/nawthviper-forex-scalper-bot.git
   cd nawthviper-forex-scalper-bot


Install dependencies:

pip install -r requirements.txt


Run the bot:

python main.py


Select Mode & Lot Size from the GUI and the bot will start monitoring live charts.

📖 Requirements

Python 3.9+

MetaTrader 5 terminal + Python API (pip install MetaTrader5)

pandas, ta, pytz, tkinter, etc. (see requirements.txt)

⚠️ Disclaimer

This bot is provided for educational and research purposes only.
Trading carries high risk — only use on demo accounts unless you fully understand the risks.
The author is not responsible for financial losses incurred through use of this software.

👤 Author

Name: Thabo Masilompana

Brand: Nawthviper Codes

📞 Contact: 066 229 7338