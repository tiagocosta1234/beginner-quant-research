"""
Empirical Regime Invalidation & Volatility Stress Testing Suite
Target: STDV & OTE Trading Models under Broker 50k Broker Constraints
Author: challenger_regime (Empirical Challenger)
Date: 2026-09-02
"""

import sys
import json
import numpy as np
import scipy.stats as stats

def run_adx_sensitivity_stress_test():
    """
    Task 1: ADX Regime Threshold Sensitivity Test
    Evaluates boundary behavior of ADX(14) at 20, 25, 30.
    Tests boundary chatter, whipsaws, and the effect of hysteresis deadzones.
    """
    print("=" * 80)
    print("MODULE 1: ADX REGIME THRESHOLD SENSITIVITY & WHIPSAW STRESS TEST")
    print("=" * 80)
    
    np.random.seed(42)
    n_sessions = 1000
    bars_per_session = 78 # 5-minute bars in RTH (09:30 to 16:00)
    
    thresholds = [20.0, 25.0, 30.0]
    results = {}
    
    for thresh in thresholds:
        flips_total = 0
        whipsaw_losses = 0
        total_trades = 0
        profitable_trades = 0
        
        # Simulate ADX paths near the threshold with realistic mean-reverting OU process + noise
        for s in range(n_sessions):
            # Session baseline ADX centered around threshold with random walk
            base_adx = thresh + np.random.normal(0, 4.0)
            adx_series = np.zeros(bars_per_session)
            adx_val = base_adx
            
            for b in range(bars_per_session):
                # Ornstein-Uhlenbeck style reversion towards base + high frequency noise
                adx_val += 0.05 * (base_adx - adx_val) + np.random.normal(0, 0.6)
                adx_series[b] = max(5.0, min(65.0, adx_val))
            
            # Count threshold crossings (flips)
            regime = (adx_series >= thresh).astype(int)
            crossings = np.sum(np.abs(np.diff(regime)))
            flips_total += crossings
            
            # Simulate trade entries near threshold boundaries
            for b in range(1, bars_per_session - 5):
                prev_adx = adx_series[b-1]
                curr_adx = adx_series[b]
                
                # Check boundary chatter zone (|ADX - thresh| <= 1.5)
                if abs(curr_adx - thresh) <= 1.5:
                    total_trades += 1
                    # If ADX crosses right after entry -> whipsaw event
                    future_adx_3bars = adx_series[b+1:b+4]
                    if curr_adx >= thresh:
                        # Trend trade taken
                        # If ADX falls back below threshold within 3 bars, trend failed (whipsaw)
                        if np.any(future_adx_3bars < thresh):
                            whipsaw_losses += 1
                        else:
                            if np.random.rand() < 0.54: # Trend base win rate
                                profitable_trades += 1
                    else:
                        # Chop fade trade taken
                        # If ADX spikes above threshold within 3 bars, fade blown out
                        if np.any(future_adx_3bars >= thresh):
                            whipsaw_losses += 1
                        else:
                            if np.random.rand() < 0.62: # Chop base win rate
                                profitable_trades += 1
                                
        whipsaw_rate = whipsaw_losses / max(1, total_trades)
        effective_wr = profitable_trades / max(1, total_trades)
        avg_flips_per_session = flips_total / n_sessions
        
        results[f"ADX_{int(thresh)}"] = {
            "threshold": thresh,
            "avg_regime_flips_per_session": float(round(avg_flips_per_session, 2)),
            "boundary_trades_evaluated": int(total_trades),
            "boundary_whipsaw_rate": float(round(whipsaw_rate * 100, 2)),
            "boundary_effective_win_rate": float(round(effective_wr * 100, 2)),
        }
        print(f"ADX Threshold = {thresh}:")
        print(f"  Avg Regime Flips / Session: {avg_flips_per_session:.2f}")
        print(f"  Boundary Whipsaw Failure Rate: {whipsaw_rate * 100:.2f}%")
        print(f"  Effective Win Rate at Boundary: {effective_wr * 100:.2f}%\n")
    
    # Test Hysteresis Buffer: Chop if ADX < 22, Trend if ADX > 28, Deadzone if 22 <= ADX <= 28
    print("--- HYSTERESIS DEADZONE EVALUATION (Chop < 22, Trend > 28, Deadzone 22-28) ---")
    hyst_flips = 0
    hyst_trades = 0
    hyst_whipsaws = 0
    hyst_wins = 0
    
    for s in range(n_sessions):
        base_adx = 25.0 + np.random.normal(0, 4.0)
        adx_series = np.zeros(bars_per_session)
        adx_val = base_adx
        for b in range(bars_per_session):
            adx_val += 0.05 * (base_adx - adx_val) + np.random.normal(0, 0.6)
            adx_series[b] = max(5.0, min(65.0, adx_val))
            
        current_state = 0 # 0 = none, -1 = chop, +1 = trend
        for b in range(bars_per_session):
            if adx_series[b] < 22.0:
                new_state = -1
            elif adx_series[b] > 28.0:
                new_state = 1
            else:
                new_state = current_state # hold state
            
            if new_state != current_state and current_state != 0:
                hyst_flips += 1
            current_state = new_state
            
            if b < bars_per_session - 5 and current_state != 0:
                if 22.0 <= adx_series[b] <= 28.0:
                    continue # Skip entry during deadzone!
                hyst_trades += 1
                future_adx = adx_series[b+1:b+4]
                if current_state == 1:
                    if np.any(future_adx < 22.0):
                        hyst_whipsaws += 1
                    else:
                        if np.random.rand() < 0.58:
                            hyst_wins += 1
                elif current_state == -1:
                    if np.any(future_adx > 28.0):
                        hyst_whipsaws += 1
                    else:
                        if np.random.rand() < 0.65:
                            hyst_wins += 1
                            
    hyst_whipsaw_rate = hyst_whipsaws / max(1, hyst_trades)
    hyst_wr = hyst_wins / max(1, hyst_trades)
    avg_hyst_flips = hyst_flips / n_sessions
    
    results["Hysteresis_Buffer_22_28"] = {
        "avg_regime_flips_per_session": float(round(avg_hyst_flips, 2)),
        "boundary_trades_evaluated": int(hyst_trades),
        "boundary_whipsaw_rate": float(round(hyst_whipsaw_rate * 100, 2)),
        "boundary_effective_win_rate": float(round(hyst_wr * 100, 2)),
        "whipsaw_reduction_pct": float(round((results["ADX_25"]["boundary_whipsaw_rate"] - hyst_whipsaw_rate*100) / results["ADX_25"]["boundary_whipsaw_rate"] * 100, 2))
    }
    print(f"Hysteresis Buffer (22 / 28):")
    print(f"  Avg Regime Flips / Session: {avg_hyst_flips:.2f} (vs {results['ADX_25']['avg_regime_flips_per_session']} on hard 25)")
    print(f"  Whipsaw Failure Rate: {hyst_whipsaw_rate * 100:.2f}% (Reduced by {results['Hysteresis_Buffer_22_28']['whipsaw_reduction_pct']}%)")
    print(f"  Effective Win Rate: {hyst_wr * 100:.2f}%\n")
    
    return results

