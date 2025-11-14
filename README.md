💸 NawthViper Currency Bot⚙️ OverviewNawthViper Currency Bot is a sophisticated, multi-timeframe automated trading system for MetaTrader 5. It is not a simple indicator-based bot; it uses a multi-layered filtering system based on price action, volatility, and institutional-grade risk management to execute high-probability scalping trades.The core strategy is built on a top-down-analysis approach:H4 Bias: Establishes the high-level trend (Up/Down) using a 50/200 EMA cross.H1 Zones: Identifies high-probability Supply and Demand zones based on strict, explosive price pivots.M5 Patterns: Waits for price to retest an H1 zone and confirm entry with a classic candlestick pattern (e.g., Engulfing, Pin Bar).M1 Confirmation: Uses Candle Range Theory (CRT) for final momentum and entry validation.Execution: Manages the trade with partial take-profits and an automatic move to breakeven.🚀 Key Features🧠 Strategy & AnalysisMulti-Timeframe (MTF) Bias: Employs an H4 EMA cross (50/200) to ensure all M5/M1 entries trade only in the direction of the long-term trend.H1 Supply/Demand Engine: Detects strict, high-quality S/D zones based on explosive "Strength of Departure" (ATR-based) logic.M5 Candlestick Confirmation: Identifies precise entries at zones using patterns like Engulfing, Pin Bars, and Morning/Evening Stars.Candle Range Theory (CRT): Uses a proprietary M1 CRT filter to validate momentum and filter out "noise" before entry.Indicator Confluence: Further validates entries with a confluence of RSI, MACD, and VWAP filters.🛡️ Risk & Trade ManagementEmergency Equity Control: A "master switch" that halts all trading if a Max Daily Loss % or Max Total Drawdown % is breached.Live News Filter: Automatically scrapes ForexFactory.com and pauses trading during high-impact (red folder) news events.Partial TP & Auto-Breakeven: Automatically closes 50% of a position at a 1:1 Risk/Reward ratio and simultaneously moves the Stop Loss to the entry price, making the remainder of the trade risk-free.Dynamic Lot Sizing: Calculates lot sizes based on a fixed % of account equity and the trade's specific stop-loss distance.ATR Trailing Stop: An optional trailing stop-loss that trails price based on current market volatility (ATR).🖥️ System & InterfaceReal-time Web Dashboard: A full React frontend (from image_889140.jpg) to monitor performance, equity, and live trades.Clean Telegram Notifications: Sends focused, clean alerts for signal execution and trade closures, not spam.Scalable Engine: The core logic is built in modular Python, allowing for easy updates and strategy tuning.🧠 Tech StackLayerTechnologyDescriptionFrontendReact, TailwindCSSReal-time monitoring dashboard.BackendPython (Flask/FastAPI)Serves the frontend and manages the bot thread.Bot LogicPythonPure Python core logic (scalper_strategy_engine.py).LibrariesMetaTrader5, Pandas, TA, BeautifulSoup4For execution, analysis, and news scraping.DatabasePostgreSQL / CSVFor storing trade history and performance metrics.Trading APIMetaTrader 5Direct connection to the broker.HostingRender / VPSFor 24/7 bot operation.📂 Project Structurenawthviper_currency/
├── backend/            # Python Backend
│   ├── main.py         # Main bot runner/API entry
│   ├── scalper_strategy_engine.py # Core logic
│   ├── trade_decision_engine.py # Signal generation
│   ├── trade_executor.py   # MT5 order execution
│   ├── emergency_control.py # Equity risk management
│   ├── news_filter_te.py     # ForexFactory scraper
│   ├── zone_detector.py      # S/D zone logic
│   ├── indicator_filters.py  # RSI, MACD, VWAP
│   ├── candlestick_patterns.py # Pattern logic
│   └── ...
├── frontend/           # React + Tailwind Dashboard
│   ├── src/
│   └── ...
├── package.json        # Node.js dependencies
├── requirements.txt    # Python dependencies
├── .gitignore
└── README.md
⚡ Installation1️⃣ Clone the RepositoryBashgit clone https://github.com/NawthviperCodes/currency_bot_v2.git
cd currency_bot_v2
2️⃣ Backend Setup (Python)Bash# Navigate to the backend folder
cd backend

# Install Python dependencies
pip install -r requirements.txt
# (or manually: pip install MetaTrader5 pandas ta requests beautifulsoup4 pytz)

# Run the bot
python main.py
3️⃣ Frontend Setup (React)Bash# Navigate to the frontend folder
cd ../frontend

# Install Node.js dependencies
npm install

# Run the development server
npm start
