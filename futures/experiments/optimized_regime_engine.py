"""
Optimized Hybrid Regime Engine for CME MNQ/NQ Futures
Integrates:
- Setup A (Conditioned Initial Balance Breakout):
    * Filtered by ADX(14) >= 25 AND Kaufman Efficiency Ratio (KER) >= 0.35
    * Time Window: 10:00 - 11:30 EST
    * Trigger: 5-minute bar closes beyond Initial Balance (09:30-10:00 EST range)
    * SL/TP: 20pt / 40pt (1:2 R:R)
- Setup C (Judas Pre-Market Sweep & Reclaim):
    * Trigger: 1-minute bar sweeps Pre-Market (00:00-09:15 EST) High/Low
    * Absorption Wick Filter: Rejection wick >= 40% of candle range (or clean reclaim)
    * Regime Activation: ADX(14) < 25 or PM extreme sweep absorption
    * Time Window: 09:30 - 10:30 EST
    * SL/TP: 20pt / 40pt
- Risk & Drawdown Protections:
    * Max 1-2 trades/day hard circuit breaker.
    * Loss Pause Filter: Halts subsequent trading on the day immediately after a loss to prevent consecutive loss sequences.
    * Evaluation of fixed sizing (1 MNQ, 2 MNQ, 3 MNQ, 5 MNQ) vs. dynamic buffer sizing.
"""

import sys
import os
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

# Path configuration
ENGINE_DIR = r"futures\engine"
sys.path.append(ENGINE_DIR)

from futures_engine import Trade
from filter_library import compute_atr, compute_adx, compute_kaufman_efficiency_ratio

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
    peak_equity = account_size
    drawdowns = []
    
    for p in pnls:
        equity += p
        if equity > peak_equity:
            peak_equity = equity
        drawdowns.append(peak_equity - equity)

    max_dd = max(drawdowns) if drawdowns else 0.0

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