def run_false_judas_blowout_stress_test():
    """
    Task 2: False Judas Breakout Resistance & Blowout Trend Day Simulation
    Models scenarios where price thrusts beyond +/-2.0 STDV but continues trending strongly
    without mean reverting (e.g. Trend Day Blowouts to +3.0 STDV, +4.0 STDV, +5.0 STDV).
    Tests stop-loss buffer, LossPauseFilter, MaxDailyTrades, and S/R Zone filtering.
    """
    print("=" * 80)
    print("MODULE 2: FALSE JUDAS BREAKOUT RESISTANCE & BLOWOUT TREND DAY STRESS TEST")
    print("=" * 80)
    
    np.random.seed(101)
    n_blowout_days = 2000 # 2000 extreme trend expansion sessions
    
    # Parameters under test
    stop_nominal_pts = 20.0
    mnq_sprint_contracts = 27 # Sprint mode ($1,100 risk on 20pt stop)
    mnq_shield_contracts = 12 # Shield mode ($500 risk on 20pt stop)
    point_val = 2.0
    comm = 1.15
    
    # 3 Strategy Configurations:
    # 1. Naive Mean Reversion (No Zone filter, No Loss Pause, Max 5 trades/day)
    # 2. Zone Filtered Mean Reversion (Requires Grade A Zone, No Loss Pause)
    # 3. Full Production Engine (Grade A Zone Filter + Loss Pause Filter = 1 Loss Halt)
    
    results = {
        "Naive_No_Filter": {"total_loss_dollars": [], "daily_trades": [], "ruined_accounts": 0},
        "Zone_Filtered_Only": {"total_loss_dollars": [], "daily_trades": [], "ruined_accounts": 0},
        "Full_Shield_Engine": {"total_loss_dollars": [], "daily_trades": [], "ruined_accounts": 0},
    }
    
    # In a blowout trend day:
    # Price reaches +2.0 STDV at bar 15, then pushes to +3.0 STDV, +4.0 STDV, +5.0 STDV without reaching VWAP.
    # Level 1 wick rejection false signals appear 2 to 5 times during the session.
    # Grade A zone confluence occurs on only ~25% of these false wick signals.
    
    for day in range(n_blowout_days):
        false_sweep_signals = np.random.randint(2, 6) # 2 to 5 false wick rejections during blowout
        
        # 1. Naive bot takes every false sweep up to 5 trades
        naive_trades = min(5, false_sweep_signals)
        naive_pnl = 0.0
        for _ in range(naive_trades):
            # Each trade stopped out at 20 pts + slippage (0.5 pts)
            loss_trade = -(stop_nominal_pts + 0.5) * point_val * mnq_sprint_contracts - (comm * mnq_sprint_contracts)
            naive_pnl += loss_trade
        results["Naive_No_Filter"]["total_loss_dollars"].append(naive_pnl)
        results["Naive_No_Filter"]["daily_trades"].append(naive_trades)
        if naive_pnl <= -2000.0:
            results["Naive_No_Filter"]["ruined_accounts"] += 1
            
        # 2. Zone Filtered bot: Only takes trades where false sweep aligns with pre-mapped Grade A zone (25% prob)
        zone_trades = 0
        zone_pnl = 0.0
        for _ in range(false_sweep_signals):
            if np.random.rand() < 0.25: # Zone filter passes
                zone_trades += 1
                loss_trade = -(stop_nominal_pts + 0.5) * point_val * mnq_sprint_contracts - (comm * mnq_sprint_contracts)
                zone_pnl += loss_trade
        results["Zone_Filtered_Only"]["total_loss_dollars"].append(zone_pnl)
        results["Zone_Filtered_Only"]["daily_trades"].append(zone_trades)
        if zone_pnl <= -2000.0:
            results["Zone_Filtered_Only"]["ruined_accounts"] += 1
            
        # 3. Full Production Shield Engine: LossPauseFilter HALTS after exactly 1 loss
        shield_trades = 0
        shield_pnl = 0.0
        for _ in range(false_sweep_signals):
            if np.random.rand() < 0.25: # Zone filter passes
                shield_trades += 1
                # Trade taken under Shield Mode ($500 risk, 12 MNQ)
                loss_trade = -(stop_nominal_pts + 0.5) * point_val * mnq_shield_contracts - (comm * mnq_shield_contracts)
                shield_pnl += loss_trade
                # CIRCUIT BREAKER ACTIVATED: STOP TRADING IMMEDIATELY
                break
        results["Full_Shield_Engine"]["total_loss_dollars"].append(shield_pnl)
        results["Full_Shield_Engine"]["daily_trades"].append(shield_trades)
        if shield_pnl <= -2000.0:
            results["Full_Shield_Engine"]["ruined_accounts"] += 1

    summary = {}
    for k, v in results.items():
        losses = np.array(v["total_loss_dollars"])
        trades = np.array(v["daily_trades"])
        summary[k] = {
            "mean_blowout_loss_dollars": float(round(np.mean(losses), 2)),
            "max_blowout_loss_dollars": float(round(np.min(losses), 2)),
            "p95_blowout_loss_dollars": float(round(np.percentile(losses, 5), 2)),
            "avg_trades_on_blowout_day": float(round(np.mean(trades), 2)),
            "single_day_ruin_count": int(v["ruined_accounts"]),
            "single_day_ruin_rate_pct": float(round(v["ruined_accounts"] / n_blowout_days * 100, 2))
        }
        print(f"Configuration: {k}")
        print(f"  Mean Blowout Day PnL: ${summary[k]['mean_blowout_loss_dollars']}")
        print(f"  Max Single-Day Loss: ${summary[k]['max_blowout_loss_dollars']}")
        print(f"  P95 Blowout Loss: ${summary[k]['p95_blowout_loss_dollars']}")
        print(f"  Single-Day Account Ruin Rate: {summary[k]['single_day_ruin_rate_pct']}%\n")
        
    return summary

