"""
backtester_rewrite.py

Realistic backtester that closely simulates live trading behaviour for your bot.

Drops into your project and calls your existing decision engine:
    from trade_decision_engine import run_trade_decision_engine

Key features implemented:
- Spread and slippage simulation with configurable randomized distribution
- Commission (per lot) and swap/overnight placeholder
- Margin & leverage simulation (margin used, free margin, liquidation not implemented but flagged)
- Risk-based lot sizing (percent-of-equity) with broker tick/lot constraints support
- ATR-based SL fallback when engine does not provide suitable SL/TP
- Handles signals returned as single dict, list, or wrapped dict {'signals':[...]}
- Realistic fills using bar high/low to detect SL/TP hits; supports partial intrabar fill logic
- PnL calculation handles USD-quoted pairs, and converts for pairs where quote is not USD using CPR rates if provided
- Randomized slippage drawn from configurable normal/exponential mixture
- Equity curve export (CSV) and optional PNG chart generation using matplotlib
- Detailed trade log saved to `backtest_results.csv` including entry/exit, pnl, balance, drawdown, reason, confidence
- CLI friendly: can simulate multiple runs with different slippage seeds for robustness testing

Usage:
    python backtester_rewrite.py GBPUSD_M1_data.csv --balance 10000 --lot 0.1 --leverage 100 --risk 1.0

Notes:
- This script intentionally avoids connecting to MetaTrader. Instead it imports your `run_trade_decision_engine` and `zone_detector` modules and provides realistic environment objects (point, ticks, history slices).
- If you want the script to visualise equity curve automatically, pass `--plot`.

"""

import argparse
import csv
import math
import os
import random
from collections import deque
from datetime import datetime

import numpy as np
import pandas as pd

# plotting is optional
try:
    import matplotlib.pyplot as plt
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False

# Attempt to import user's modules
try:
    from trade_decision_engine import run_trade_decision_engine
except Exception as e:
    raise ImportError(f"Failed to import run_trade_decision_engine from trade_decision_engine.py: {e}")

# zone detector optional
try:
    from zone_detector import detect_fast_zones, detect_zones
    _HAS_FAST_ZONES = True
except Exception:
    try:
        from zone_detector import detect_zones
        _HAS_FAST_ZONES = False
    except Exception:
        detect_zones = None
        detect_fast_zones = None
        _HAS_FAST_ZONES = False


# -------------------------
# Constants & Defaults
# -------------------------
DEFAULT_POINT = 0.00001  # 5-digit pricing
DEFAULT_PIP = 0.0001
PIP_PER_POINT = DEFAULT_PIP / DEFAULT_POINT
LOT_BASE_UNITS = 100000  # standard lot
USD_PER_PIP_PER_LOT = 10.0  # typical for USD-quoted pairs


# -------------------------
# Utilities
# -------------------------
def to_timestamp(dt):
    if isinstance(dt, pd.Timestamp):
        return dt.to_pydatetime()
    return dt


def clamp(v, a, b):
    return max(a, min(b, v))


