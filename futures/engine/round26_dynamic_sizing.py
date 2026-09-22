"""
Round 26: does DYNAMIC, equity-scaled position sizing beat Round 25's best
fixed-risk trade-off (P(success)~24.4% / P(ruin)~66.3% at $1,900/trade)?

Round 25 simulated the remaining ~57 trading days at a FIXED dollar risk per
trade for the whole path. This round tests risking a *fraction of the
account's current state* instead, so risk automatically shrinks after losses
(protecting what's left) and grows after wins (sizing up with profit the
market already provided, not the original buffer). This is standard
professional risk management for exactly this situation and has not been
tested anywhere in this 25-round campaign.

Method for honestly extending Round 25's real data to a path-dependent size:
  P&L scales close to linearly with risk_dollars throughout this campaign
  (confirmed repeatedly, e.g. Round 19: $66.27 at $400 risk vs $103.31 at
  $600 -- ratio 1.559 vs risk ratio 1.5, small deviation from whole-contract
  rounding only). So the real, validated daily-P&L pool at a reference risk
  level (chosen here as $600 -- large enough contract counts to minimize
  rounding noise, already used as a standard secondary level throughout the
  campaign) is converted to a pool of daily R-multiples: r = daily_pnl / 600.
  A dynamic path then applies the SAME block-bootstrapped, chronologically-
  contiguous r-sequences Round 25 used, but rescales each day's r by
  whatever dollar risk the sizing RULE assigns at that point in the path
  (a function of current equity), rather than a fixed number. This preserves
  the edge's real win rate, R-multiple distribution, and day-to-day
  autocorrelation; only the dollar SIZE applied to it varies by policy.

Honest framing, same as Round 25: the underlying edge is the same
walk-forward-validated backtest (Rounds 19-24). The Monte Carlo resampling
layer -- now with a path-dependent sizing RULE on top -- is weaker evidence
than that backtest: it tests a sizing POLICY's simulated outcome against the
edge's historical variance, not a new validated edge. Report accordingly.
"""
import sys
import os
import numpy as np
import pandas as pd
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import load_1m
from round19_random_entry import causal_atr15_lookup
from round23_multi_trade_v2 import generate_and_resolve_multi, daily_pnl_series
from round25_risk_of_ruin import (
    build_daily_pnl_pool, block_bootstrap_path,
    CURRENT_BALANCE, HWM, TRAILING_DD_AMOUNT, DAILY_LOSS_LIMIT, TRAILING_FLOOR,
    REMAINING_BUFFER, PROFIT_TARGET_GAP, N_SEEDS_POOL, BLOCK_SIZE, SYMBOL,
)

REFERENCE_RISK = 600.0          # risk level the R-multiple pool is derived from
N_MC_PATHS = 8000
MC_SEED = 20260920

TODAY = date(2026, 9, 20)
DEADLINE = date(2026, 12, 10)
TRADING_DAYS_REMAINING = round((DEADLINE - TODAY).days * 5 / 7)  # recomputed, not reused from Round 25

RISK_FLOOR = 75.0     # established safe minimum throughout the campaign
RISK_CEIL = 2500.0    # Round 25 showed beyond this is strictly worse on both axes


def build_r_multiple_pool(df1m, atr15, symbol, reference_risk=REFERENCE_RISK, n_seeds=N_SEEDS_POOL):
    pool, n_trades = build_daily_pnl_pool(df1m, atr15, symbol, int(reference_risk), n_seeds=n_seeds)
    r_pool = [s / reference_risk for s in pool]
    return r_pool, n_trades


# --- sizing rules: fn(equity, path_high_water_mark, day_index) -> risk_dollars ---

def make_fixed_fraction_rule(frac):
    def rule(equity, path_hwm, day_idx):
        buffer_now = max(equity - TRAILING_FLOOR, 0.0)
        return float(np.clip(frac * buffer_now, RISK_FLOOR, RISK_CEIL))
    return rule


def make_asymmetric_fraction_rule(frac_down, frac_up):
    """Smaller fraction while below the starting balance (protect harder on the way
    down), larger fraction once above it (grow using the market's money)."""
    def rule(equity, path_hwm, day_idx):
        buffer_now = max(equity - TRAILING_FLOOR, 0.0)
        frac = frac_up if equity >= CURRENT_BALANCE else frac_down
        return float(np.clip(frac * buffer_now, RISK_FLOOR, RISK_CEIL))
    return rule


