"""
Quantitative Backtesting Baseline Experiments
Evaluates 3 foundational Level 1 setups on CME MNQ 1m continuous data:
  Setup A: Classical Initial Balance (IB) Breakout (30m IB 09:30-10:00 EST, 5m close outside IB, 20/40pt SL/TP)
  Setup B: Session VWAP Sigma Bands Mean-Reversion (09:30-16:00 EST, intraday VWAP + 2.0 std dev sweep & close inside, target VWAP)
  Setup C: Pre-market High/Low Sweep & Reclaim (Judas Open at 09:30-10:30 EST sweeping 00:00-09:15 high/low and closing back inside)
"""

import sys
import os
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple

# Add engine directory to path
sys.path.append(r"futures\engine")
from futures_engine import FuturesBacktestEngine, Trade

DATA_PATH = r"futures\data\mnq_1m_continuous.csv"


def calculate_metrics(trades: List[Trade], account_size: float = 50_000.0) -> Dict:
    """Computes comprehensive performance statistics across all trades."""
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "net_pnl": 0.0,
            "max_drawdown": 0.0,
            "monthly_avg_return": 0.0,
            "gross_wins": 0.0,
            "gross_losses": 0.0,
            "avg_trade": 0.0,
            "monthly_pnl": {}
        }

    pnls = [t.net_pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    win_rate = (len(wins) / len(pnls)) * 100.0 if pnls else 0.0
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else (float("inf") if wins else 0.0)
    net_pnl = sum(pnls)
    avg_trade = net_pnl / len(pnls) if pnls else 0.0

    # Equity curve and peak-to-trough Drawdown calculation
    equity = account_size
    equity_curve = [equity]
    for p in pnls:
        equity += p
        equity_curve.append(equity)

    eq_series = pd.Series(equity_curve)
    cummax = eq_series.cummax()
    drawdowns = cummax - eq_series
    max_dd = drawdowns.max()

    # Monthly statistics
    df_trades = pd.DataFrame([{
        "exit_time": t.exit_time,
        "net_pnl": t.net_pnl
    } for t in trades])
    df_trades["month"] = df_trades["exit_time"].dt.to_period("M")
    monthly_pnl = df_trades.groupby("month")["net_pnl"].sum()
    monthly_avg = monthly_pnl.mean() if len(monthly_pnl) > 0 else 0.0

    return {
        "total_trades": len(trades),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "net_pnl": round(net_pnl, 2),
        "max_drawdown": round(max_dd, 2),
        "monthly_avg_return": round(monthly_avg, 2),
        "gross_wins": round(sum(wins), 2),
        "gross_losses": round(sum(losses), 2),
        "avg_trade": round(avg_trade, 2),
        "monthly_pnl": {str(k): round(v, 2) for k, v in monthly_pnl.items()}
    }


# ==========================================
# SETUP A: Classical Initial Balance Breakout
# ==========================================
def run_setup_a(df_raw: pd.DataFrame, fixed_sl_pts: float = 20.0, fixed_tp_pts: float = 40.0) -> Dict:
    """
    Setup A: Classical Initial Balance (IB) Breakout
    - IB Period: 09:30 - 10:00 EST (first 30m of RTH)
    - Resampled to 5-minute bars during RTH (09:30 - 16:00 EST)
    - Trigger: First 5m candle closing outside IB High (Long) or Low (Short) between 10:00 and 15:00 EST.
    - Risk/Reward: 20-40pt SL/TP
    """
    print(f"\n--- Running Setup A: Initial Balance Breakout (SL: {fixed_sl_pts}pt, TP: {fixed_tp_pts}pt) ---")
    
    # Filter RTH 09:30 to 16:00
    df_rth = df_raw.between_time("09:30", "16:00").copy()
    
    # Resample to 5m
    df_5m = df_rth.resample("5min").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()
    df_5m["time_str"] = df_5m.index.strftime("%H:%M")
    df_5m["date"] = df_5m.index.date

    # Precalculate Initial Balance for each day (09:30 - 09:59)
    ib_bars = df_5m[(df_5m["time_str"] >= "09:30") & (df_5m["time_str"] < "10:00")]
    ib_highs = ib_bars.groupby("date")["high"].max().to_dict()
    ib_lows = ib_bars.groupby("date")["low"].min().to_dict()

    # Generate signals
    df_5m["signal"] = 0
    
    # Bar by bar iteration
    for date, group in df_5m.groupby("date"):
        ib_h = ib_highs.get(date)
        ib_l = ib_lows.get(date)
        if ib_h is None or ib_l is None:
            continue
        
        traded_today = False
        for idx, row in group.iterrows():
            t_str = row["time_str"]
            if "10:00" <= t_str < "15:00" and not traded_today:
                if row["close"] > ib_h:
                    df_5m.loc[idx, "signal"] = 1
                    traded_today = True
                elif row["close"] < ib_l:
                    df_5m.loc[idx, "signal"] = -1
                    traded_today = True

    # Run engine on 5m data
    engine = FuturesBacktestEngine(
        data_path=DATA_PATH,
        account_size=50_000.0,
        max_trailing_drawdown=2_000.0,
        daily_loss_limit=1_000.0,
        point_value=2.0,
        tick_size=0.25,
        roundtrip_commission=0.62,
        slippage_ticks=1,
        rth_only=False, # already prepared
        flatten_time_est="15:55"
    )
    engine.df = df_5m

    res = engine.run_simulation(
        signal_generator=lambda d: d,
        fixed_contracts=2,
        fixed_stop_pts=fixed_sl_pts,
        fixed_target_pts=fixed_tp_pts
    )
    
    metrics = calculate_metrics(engine.trades)
    metrics["account_blown"] = res.get("account_blown", False)
    metrics["blown_timestamp"] = res.get("blown_timestamp", None)
    return metrics


# ==========================================
# SETUP B: Session VWAP Sigma Bands Mean-Reversion
# ==========================================
def run_setup_b(df_raw: pd.DataFrame, sigma_threshold: float = 2.0, fixed_sl_pts: float = 30.0) -> Dict:
    """
    Setup B: Session VWAP Sigma Bands Mean-Reversion
    - Time: 09:30 - 16:00 EST
    - Uses 1m continuous data
    - VWAP = cumsum(typical_price * volume) / cumsum(volume) reset at 09:30 EST each day
    - Variance = cumsum(volume * (typical_price - VWAP)^2) / cumsum(volume)
    - Upper Band = VWAP + 2.0 * sigma
    - Lower Band = VWAP - 2.0 * sigma
    - Entry Long: Price sweeps below Lower Band (low <= Lower) and closes back above Lower Band (close > Lower)
    - Entry Short: Price sweeps above Upper Band (high >= Upper) and closes back below Upper Band (close < Upper)
    - Target: Dynamic VWAP, Stop: fixed stop
    """
    print(f"\n--- Running Setup B: Session VWAP {sigma_threshold} Sigma Reversion (Stop: {fixed_sl_pts}pt, Target: VWAP) ---")
    
    df_rth = df_raw.between_time("09:30", "16:00").copy()
    df_rth["time_str"] = df_rth.index.strftime("%H:%M")
    df_rth["date"] = df_rth.index.date
    df_rth["typical_price"] = (df_rth["high"] + df_rth["low"] + df_rth["close"]) / 3.0

    trades: List[Trade] = []
    point_value = 2.0
    contracts = 2
    roundtrip_comm = 0.62 * contracts
    slippage_pts = 0.25 # 1 tick

    for date, day_df in df_rth.groupby("date"):
        vol = day_df["volume"].values
        tp = day_df["typical_price"].values
        pv = tp * vol

        cum_vol = np.cumsum(vol)
        cum_vol = np.where(cum_vol == 0, 1e-9, cum_vol)
        cum_pv = np.cumsum(pv)
        vwap_arr = cum_pv / cum_vol

        pv2 = vol * (tp ** 2)
        cum_pv2 = np.cumsum(pv2)
        variance = (cum_pv2 / cum_vol) - (vwap_arr ** 2)
        variance = np.maximum(variance, 0.0)
        sigma_arr = np.sqrt(variance)

        upper_band = vwap_arr + sigma_threshold * sigma_arr
        lower_band = vwap_arr - sigma_threshold * sigma_arr

        current_pos = 0
        entry_price = 0.0
        entry_time = None
        stop_price = 0.0
        
        highs = day_df["high"].values
        lows = day_df["low"].values
        closes = day_df["close"].values
        times = day_df.index
        time_strs = day_df["time_str"].values

        for i in range(len(day_df)):
            t_str = time_strs[i]
            b_time = times[i]
            b_high = highs[i]
            b_low = lows[i]
            b_close = closes[i]
            b_vwap = vwap_arr[i]

            # 1. Manage position if active
            if current_pos != 0:
                exit_price = None
                exit_reason = None

                if t_str >= "15:55":
                    exit_price = b_close - (slippage_pts * current_pos)
                    exit_reason = "SESSION_FLATTEN"
                elif current_pos == 1: # LONG
                    hit_sl = b_low <= stop_price
                    hit_tp = b_high >= b_vwap
                    if hit_sl and hit_tp:
                        exit_price = stop_price - slippage_pts
                        exit_reason = "SL"
                    elif hit_sl:
                        exit_price = stop_price - slippage_pts
                        exit_reason = "SL"
                    elif hit_tp:
                        exit_price = b_vwap
                        exit_reason = "TP"
                elif current_pos == -1: # SHORT
                    hit_sl = b_high >= stop_price
                    hit_tp = b_low <= b_vwap
                    if hit_sl and hit_tp:
                        exit_price = stop_price + slippage_pts
                        exit_reason = "SL"
                    elif hit_sl:
                        exit_price = stop_price + slippage_pts
                        exit_reason = "SL"
                    elif hit_tp:
                        exit_price = b_vwap
                        exit_reason = "TP"

                if exit_price is not None:
                    pts = (exit_price - entry_price) if current_pos == 1 else (entry_price - exit_price)
                    gross = pts * point_value * contracts
                    net = gross - roundtrip_comm
                    trades.append(Trade(
                        entry_time=entry_time,
                        exit_time=b_time,
                        direction=current_pos,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        stop_loss=stop_price,
                        take_profit=b_vwap,
                        contracts=contracts,
                        gross_pnl=gross,
                        net_pnl=net,
                        exit_reason=exit_reason
                    ))
                    current_pos = 0

            # 2. Look for entries if flat
            if current_pos == 0 and "09:45" <= t_str <= "15:30":
                if sigma_arr[i] > 5.0:
                    if b_low <= lower_band[i] and b_close > lower_band[i]:
                        current_pos = 1
                        entry_time = b_time
                        entry_price = b_close + slippage_pts
                        stop_price = entry_price - fixed_sl_pts

                    elif b_high >= upper_band[i] and b_close < upper_band[i]:
                        current_pos = -1
                        entry_time = b_time
                        entry_price = b_close - slippage_pts
                        stop_price = entry_price + fixed_sl_pts

    metrics = calculate_metrics(trades)
    return metrics


# ==========================================
# SETUP C: Pre-market High/Low Sweep & Reclaim (Judas Open)
# ==========================================
def run_setup_c(df_raw: pd.DataFrame, fixed_sl_pts: float = 25.0, fixed_tp_pts: float = 50.0) -> Dict:
    """
    Setup C: Pre-market High/Low Sweep & Reclaim (Judas Open)
    - Pre-market Reference Range: 00:00 - 09:15 EST (High & Low)
    - Window for Judas Sweep: 09:30 - 10:30 EST (Opening 60 minutes)
    - Long Trap: Low < PM_Low and Close > PM_Low
    - Short Trap: High > PM_High and Close < PM_High
    - Limit: 1 trade per day maximum.
    - SL/TP: fixed 25pt SL / 50pt TP (2:1 R:R)
    """
    print(f"\n--- Running Setup C: Judas Pre-Market Sweep & Reclaim (SL: {fixed_sl_pts}pt, TP: {fixed_tp_pts}pt) ---")
    
    df = df_raw.copy()
    df["time_str"] = df.index.strftime("%H:%M")
    df["date"] = df.index.date

    pm_bars = df[(df["time_str"] >= "00:00") & (df["time_str"] <= "09:15")]
    pm_highs = pm_bars.groupby("date")["high"].max().to_dict()
    pm_lows = pm_bars.groupby("date")["low"].min().to_dict()

    trades: List[Trade] = []
    point_value = 2.0
    contracts = 2
    roundtrip_comm = 0.62 * contracts
    slippage_pts = 0.25 # 1 tick

    df_rth = df.between_time("09:30", "16:00")

    for date, day_df in df_rth.groupby("date"):
        pm_h = pm_highs.get(date)
        pm_l = pm_lows.get(date)

        if pm_h is None or pm_l is None or np.isnan(pm_h) or np.isnan(pm_l):
            continue

        traded_today = False
        current_pos = 0
        entry_price = 0.0
        entry_time = None
        stop_price = 0.0
        tp_price = 0.0

        for row in day_df.itertuples():
            b_time = row.Index
            t_str = row.time_str
            b_high = row.high
            b_low = row.low
            b_close = row.close

            # 1. Manage position
            if current_pos != 0:
                exit_price = None
                exit_reason = None

                if t_str >= "15:55":
                    exit_price = b_close - (slippage_pts * current_pos)
                    exit_reason = "SESSION_FLATTEN"
                elif current_pos == 1:
                    hit_sl = b_low <= stop_price
                    hit_tp = b_high >= tp_price
                    if hit_sl and hit_tp:
                        exit_price = stop_price - slippage_pts
                        exit_reason = "SL"
                    elif hit_sl:
                        exit_price = stop_price - slippage_pts
                        exit_reason = "SL"
                    elif hit_tp:
                        exit_price = tp_price
                        exit_reason = "TP"
                elif current_pos == -1:
                    hit_sl = b_high >= stop_price
                    hit_tp = b_low <= tp_price
                    if hit_sl and hit_tp:
                        exit_price = stop_price + slippage_pts
                        exit_reason = "SL"
                    elif hit_sl:
                        exit_price = stop_price + slippage_pts
                        exit_reason = "SL"
                    elif hit_tp:
                        exit_price = tp_price
                        exit_reason = "TP"

                if exit_price is not None:
                    pts = (exit_price - entry_price) if current_pos == 1 else (entry_price - exit_price)
                    gross = pts * point_value * contracts
                    net = gross - roundtrip_comm
                    trades.append(Trade(
                        entry_time=entry_time,
                        exit_time=b_time,
                        direction=current_pos,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        stop_loss=stop_price,
                        take_profit=tp_price,
                        contracts=contracts,
                        gross_pnl=gross,
                        net_pnl=net,
                        exit_reason=exit_reason
                    ))
                    current_pos = 0

            # 2. Check for entry
            if current_pos == 0 and not traded_today:
                if "09:30" <= t_str <= "10:30":
                    if b_high > pm_h and b_close < pm_h:
                        current_pos = -1
                        entry_time = b_time
                        entry_price = b_close - slippage_pts
                        stop_price = entry_price + fixed_sl_pts
                        tp_price = entry_price - fixed_tp_pts
                        traded_today = True

                    elif b_low < pm_l and b_close > pm_l:
                        current_pos = 1
                        entry_time = b_time
                        entry_price = b_close + slippage_pts
                        stop_price = entry_price - fixed_sl_pts
                        tp_price = entry_price + fixed_tp_pts
                        traded_today = True

    metrics = calculate_metrics(trades)
    return metrics


def main():
    print("=" * 70)
    print("QUANTITATIVE LEVEL 1 BASELINE BACKTEST (CME MNQ 1-MIN CONTINUOUS)")
    print("=" * 70)

    print(f"Loading continuous dataset: {DATA_PATH}")
    df_raw = pd.read_csv(DATA_PATH, parse_dates=["datetime"])
    df_raw.set_index("datetime", inplace=True)
    print(f"Loaded {len(df_raw):,} 1m bars from {df_raw.index[0]} to {df_raw.index[-1]}.")

    # Run Setup A variants (20/40, 30/30, 40/40)
    res_a_20_40 = run_setup_a(df_raw, fixed_sl_pts=20.0, fixed_tp_pts=40.0)
    res_a_30_30 = run_setup_a(df_raw, fixed_sl_pts=30.0, fixed_tp_pts=30.0)
    res_a_40_40 = run_setup_a(df_raw, fixed_sl_pts=40.0, fixed_tp_pts=40.0)

    # Run Setup B variants (2.0 sigma, 2.5 sigma)
    res_b_20 = run_setup_b(df_raw, sigma_threshold=2.0, fixed_sl_pts=30.0)
    res_b_25 = run_setup_b(df_raw, sigma_threshold=2.5, fixed_sl_pts=30.0)

    # Run Setup C variants (25/50, 30/60, 20/40)
    res_c_25_50 = run_setup_c(df_raw, fixed_sl_pts=25.0, fixed_tp_pts=50.0)
    res_c_30_60 = run_setup_c(df_raw, fixed_sl_pts=30.0, fixed_tp_pts=60.0)
    res_c_20_40 = run_setup_c(df_raw, fixed_sl_pts=20.0, fixed_tp_pts=40.0)

    print("\n" + "=" * 70)
    print("SUMMARY RESULTS MATRIX")
    print("=" * 70)
    
    experiments = [
        ("Setup A: IB Breakout (SL 20 / TP 40)", res_a_20_40),
        ("Setup A: IB Breakout (SL 30 / TP 30)", res_a_30_30),
        ("Setup A: IB Breakout (SL 40 / TP 40)", res_a_40_40),
        ("Setup B: VWAP Reversion (2.0 Sigma, SL 30)", res_b_20),
        ("Setup B: VWAP Reversion (2.5 Sigma, SL 30)", res_b_25),
        ("Setup C: Judas Sweep (SL 25 / TP 50)", res_c_25_50),
        ("Setup C: Judas Sweep (SL 30 / TP 60)", res_c_30_60),
        ("Setup C: Judas Sweep (SL 20 / TP 40)", res_c_20_40),
    ]

    for name, exp in experiments:
        print(f"\n[{name}]")
        print(f"  Trades: {exp['total_trades']}")
        print(f"  Win Rate: {exp['win_rate']}%")
        print(f"  Profit Factor: {exp['profit_factor']}")
        print(f"  Net PnL: ${exp['net_pnl']:,.2f}")
        print(f"  Max Drawdown: ${exp['max_drawdown']:,.2f}")
        print(f"  Monthly Avg Return: ${exp['monthly_avg_return']:,.2f}")
        print(f"  Avg Trade Expectancy: ${exp['avg_trade']:,.2f}")


if __name__ == "__main__":
    main()