def run_hybrid_simulation(
    df_raw: pd.DataFrame,
    contracts_mode: str = "fixed", # "fixed", "dynamic_buffer"
    fixed_contracts: int = 2,
    max_trades_per_day: int = 2,
    loss_pause_filter: bool = False,
    enable_breakout: bool = True,
    enable_judas: bool = True,
    adx_threshold: float = 25.0,
    ker_threshold: float = 0.35,
    wick_threshold: float = 0.0,
    breakout_sl_pts: float = 20.0,
    breakout_tp_pts: float = 40.0,
    judas_sl_pts: float = 20.0,
    judas_tp_pts: float = 40.0,
    daily_loss_limit: float = 1000.0,
    point_value: float = 2.0,
    slippage_ticks: int = 1,
    tick_size: float = 0.25,
    roundtrip_comm_per_contract: float = 0.62,
    account_size: float = 50_000.0
) -> Tuple[Dict, List[Trade]]:
    """
    Executes a unified, deterministic bar-by-bar hybrid backtest on 1-minute data,
    evaluating 5-minute IB Breakouts and 1-minute Judas Absorption Sweeps.
    """
    slippage_pts = slippage_ticks * tick_size
    
    # 1. Prepare base dataframe
    df = df_raw.copy()
    df["time_str"] = df.index.strftime("%H:%M")
    df["date"] = df.index.date
    df["minute"] = df.index.minute

    # 2. Compute Indicators on 1m
    df["atr14"] = compute_atr(df, period=14)
    adx_1m, _, _ = compute_adx(df, period=14)
    df["adx14"] = adx_1m
    df["ker10"] = compute_kaufman_efficiency_ratio(df, period=10)

    # 3. Precalculate Pre-Market Extrema (00:00 - 09:15 EST)
    pm_bars = df[(df["time_str"] >= "00:00") & (df["time_str"] <= "09:15")]
    pm_highs = pm_bars.groupby("date")["high"].max().to_dict()
    pm_lows = pm_bars.groupby("date")["low"].min().to_dict()

    # 4. Precalculate Initial Balance (09:30 - 09:59 EST)
    ib_bars = df[(df["time_str"] >= "09:30") & (df["time_str"] < "10:00")]
    ib_highs = ib_bars.groupby("date")["high"].max().to_dict()
    ib_lows = ib_bars.groupby("date")["low"].min().to_dict()

    # 5. Filter for Regular Trading Hours (09:30 - 16:00 EST)
    df_rth = df.between_time("09:30", "16:00").copy()

    trades: List[Trade] = []
    
    # Tracking
    current_equity = account_size
    current_day = None
    daily_pnl = 0.0
    daily_trade_count = 0
    daily_loss_count = 0
    daily_locked_out = False

    current_pos = 0 # 0 Flat, 1 Long, -1 Short
    entry_time = None
    entry_price = 0.0
    stop_price = 0.0
    tp_price = 0.0
    active_contracts = fixed_contracts
    active_setup = None # "BREAKOUT" or "JUDAS"

    # Tracking 5m bars for IB breakout
    cur_5m_open = 0.0
    cur_5m_high = -1e9
    cur_5m_low = 1e9

    for bar in df_rth.itertuples():
        b_time = bar.Index
        b_day = bar.date
        t_str = bar.time_str
        b_open = bar.open
        b_high = bar.high
        b_low = bar.low
        b_close = bar.close
        b_adx = bar.adx14
        b_ker = bar.ker10

        # Day Boundary Reset
        if current_day != b_day:
            current_day = b_day
            daily_pnl = 0.0
            daily_trade_count = 0
            daily_loss_count = 0
            daily_locked_out = False
            cur_5m_high = -1e9
            cur_5m_low = 1e9

        # Daily loss lockout
        if daily_pnl <= -daily_loss_limit:
            daily_locked_out = True

        # Loss Pause Filter check
        if loss_pause_filter and daily_loss_count >= 1:
            daily_locked_out = True

        # Track 5m bar construction
        if bar.minute % 5 == 0:
            cur_5m_open = b_open
            cur_5m_high = b_high
            cur_5m_low = b_low
        else:
            if b_high > cur_5m_high: cur_5m_high = b_high
            if b_low < cur_5m_low: cur_5m_low = b_low
        
        is_5m_close = (bar.minute % 5 == 4)

        # -------------------------------------------------------------
        # STEP 1: MANAGE OPEN POSITION
        # -------------------------------------------------------------
        if current_pos != 0:
            exit_price = None
            exit_reason = None

            # Flatten at 15:55 EST
            if t_str >= "15:55":
                exit_price = b_close - (slippage_pts * current_pos)
                exit_reason = "SESSION_FLATTEN"
            elif current_pos == 1: # LONG
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

            elif current_pos == -1: # SHORT
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
                gross = pts * point_value * active_contracts
                comm = roundtrip_comm_per_contract * active_contracts
                net = gross - comm

                daily_pnl += net
                current_equity += net
                if net <= 0:
                    daily_loss_count += 1

                trades.append(Trade(
                    entry_time=entry_time,
                    exit_time=b_time,
                    direction=current_pos,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    stop_loss=stop_price,
                    take_profit=tp_price,
                    contracts=active_contracts,
                    gross_pnl=gross,
                    net_pnl=net,
                    exit_reason=f"{active_setup}_{exit_reason}"
                ))

                current_pos = 0
                active_setup = None

        # -------------------------------------------------------------
        # STEP 2: CHECK FOR NEW ENTRIES
        # -------------------------------------------------------------
        can_enter = (current_pos == 0) and (not daily_locked_out) and (daily_trade_count < max_trades_per_day) and (t_str < "15:45")
        
        if can_enter:
            pm_h = pm_highs.get(b_day)
            pm_l = pm_lows.get(b_day)
            ib_h = ib_highs.get(b_day)
            ib_l = ib_lows.get(b_day)

            # Contract sizing calculation
            if contracts_mode == "dynamic_buffer":
                profit_buffer = max(0.0, current_equity - account_size)
                if profit_buffer < 600:
                    pos_contracts = 1
                elif profit_buffer < 1200:
                    pos_contracts = 2
                elif profit_buffer < 2000:
                    pos_contracts = 3
                else:
                    pos_contracts = 4
            else:
                pos_contracts = fixed_contracts

            # =========================================================
            # SETUP C: JUDAS SWEEP WITH ABSORPTION WICK FILTER
            # Window: 09:30 - 10:30 EST
            # =========================================================
            if enable_judas and ("09:30" <= t_str <= "10:30") and (pm_h is not None) and (pm_l is not None):
                c_range = b_high - b_low
                if c_range > 0.5:
                    upper_wick = b_high - max(b_open, b_close)
                    wick_ratio_upper = upper_wick / c_range
                    
                    lower_wick = min(b_open, b_close) - b_low
                    wick_ratio_lower = lower_wick / c_range

                    # Short Judas
                    if (b_high > pm_h) and (b_close < pm_h) and (wick_ratio_upper >= wick_threshold):
                        if b_adx < adx_threshold or b_ker < ker_threshold:
                            current_pos = -1
                            active_setup = "JUDAS"
                            active_contracts = pos_contracts
                            entry_time = b_time
                            entry_price = b_close - slippage_pts
                            stop_price = entry_price + judas_sl_pts
                            tp_price = entry_price - judas_tp_pts
                            daily_trade_count += 1
                            continue

                    # Long Judas
                    elif (b_low < pm_l) and (b_close > pm_l) and (wick_ratio_lower >= wick_threshold):
                        if b_adx < adx_threshold or b_ker < ker_threshold:
                            current_pos = 1
                            active_setup = "JUDAS"
                            active_contracts = pos_contracts
                            entry_time = b_time
                            entry_price = b_close + slippage_pts
                            stop_price = entry_price - judas_sl_pts
                            tp_price = entry_price + judas_tp_pts
                            daily_trade_count += 1
                            continue

            # =========================================================
            # SETUP A: INITIAL BALANCE BREAKOUT GATED BY REGIME
            # Window: 10:00 - 11:30 EST (Institutional window)
            # Gate: ADX(14) >= 25 AND KER(10) >= 0.35 (or 0.45)
            # =========================================================
            if enable_breakout and is_5m_close and ("10:00" <= t_str <= "11:30") and (ib_h is not None) and (ib_l is not None):
                is_trending = (b_adx >= adx_threshold) and (b_ker >= ker_threshold)
                
                if is_trending:
                    if b_close > ib_h:
                        current_pos = 1
                        active_setup = "BREAKOUT"
                        active_contracts = pos_contracts
                        entry_time = b_time
                        entry_price = b_close + slippage_pts
                        stop_price = entry_price - breakout_sl_pts
                        tp_price = entry_price + breakout_tp_pts
                        daily_trade_count += 1
                    elif b_close < ib_l:
                        current_pos = -1
                        active_setup = "BREAKOUT"
                        active_contracts = pos_contracts
                        entry_time = b_time
                        entry_price = b_close - slippage_pts
                        stop_price = entry_price + breakout_sl_pts
                        tp_price = entry_price - breakout_tp_pts
                        daily_trade_count += 1

    metrics = calculate_metrics(trades, account_size)
    return metrics, trades