def make_step_ladder_rule(base=150.0, step=150.0, step_up_gain=1000.0, step_down_giveback=500.0, n_levels=8):
    """Discrete: start at `base`. Step up one level for every step_up_gain of net
    profit from the account's starting balance reached along this path. Step down
    one level if equity gives back step_down_giveback from the path's own running
    high-water-mark. Levels are bounded to [0, n_levels]."""
    def rule(equity, path_hwm, day_idx):
        net_gain = equity - CURRENT_BALANCE
        level_from_gain = int(max(net_gain, 0.0) // step_up_gain) if net_gain > 0 else 0
        giveback = max(path_hwm - equity, 0.0)
        level_penalty = int(giveback // step_down_giveback)
        level = int(np.clip(level_from_gain - level_penalty, 0, n_levels))
        risk = base + level * step
        return float(np.clip(risk, RISK_FLOOR, RISK_CEIL))
    return rule


def simulate_dynamic(r_pool, rule, n_days=TRADING_DAYS_REMAINING, n_paths=N_MC_PATHS,
                      block_size=BLOCK_SIZE, mc_seed=MC_SEED):
    rng = np.random.default_rng(mc_seed)
    ruined = np.zeros(n_paths, dtype=bool)
    success = np.zeros(n_paths, dtype=bool)
    final_balance = np.zeros(n_paths)
    ruin_day = np.full(n_paths, -1)
    median_risk_used = np.zeros(n_paths)

    for p in range(n_paths):
        r_path = block_bootstrap_path(r_pool, n_days, block_size, rng)
        equity = CURRENT_BALANCE
        path_hwm = CURRENT_BALANCE
        risks_used = np.empty(n_days)
        ruined_here = False
        days_elapsed = n_days
        for d in range(n_days):
            risk_d = rule(equity, path_hwm, d)
            risks_used[d] = risk_d
            day_pnl = r_path[d] * risk_d
            equity += day_pnl
            path_hwm = max(path_hwm, equity)

            if equity <= TRAILING_FLOOR or day_pnl <= -DAILY_LOSS_LIMIT:
                ruined[p] = True
                ruin_day[p] = d
                final_balance[p] = equity
                ruined_here = True
                days_elapsed = d + 1
                break
        if not ruined_here:
            final_balance[p] = equity
            success[p] = (equity - CURRENT_BALANCE) >= PROFIT_TARGET_GAP
        median_risk_used[p] = np.median(risks_used[:days_elapsed])

    survived = ~ruined
    result = dict(
        n_paths=n_paths,
        p_ruin=float(ruined.mean()),
        p_success=float(success.mean()),
        p_survived_no_target=float((survived & ~success).mean()),
        median_final=float(np.median(final_balance)),
        p10_final=float(np.percentile(final_balance, 10)),
        p90_final=float(np.percentile(final_balance, 90)),
        median_ruin_day=float(np.median(ruin_day[ruined])) if ruined.any() else None,
        median_risk_used=float(np.median(median_risk_used)),
    )
    return result


if __name__ == "__main__":
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "MNQ_CONTINUOUS.txt")
    print(f"Loading {SYMBOL} from {data_path} ...", flush=True)
    df1m = load_1m(data_path)
    atr15 = causal_atr15_lookup(df1m)
    print(f"Account: balance=${CURRENT_BALANCE:,.2f} HWM=${HWM:,.2f} "
          f"trailing_floor=${TRAILING_FLOOR:,.2f} buffer=${REMAINING_BUFFER:,.2f} "
          f"DLL=${DAILY_LOSS_LIMIT:,.2f} profit_target_gap=${PROFIT_TARGET_GAP:,.2f}", flush=True)
    print(f"Recomputed trading days remaining ({TODAY} -> {DEADLINE}): {TRADING_DAYS_REMAINING}"
          f" (Round 25 used 57)", flush=True)

    print(f"\nBuilding R-multiple pool from ${REFERENCE_RISK:.0f}-risk historical trades "
          f"({N_SEEDS_POOL} seeds) ...", flush=True)
    r_pool, n_trades = build_r_multiple_pool(df1m, atr15, SYMBOL)
    pool_days = sum(len(s) for s in r_pool)
    print(f"  pool: {len(r_pool)} seeds, {n_trades} total trades, {pool_days} total trading-day observations",
          flush=True)

    rules = {}
    for frac in (0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20):
        rules[f"fixed_frac_{frac:.2f}"] = make_fixed_fraction_rule(frac)
    for fd, fu in ((0.02, 0.06), (0.02, 0.10), (0.04, 0.12)):
        rules[f"asym_down{fd:.2f}_up{fu:.2f}"] = make_asymmetric_fraction_rule(fd, fu)
    for base, step in ((150, 150), (75, 225), (150, 300)):
        rules[f"ladder_base{base}_step{step}"] = make_step_ladder_rule(base=base, step=step)

    rows = []
    for name, rule in rules.items():
        res = simulate_dynamic(r_pool, rule)
        res["rule"] = name
        rows.append(res)
        print(f"  [{name}] P(ruin)={res['p_ruin']:.1%} P(success)={res['p_success']:.1%} "
              f"median_final=${res['median_final']:,.2f} "
              f"[p10=${res['p10_final']:,.2f} p90=${res['p90_final']:,.2f}] "
              f"median_risk_used=${res['median_risk_used']:,.2f}", flush=True)

    df = pd.DataFrame(rows).sort_values("p_success", ascending=False)
    print("\n\n=== FULL DYNAMIC-SIZING RESULTS (sorted by P(success) desc) ===")
    print(df.to_string(index=False))
    out_dir = os.path.dirname(__file__)
    df.to_csv(os.path.join(out_dir, "round26_dynamic_sizing_grid.csv"), index=False)

    best = df.iloc[0]
    print(f"\nBest by P(success): rule={best['rule']} P(success)={best['p_success']:.1%} "
          f"P(ruin)={best['p_ruin']:.1%}")
    print("Round 25 best fixed-risk: rule=fixed_$1900 P(success)=24.4% P(ruin)=66.3%")

    print("\nDONE.", flush=True)