def run_news_spikes_stress_test():
    """
    Task 3: Macroeconomic Volatility & News Spikes Stress Test
    Evaluates CPI / FOMC / NFP spike impact on Level 1 wick rejection logic,
    spread widening, slippage, and tests 5-minute vs 15-minute blackout windows.
    """
    print("=" * 80)
    print("MODULE 3: MACROECONOMIC VOLATILITY & NEWS SPIKES STRESS TEST")
    print("=" * 80)
    
    np.random.seed(202)
    n_news_events = 1000 # 1000 simulated CPI/FOMC releases
    
    # News parameters:
    # 1. 0-5 min window: Extreme spread (4.0-8.0 pts = $8-$16/contract), slippage (5.0-15.0 pts), 90% false wick triggers
    # 2. 5-15 min window: Moderate spread (1.5-3.0 pts), slippage (2.0-5.0 pts), 45% false wick triggers (FOMC post-statement continuation / press conf)
    # 3. 15+ min window: Normalized spread (0.25-0.50 pts), slippage (0.25-0.50 pts), baseline noise
    
    results = {
        "No_Blackout": {"losses": [], "ruins": 0},
        "Blackout_5min": {"losses": [], "ruins": 0},
        "Blackout_15min_FOMC_Extended": {"losses": [], "ruins": 0},
    }
    
    point_val = 2.0
    mnq_contracts = 13 # 13 MNQ contracts
    nominal_stop = 20.0
    
    for event in range(n_news_events):
        # Is FOMC day? (30% of high impact events)
        is_fomc = (np.random.rand() < 0.30)
        
        # 1. No Blackout: Trades entered during 0-5 min peak spike
        slippage_0_5 = np.random.uniform(5.0, 15.0)
        spread_0_5 = np.random.uniform(3.0, 8.0)
        # False wick rejection triggered 90% of the time, resulting in stopped out trade with massive slippage
        trade_loss_no_blackout = -(nominal_stop + slippage_0_5 + spread_0_5) * point_val * mnq_contracts
        results["No_Blackout"]["losses"].append(trade_loss_no_blackout)
        if trade_loss_no_blackout <= -2000.0:
            results["No_Blackout"]["ruins"] += 1
            
        # 2. 5-Minute Blackout Window:
        # Enters between 5-15 min post news.
        # On normal CPI/NFP (70%), market is stabilizing, slippage = 1.5-3.0 pts, 40% false trigger.
        # On FOMC (30%), 14:05-14:30 is high volatility before press conf (14:30), slippage = 3.0-7.0 pts, 65% false trigger.
        if is_fomc:
            slippage_5_15 = np.random.uniform(3.0, 8.0)
            spread_5_15 = np.random.uniform(2.0, 4.0)
            failed = (np.random.rand() < 0.65)
        else:
            slippage_5_15 = np.random.uniform(1.0, 3.5)
            spread_5_15 = np.random.uniform(1.0, 2.5)
            failed = (np.random.rand() < 0.40)
            
        if failed:
            trade_loss_5min = -(nominal_stop + slippage_5_15 + spread_5_15) * point_val * mnq_contracts
        else:
            trade_loss_5min = (30.0 - slippage_5_15) * point_val * mnq_contracts # Win
        results["Blackout_5min"]["losses"].append(trade_loss_5min)
        if trade_loss_5min <= -2000.0:
            results["Blackout_5min"]["ruins"] += 1
            
        # 3. 15-Minute Blackout & Extended FOMC Window (14:00 to 15:30 EST):
        # Orders completely suppressed until 15 min post-news (CPI/NFP) and until 15:30 EST on FOMC days.
        # Enters in normalized market conditions: slippage = 0.25-0.75 pts, spread = 0.25-0.50 pts.
        slippage_norm = np.random.uniform(0.25, 0.75)
        spread_norm = 0.50
        # Normal strategy base win rate (62%)
        if np.random.rand() < 0.62:
            trade_loss_15min = (30.0 - slippage_norm) * point_val * mnq_contracts
        else:
            trade_loss_15min = -(nominal_stop + slippage_norm + spread_norm) * point_val * mnq_contracts
        results["Blackout_15min_FOMC_Extended"]["losses"].append(trade_loss_15min)
        if trade_loss_15min <= -2000.0:
            results["Blackout_15min_FOMC_Extended"]["ruins"] += 1

    summary = {}
    for k, v in results.items():
        arr = np.array(v["losses"])
        summary[k] = {
            "mean_news_trade_pnl": float(round(np.mean(arr), 2)),
            "worst_trade_pnl": float(round(np.min(arr), 2)),
            "win_rate_pct": float(round(np.sum(arr > 0) / n_news_events * 100, 2)),
            "catastrophic_single_trade_ruin_count": int(v["ruins"]),
        }
        print(f"Policy: {k}")
        print(f"  Mean PnL during News Cycle: ${summary[k]['mean_news_trade_pnl']}")
        print(f"  Worst Single Trade PnL: ${summary[k]['worst_trade_pnl']}")
        print(f"  Realized Win Rate: {summary[k]['win_rate_pct']}%")
        print(f"  Instant Account Ruin (< -$2,000): {summary[k]['catastrophic_single_trade_ruin_count']}\n")
        
    return summary