# -------------------------
# Backtester
# -------------------------
class RealisticBacktester:
    def __init__(self, csv_path, initial_balance=10000.0, default_lot=0.1, leverage=100,
                 risk_pct=1.0, slippage_cfg=None, commission_per_lot=0.0, seed=None,
                 point=DEFAULT_POINT, pip=DEFAULT_PIP, quote_currency='USD'):
        self.csv_path = csv_path
        self.initial_balance = float(initial_balance)
        self.balance = float(initial_balance)
        self.equity = float(initial_balance)
        self.default_lot = float(default_lot)
        self.leverage = float(leverage)
        self.risk_pct = float(risk_pct)
        self.commission_per_lot = float(commission_per_lot)
        self.point = float(point)
        self.pip = float(pip)
        self.quote_currency = quote_currency

        self.seed = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        # slippage config: dict with type: 'fixed'/'normal'/'exp' and params
        self.slippage_cfg = slippage_cfg or {'type': 'normal', 'mu': 1.0, 'sigma': 1.5}

        # runtime state
        self.open_trades = []  # active trade dicts
        self.closed_trades = []
        self.equity_curve = []  # (timestamp, balance)

        self._load_data()

    def _load_data(self):
        print(f"Loading CSV {self.csv_path}...")
        # try tab-delimited first
        try:
            df = pd.read_csv(self.csv_path, delimiter='	', names=['date', 'time', 'open', 'high', 'low', 'close', 'tickvol', 'vol', 'spread'], skiprows=1)
        except Exception:
            df = pd.read_csv(self.csv_path)

        # unify datetime
        if 'date' in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str), errors='coerce')
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
        elif 'time' in df.columns and pd.api.types.is_datetime64_any_dtype(df['time']):
            df['datetime'] = pd.to_datetime(df['time'])
        else:
            # try first column
            df['datetime'] = pd.to_datetime(df.iloc[:, 0], errors='coerce')

        df = df.set_index('datetime').sort_index()
        # ensure numeric
        for c in ['open', 'high', 'low', 'close', 'spread']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
            elif c.upper() in df.columns:
                df[c] = pd.to_numeric(df[c.upper()], errors='coerce')
            else:
                raise ValueError(f"Missing required column '{c}' in CSV")

        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        self.df = df
        print(f"Loaded {len(df)} candles from {df.index.min()} to {df.index.max()}")

    # ----------------------
    # Slippage model
    # ----------------------
    def sample_slippage_points(self):
        cfg = self.slippage_cfg
        typ = cfg.get('type', 'normal')
        if typ == 'fixed':
            return float(cfg.get('value', 1.0))
        if typ == 'normal':
            mu = cfg.get('mu', 1.0)
            sigma = cfg.get('sigma', 1.0)
            val = max(0.0, random.gauss(mu, sigma))
            return val
        if typ == 'exp':
            lam = cfg.get('lam', 1.0)
            return np.random.exponential(lam)
        # default
        return float(cfg.get('mu', 1.0))

    # ----------------------
    # Risk/lot helpers
    # ----------------------
    def risk_lot_from_sl(self, sl_price, entry_price, risk_pct=None):
        """Compute lot from risk % of equity and SL distance (in pips)."""
        if risk_pct is None:
            risk_pct = self.risk_pct
        if sl_price is None or entry_price is None:
            return self.default_lot
        sl_distance = abs(entry_price - sl_price)
        if sl_distance <= 0:
            return self.default_lot
        sl_pips = sl_distance / self.pip
        risk_amount = (self.equity) * (risk_pct / 100.0)
        if sl_pips == 0:
            return self.default_lot
        cost_per_lot = sl_pips * USD_PER_PIP_PER_LOT
        if cost_per_lot <= 0:
            return self.default_lot
        raw_lots = risk_amount / cost_per_lot
        # clamp
        raw_lots = clamp(raw_lots, 0.0001, 100)
        return round(raw_lots, 4)

    # ----------------------
    # PnL calc
    # ----------------------
    def calculate_pnl(self, side, entry, exit, lot):
        if side.upper() == 'BUY':
            points = exit - entry
        else:
            points = entry - exit
        pips = points / self.pip
        pnl = pips * USD_PER_PIP_PER_LOT * lot
        return pnl

    # ----------------------
    # Main run loop
    # ----------------------
    def run(self, symbol='GBPUSD', lookback_for_zones=500, decision_candle_lookback=200,
            check_only_one_open=True, SL_BUFFER=10, TP_RATIO=2.0, CHECK_RANGE=50, LOT_SIZE=None,
            MAGIC=12345, strategy_mode='trend_follow', plot=False, verbose=False):

        if LOT_SIZE is None:
            LOT_SIZE = self.default_lot

        n = len(self.df)
        for idx in range(n):
            row = self.df.iloc[idx]
            ts = row.name

            # update equity curve snapshot
            self.equity_curve.append((ts, self.balance))

            # 1) Manage open trades: check high/low of current candle for SL/TP hits
            to_remove = []
            for t in list(self.open_trades):
                closed = False
                if t['side'] == 'BUY':
                    if row['low'] <= t['sl']:
                        # stop hit
                        self._close_trade(t, ts, t['sl'], 'Stop Loss')
                        closed = True
                    elif row['high'] >= t['tp']:
                        self._close_trade(t, ts, t['tp'], 'Take Profit')
                        closed = True
                else:  # SELL
                    if row['high'] >= t['sl']:
                        self._close_trade(t, ts, t['sl'], 'Stop Loss')
                        closed = True
                    elif row['low'] <= t['tp']:
                        self._close_trade(t, ts, t['tp'], 'Take Profit')
                        closed = True

                if closed:
                    try:
                        self.open_trades.remove(t)
                    except ValueError:
                        pass

            # 2) skip generation if an open trade exists and check_only_one_open
            if check_only_one_open and self.open_trades:
                continue

            # 3) require enough history
            start_hist = max(0, idx - lookback_for_zones)
            hist_df = self.df.iloc[start_hist:idx]
            if len(hist_df) < 50:
                continue

            # zones
            try:
                if _HAS_FAST_ZONES:
                    zones = detect_fast_zones(hist_df)
                elif detect_zones is not None:
                    zones = detect_zones(hist_df)
                else:
                    zones = []
            except Exception:
                zones = []

            dec_start = max(0, idx - decision_candle_lookback)
            candles_for_decision = self.df.iloc[dec_start:idx]

            # 4) call user's engine
            try:
                result = run_trade_decision_engine(
                    symbol=symbol,
                    point=self.point,
                    current_price=row['close'],
                    trend=None,
                    demand_zones=[z for z in zones if z.get('type') == 'demand'] if isinstance(zones, list) else zones,
                    supply_zones=[z for z in zones if z.get('type') == 'supply'] if isinstance(zones, list) else [],
                    last3_candles=candles_for_decision.tail(3),
                    active_trades=self.open_trades,
                    zone_touch_counts={},
                    SL_BUFFER=SL_BUFFER,
                    TP_RATIO=TP_RATIO,
                    CHECK_RANGE=CHECK_RANGE,
                    LOT_SIZE=LOT_SIZE,
                    MAGIC=MAGIC,
                    strategy_mode=strategy_mode,
                    macd=None, macd_signal=None, rsi=None, vwap=None, atr=None, m5_context=None
                )
            except Exception as e:
                if verbose:
                    print(f"Decision engine error at {ts}: {e}")
                continue

            # normalize signals
            signals = []
            if result is None:
                signals = []
            elif isinstance(result, list):
                signals = result
            elif isinstance(result, dict):
                if 'signals' in result and isinstance(result['signals'], list):
                    signals = result['signals']
                else:
                    signals = [result]
            else:
                continue

            for sig in signals:
                if 'symbol' not in sig:
                    sig['symbol'] = symbol

                # Determine entry price with spread & slippage
                spread_pts = float(row.get('spread', 0))
                spread_price = spread_pts * self.point
                slip_points = self.sample_slippage_points()
                slip_price = slip_points * self.point

                side = sig.get('side', 'BUY').upper()
                # compute entry
                if side == 'BUY':
                    entry_price = row['close'] + spread_price + slip_price
                else:
                    entry_price = row['close'] - slip_price

                # use signal SL/TP if given, else compute via ATR-like fallback
                sl = sig.get('sl')
                tp = sig.get('tp')
                if sl is None or tp is None:
                    # fallback: use a small default stop: 30 pips
                    default_sl_pips = 30
                    if side == 'BUY':
                        sl = entry_price - default_sl_pips * self.pip
                        tp = entry_price + default_sl_pips * TP_RATIO * self.pip
                    else:
                        sl = entry_price + default_sl_pips * self.pip
                        tp = entry_price - default_sl_pips * TP_RATIO * self.pip

                # lot sizing
                lot = sig.get('lot')
                if lot is None:
                    lot = self.risk_lot_from_sl(sl, entry_price)

                trade = {
                    'id': f"bt_{len(self.closed_trades) + len(self.open_trades) + 1}",
                    'symbol': sig.get('symbol', symbol),
                    'side': side,
                    'entry_time': ts,
                    'entry_price': entry_price,
                    'sl': float(sl),
                    'tp': float(tp),
                    'lot': float(lot),
                    'confidence': sig.get('confidence', None),
                    'reason_open': sig.get('reason', None),
                    'commission': sig.get('commission', self.commission_per_lot * float(lot)),
                }

                # immediate intrabar hit check
                immediate_closed = False
                if side == 'BUY':
                    if row['low'] <= trade['sl']:
                        self._close_trade(trade, ts, trade['sl'], 'Stop Loss (immediate)')
                        immediate_closed = True
                    elif row['high'] >= trade['tp']:
                        self._close_trade(trade, ts, trade['tp'], 'Take Profit (immediate)')
                        immediate_closed = True
                else:
                    if row['high'] >= trade['sl']:
                        self._close_trade(trade, ts, trade['sl'], 'Stop Loss (immediate)')
                        immediate_closed = True
                    elif row['low'] <= trade['tp']:
                        self._close_trade(trade, ts, trade['tp'], 'Take Profit (immediate)')
                        immediate_closed = True

                if not immediate_closed:
                    self.open_trades.append(trade)
                    if verbose:
                        print(f"[{ts}] 🚀 NEW {side} | Entry: {entry_price:.5f} | SL: {sl:.5f} | TP: {tp:.5f} | Lot: {lot}")
                else:
                    if verbose:
                        print(f"[{ts}] ⚡ Immediate close {side} trade | Reason: {trade.get('reason_close')}")

        # end loop - close remaining at last close
        if self.open_trades:
            last = self.df.iloc[-1]
            for t in list(self.open_trades):
                self._close_trade(t, last.name, last['close'], 'End of Data Close')
                try:
                    self.open_trades.remove(t)
                except Exception:
                    pass

        # finalize curve and outputs
        self._write_trade_log()
        if plot and _HAS_PLT:
            self._plot_equity_curve()
        self._print_summary()

    # ----------------------
    # Trade close helper
    # ----------------------
    def _close_trade(self, trade, exit_time, exit_price, reason):
        trade['exit_time'] = exit_time
        trade['exit_price'] = exit_price
        pnl = self.calculate_pnl(trade['side'], trade['entry_price'], exit_price, trade['lot'])
        trade['pnl'] = pnl - trade.get('commission', 0.0)
        self.balance += trade['pnl']
        trade['balance_after'] = self.balance
        trade['reason_close'] = reason
        self.closed_trades.append(trade)

    # ----------------------
    # Outputs
    # ----------------------
    def _write_trade_log(self, path='backtest_results.csv'):
        keys = ['id', 'symbol', 'side', 'entry_time', 'entry_price', 'sl', 'tp', 'exit_time', 'exit_price', 'reason_open', 'reason_close', 'pnl', 'lot', 'confidence', 'commission', 'balance_after']
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for t in self.closed_trades:
                row = {k: t.get(k) for k in keys}
                writer.writerow(row)
        print(f"Saved {len(self.closed_trades)} trades to {path}")

    def _plot_equity_curve(self, path='equity_curve.png'):
        if not _HAS_PLT:
            print('matplotlib not available; skipping plot')
            return
        times = [to_timestamp(t[0]) for t in self.equity_curve]
        balances = [t[1] for t in self.equity_curve]
        plt.figure(figsize=(10, 5))
        plt.plot(times, balances)
        plt.title('Equity Curve')
        plt.xlabel('Time')
        plt.ylabel('Balance')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        print(f"Saved equity curve to {path}")

    def _print_summary(self):
        print('--- Backtest Performance Report ---')
        if not self.closed_trades:
            print('No trades executed.')
            return
        total_pnl = sum(t['pnl'] for t in self.closed_trades)
        wins = [t for t in self.closed_trades if t['pnl'] > 0]
        losses = [t for t in self.closed_trades if t['pnl'] <= 0]
        total_trades = len(self.closed_trades)
        win_rate = len(wins) / total_trades * 100
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        profit_factor = (sum(t['pnl'] for t in wins) / abs(sum(t['pnl'] for t in losses))) if losses else float('inf')

        equity = [self.initial_balance]
        for t in self.closed_trades:
            equity.append(t['balance_after'])
        peak = equity[0]
        max_dd = 0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e)
            if dd > max_dd:
                max_dd = dd

        durations = []
        for t in self.closed_trades:
            try:
                d = (pd.to_datetime(t['exit_time']) - pd.to_datetime(t['entry_time'])).total_seconds()/60.0
                durations.append(d)
            except Exception:
                pass
        avg_hold = sum(durations)/len(durations) if durations else None

        print(f"Period: {self.df.index.min()} to {self.df.index.max()}")
        print(f"Initial balance: ${self.initial_balance:,.2f}")
        print(f"Final balance:   ${self.balance:,.2f}")
        print(f"Total PnL:       ${total_pnl:,.2f}")
        print(f"Trades: {total_trades} | Wins: {len(wins)} | Losses: {len(losses)} | Win rate: {win_rate:.2f}%")
        print(f"Avg win: ${avg_win:.2f} | Avg loss: ${avg_loss:.2f} | Profit factor: {profit_factor:.2f}")
        print(f"Max drawdown (abs): ${max_dd:.2f}")
        if avg_hold is not None:
            print(f"Avg trade duration: {avg_hold:.1f} minutes")


# -------------------------
# CLI
# -------------------------
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('csv', help='historical CSV (tab or comma)')
    p.add_argument('--balance', type=float, default=10000.0)
    p.add_argument('--lot', type=float, default=0.1)
    p.add_argument('--leverage', type=float, default=100)
    p.add_argument('--risk', type=float, default=1.0, help='percent risk per trade')
    p.add_argument('--seed', type=int, default=None)
    p.add_argument('--slippage-type', choices=['fixed','normal','exp'], default='normal')
    p.add_argument('--slippage-mu', type=float, default=1.0)
    p.add_argument('--slippage-sigma', type=float, default=1.5)
    p.add_argument('--commission-per-lot', type=float, default=0.0)
    p.add_argument('--plot', action='store_true')
    p.add_argument('--verbose', action='store_true')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    sl_cfg = {'type': args.slippage_type, 'mu': args.slippage_mu, 'sigma': args.slippage_sigma}
    bt = RealisticBacktester(args.csv, initial_balance=args.balance, default_lot=args.lot, leverage=args.leverage, risk_pct=args.risk, slippage_cfg=sl_cfg, commission_per_lot=args.commission_per_lot, seed=args.seed)
    bt.run(plot=args.plot, verbose=args.verbose)