def main():
    print("=" * 80)
    print("OPTIMIZED REGIME HYBRID STRATEGY: SETUP A + SETUP C WITH ADVANCED FILTERS")
    print("=" * 80)

    print(f"Loading continuous MNQ 1m data from: {DATA_PATH}")
    df_raw = pd.read_csv(DATA_PATH, parse_dates=["datetime"])
    df_raw.set_index("datetime", inplace=True)
    print(f"Loaded {len(df_raw):,} 1m bars from {df_raw.index[0]} to {df_raw.index[-1]}.")

    scenarios = [
        ("Base_Hybrid_2MNQ", "fixed", 2, 2, False, 0.35, 0.0),
        ("Shield_LossPause_1MNQ", "fixed", 1, 1, True, 0.45, 0.0),
        ("Shield_LossPause_2MNQ", "fixed", 2, 2, True, 0.45, 0.0),
        ("Shield_LossPause_3MNQ", "fixed", 3, 2, True, 0.45, 0.0),
        ("Shield_LossPause_5MNQ", "fixed", 5, 2, True, 0.45, 0.0),
        ("DynamicBuffer_Shield", "dynamic_buffer", 1, 2, True, 0.45, 0.0)
    ]

    results_table = []

    for name, mode, fixed_cnt, max_t, lp_filter, ker_t, wick_t in scenarios:
        metrics, trades = run_hybrid_simulation(
            df_raw=df_raw,
            contracts_mode=mode,
            fixed_contracts=fixed_cnt,
            max_trades_per_day=max_t,
            loss_pause_filter=lp_filter,
            enable_breakout=True,
            enable_judas=True,
            adx_threshold=25.0,
            ker_threshold=ker_t,
            wick_threshold=wick_t,
            breakout_sl_pts=20.0,
            breakout_tp_pts=40.0,
            judas_sl_pts=20.0,
            judas_tp_pts=40.0,
            daily_loss_limit=1000.0,
            account_size=50_000.0
        )

        results_table.append({
            "Scenario": name,
            "Trades": metrics["total_trades"],
            "Win Rate (%)": metrics["win_rate"],
            "Profit Factor": metrics["profit_factor"],
            "Net PnL ($)": metrics["net_pnl"],
            "Max DD ($)": metrics["max_drawdown"],
            "Monthly Avg ($)": metrics["monthly_avg_return"],
            "Avg Trade ($)": metrics["avg_trade"],
            "Monthly Breakdown": metrics["monthly_pnl"]
        })

    print("\n" + "=" * 80)
    print("FINAL SUMMARY COMPARISON TABLE")
    print("=" * 80)
    df_summary = pd.DataFrame(results_table)[["Scenario", "Trades", "Win Rate (%)", "Profit Factor", "Net PnL ($)", "Max DD ($)", "Monthly Avg ($)"]]
    print(df_summary.to_string(index=False))

    print("\n" + "=" * 80)
    print("MONTH-BY-MONTH PnL BREAKDOWN FOR KEY SCENARIOS")
    print("=" * 80)
    for r in results_table:
        print(f"\nScenario: {r['Scenario']} (Net: ${r['Net PnL ($)']:,.2f}, Max DD: ${r['Max DD ($)']:,.2f})")
        for m, val in r["Monthly Breakdown"].items():
            print(f"  {m}: ${val:,.2f}")


if __name__ == "__main__":
    main()