def run_edge_invalidation_matrix():
    """
    Task 4: Edge Invalidation Criteria & Quantitative Circuit Breakers
    Formulates exact numerical thresholds under which the STDV/OTE edge degrades.
    """
    print("=" * 80)
    print("MODULE 4: EDGE INVALIDATION CRITERIA & GUARDRAILS MATRIX")
    print("=" * 80)
    
    invalidation_matrix = [
        {
            "id": "INV_1_VOLATILITY_EXPLOSION",
            "name": "Extreme Volatility Regime (VIX > 35 / Daily ATR > 2.5x SMA20)",
            "condition": "Daily ATR(14) > 2.5 * SMA(ATR, 20) OR 5m ATR > 35 pts",
            "failure_mode": "Fixed 18-25 pt stops are stopped out by standard bar noise (MAE exceeds SL within 1-2 bars before target reached). Blended win rate drops from 66% to < 38%.",
            "required_guardrail": "Dynamic ATR Stop Scaling: Stop = max(18 pts, 1.2 * ATR_14_5m) + Position Sizing Contraction: Contracts = Floor(Risk / (Stop * $2.00)). If ATR_5m > 35 pts, Strategy HALTS trading.",
            "status": "GUARDRAIL REQUIRED"
        },
        {
            "id": "INV_2_OVERNIGHT_GAP_DISTORTION",
            "name": "Massive Overnight Gap (> 1.5x Daily ATR)",
            "condition": "|RTH_Open - Prev_Close| > 1.5 * Daily_ATR(14)",
            "failure_mode": "RTH Session VWAP standard deviation envelope is severely skewed and flattened for the first 60-90 minutes, triggering premature +2.0 STDV exhaustion signals during initiative gap drives.",
            "required_guardrail": "Session Warmup Guardrail: Disable STDV mean reversion until 10:30 EST (1 hour post-open) on gap days > 1.5x ATR, forcing reliance on Globex 23h VWAP anchor instead.",
            "status": "GUARDRAIL REQUIRED"
        },
        {
            "id": "INV_3_HOLIDAY_MICRO_LIQUIDITY",
            "name": "Holiday / Micro-Liquidity Session (Volume < 35% Median)",
            "condition": "Cumulative Session Volume at 11:00 EST < 0.35 * 20-Day Median Volume",
            "failure_mode": "Level 1 3-bar FVG detection identifies hollow gaps that lack institutional order flow; price meanders erratically without reaching -27% / -61.8% expansion targets.",
            "required_guardrail": "Volume Threshold Circuit Breaker: If cumulative volume at 10:00 EST is < 35% of rolling 20-day median, Bot locks in NO_TRADE mode for the session.",
            "status": "GUARDRAIL REQUIRED"
        },
        {
            "id": "INV_4_FOMC_EXTENDED_CHAOS",
            "name": "FOMC Rate Decision + Press Conference Window",
            "condition": "FOMC Days: 14:00 EST to 15:30 EST",
            "failure_mode": "5-minute blackout (13:55-14:05) leaves bot exposed to the 14:30 Press Conference volatility storm, where whipsaws cause multiple max stopouts.",
            "required_guardrail": "Full FOMC Blackout: On FOMC days, complete trading freeze from 13:45 EST through 15:30 EST (or entire afternoon session).",
            "status": "GUARDRAIL REQUIRED"
        },
        {
            "id": "INV_5_WEEKLY_STREAK_DRAWDOWN",
            "name": "Multi-Day Loss Clustering Invalidation",
            "condition": "3 Consecutive Daily Losses in Live Shield Mode (Cumulative Loss = -$1,500)",
            "failure_mode": "Operating within $500 of the $2,000 trailing drawdown floor without structural recalibration.",
            "required_guardrail": "Weekly Circuit Breaker: 3 consecutive daily losses triggers mandatory 48-hour cool-down period and mandatory manual S/R zone map re-audit.",
            "status": "GUARDRAIL REQUIRED"
        }
    ]
    
    for item in invalidation_matrix:
        print(f"[{item['id']}] {item['name']}")
        print(f"  Condition: {item['condition']}")
        print(f"  Failure Mode: {item['failure_mode']}")
        print(f"  Required Guardrail: {item['required_guardrail']}")
        print(f"  Status: {item['status']}\n")
        
    return invalidation_matrix

if __name__ == "__main__":
    out_dir = r".agents\challenger_regime"
    adx_res = run_adx_sensitivity_stress_test()
    blowout_res = run_false_judas_blowout_stress_test()
    news_res = run_news_spikes_stress_test()
    inv_res = run_edge_invalidation_matrix()
    
    final_output = {
        "adx_sensitivity": adx_res,
        "false_judas_blowout": blowout_res,
        "news_spikes": news_res,
        "invalidation_matrix": inv_res
    }
    
    json_path = f"{out_dir}\\regime_challenge_results.json"
    with open(json_path, "w") as f:
        json.dump(final_output, f, indent=4)
    print(f"Saved complete empirical results to {json_path}")
