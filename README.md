<!-- PROJECT BANNER -->
<p align="center">
  <img src="https://via.placeholder.com/1000x220.png?text=NawthViper+Currency+Bot" alt="NawthViper Banner"/>
</p>

<h1 align="center">💸 NawthViper Currency Bot</h1>
<p align="center">Institutional-grade multi-timeframe automated trading system for MetaTrader 5</p>

<p align="center">
  <!-- Badges -->
  <img src="https://img.shields.io/badge/version-2.0.0-blue.svg" />
  <img src="https://img.shields.io/badge/python-3.10+-yellow.svg" />
  <img src="https://img.shields.io/badge/build-passing-brightgreen.svg" />
  <img src="https://img.shields.io/badge/license-MIT-orange.svg" />
</p>

---

## 🖼️ Preview / Dashboard Screenshots

<p align="center">
  <img src="https://via.placeholder.com/800x400.png?text=Dashboard+Preview" width="80%" />
</p>

<p align="center">
  <img src="https://via.placeholder.com/800x400.png?text=Trade+Execution+Logs" width="80%" />
</p>

---

## ⚙️ Overview

NawthViper Currency Bot is a professionally engineered trading engine designed for high-probability scalping using:

- Price Action  
- Multi-Timeframe Analysis  
- Institutional Supply/Demand Zones  
- CRT (Candle Range Theory)  
- Volatility-Adaptive Risk Management  

---

## 🚀 Key Features

### 🧠 Strategy & Analysis
- **H4 EMA Bias (50/200)** – long-term trend control  
- **H1 Supply/Demand Zones** using explosive departure logic  
- **M5 Entry Confirmation** via Engulfing, Pin Bar, Morning/Evening Star  
- **M1 CRT Filter** for intraday precision  
- **RSI / MACD / VWAP** confluence filters  

---

### 🛡️ Risk & Trade Management
- Emergency Equity Control (Daily Loss / Total Drawdown)  
- Live High-Impact News Filter (ForexFactory)  
- Partial TP (1:1 RR) + Auto Breakeven  
- ATR-based Trailing Stop  
- Dynamic Lot Sizing based on equity % and SL distance  

---

### 🖥️ UI & System Architecture
- Modern **React + Tailwind** dashboard  
- Clean Telegram notifications  
- Modular Python backend  
- 24/7 deployment-ready on VPS or Render  

---

## 🧠 Tech Stack

| Layer | Technology | Description |
|------|------------|-------------|
| Frontend | React, TailwindCSS | Real-time dashboard |
| Backend | Python (FastAPI/Flask) | API + bot engine |
| Strategy Engine | Python | Core logic, filters, S/D zones |
| Libraries | MetaTrader5, Pandas, TA, BS4 | Indicators & scraping |
| Database | PostgreSQL / CSV | Trades & analytics |
| Deployment | VPS / Render | 24/7 uptime |

---

## 📂 Project Structure

```plaintext
nawthviper_currency/
├── backend/
│   ├── main.py
│   ├── scalper_strategy_engine.py
│   ├── trade_decision_engine.py
│   ├── trade_executor.py
│   ├── emergency_control.py
│   ├── news_filter_te.py
│   ├── zone_detector.py
│   ├── indicator_filters.py
│   ├── candlestick_patterns.py
│   └── ...
├── frontend/
│   └── src/
├── requirements.txt


⚡ Installation
1️⃣ Clone the Repository
git clone https://github.com/NawthviperCodes/currency_bot_v2.git
cd currency_bot_v2

2️⃣ Backend Setup
cd backend
pip install -r requirements.txt
python main.py

3️⃣ Frontend Setup
cd ../frontend
npm install
npm start

📌 Versioning

Current Stable Version: 2.0.0

Semantic Versioning (SemVer) used:
MAJOR.MINOR.PATCH

Upcoming:

v2.1.0 — New ATR trailing stop module

v3.0.0 — Multi-symbol optimized threading & portfolio mode

📝 License

This project is licensed under the MIT License.

🤝 Contributions

Contributions, pull requests, and feature suggestions are welcome.

📩 Contact

For issues or collaboration:
NawthViperCodes – GitHub


---

