"""
INDEPENDENT AUDIT (not part of the round-numbered research sequence).

Purpose: re-derive, from as close to raw data as practical, whether the MNQ
"random_entry_atr_trail" strategy (random time-of-day entry, random direction,
ATR-based trailing stop that only ever tightens, no fixed profit target) has a
real statistical edge -- calling the REAL repo functions (round19_random_entry /
round11_fvg_bias), not a reimplementation. Also runs the identical mechanism on
MGC (Gold) as a supplementary cross-check, since the user asked about both
instruments, even though MGC's actually-deployed/recommended strategy in this
repo is a different one (round30b support/resistance bounce), not this one.

Run from: futures/engine  (relative data paths assume this cwd).
"""
import os
import sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from round11_fvg_bias import load_1m, POINT_VALUE, TICK_SIZE, COMMISSION_RT
from round19_random_entry import (
    causal_atr15_lookup, generate_random_entries, build_stop_signals,
    resolve_trailing, TRAIL_ATR_MULT,
)

RISK_DOLLAR = 245  # "currently-recommended" MNQ sizing (Round 34 / round36 / round37: MNQ_RISK=245)
N_SEEDS = 15        # matches build_mnq_daily's own n_seeds=15 convention (>= the requested 10+)


def audit_symbol(symbol, path, risk_dollar, n_seeds):
    print(f"\n{'='*78}\n{symbol}: loading real 1m data from {path}", flush=True)
    df1m = load_1m(path)
    span_start, span_end = df1m.index.min(), df1m.index.max()
    n_bars = len(df1m)
    n_dup_ts = df1m.index.duplicated().sum()  # load_1m already dropped dups; sanity re-check is 0 by construction
    print(f"{symbol}: {n_bars:,} 1m bars, {span_start} -> {span_end}, "
          f"duplicated index entries after load_1m dedup = {n_dup_ts}", flush=True)

    atr15 = causal_atr15_lookup(df1m)
    print(f"{symbol}: causal 15m ATR(14) series has {len(atr15):,} values, "
          f"{atr15.index.min()} -> {atr15.index.max()}", flush=True)

    all_trades = []
    per_seed_summaries = []
    per_seed_raw_entries = []
    for seed in range(n_seeds):
        raw = generate_random_entries(df1m, seed)  # real function: 1 random (bar,dir)/day
        sig = build_stop_signals(raw, atr15)        # real function: attach ATR-derived initial stop
        trades = resolve_trailing(sig, df1m, symbol, risk_dollar, TRAIL_ATR_MULT)  # real function: trail-only exit
        trades["seed"] = seed
        all_trades.append(trades)
        per_seed_raw_entries.append(len(raw))
        if len(trades) > 0:
            per_seed_summaries.append(dict(
                seed=seed, n=len(trades), exp=trades["pnl"].mean(), total=trades["pnl"].sum(),
                winrate=(trades["pnl"] > 0).mean(),
            ))

    combo = pd.concat(all_trades, ignore_index=True)
    combo["date"] = pd.to_datetime(combo["ts"]).dt.date

    # ---- sanity check trade count / date range vs raw data span --------------------
    n_calendar_days_in_span = (span_end.date() - span_start.date()).days + 1
    raw_entries_total = sum(per_seed_raw_entries)
    print(f"\n{symbol} SANITY CHECK:")
    print(f"  raw random entries generated across {n_seeds} seeds: {raw_entries_total:,} "
          f"(avg {raw_entries_total/n_seeds:,.0f}/seed; one entry per RTH day with >=30 1m bars, per seed)")
    print(f"  resolved trades (after requiring a valid causal ATR stop): {len(combo):,} "
          f"(avg {len(combo)/n_seeds:,.0f}/seed)")
    print(f"  calendar days spanned by raw data: {n_calendar_days_in_span:,} "
          f"({span_start.date()} -> {span_end.date()})")
    print(f"  trade dates span: {combo['date'].min()} -> {combo['date'].max()}")
    dup_check = combo.duplicated(subset=["seed", "ts", "direction"]).sum()
    print(f"  exact-duplicate (seed,ts,direction) rows: {dup_check}")
    # per-seed entries should be <= number of unique trading days in the span (1/day/seed cap)
    max_per_seed = max(per_seed_raw_entries)
    print(f"  max entries in any single seed: {max_per_seed} vs distinct calendar dates present in 1m data: "
          f"{pd.Series(df1m.index.date).nunique():,}")

    # ---- core stats on pooled trades ------------------------------------------------
    pnl = combo["pnl"].values
    n = len(pnl)
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    winrate = len(wins) / n
    avg_win = wins.mean() if len(wins) else float("nan")
    avg_loss = losses.mean() if len(losses) else float("nan")
    expectancy = pnl.mean()
    t_stat, p_val = stats.ttest_1samp(pnl, 0.0)

    print(f"\n{symbol} POOLED RESULTS ({n_seeds} seeds, risk=${risk_dollar}, trail_mult={TRAIL_ATR_MULT}x ATR):")
    print(f"  total trades: {n:,}")
    print(f"  win rate: {winrate:.2%}  (n_win={len(wins):,}, n_loss={len(losses):,})")
    print(f"  avg win: ${avg_win:,.2f}   avg loss: ${avg_loss:,.2f}   win/loss $ ratio: {avg_win/abs(avg_loss):.3f}")
    print(f"  expectancy/trade: ${expectancy:,.2f}   total P&L: ${pnl.sum():,.2f}")
    print(f"  t-stat (H0: mean pnl == 0): t={t_stat:.3f}, p={p_val:.4g}  (per-trade pooled test; "
          f"NOTE: trades across seeds overlap in time/share the same price path, so this overstates "
          f"independence -- see seed-level test below for the more defensible version)")

    # seed-level test: one independent draw per seed (15 iid-ish samples of mean expectancy)
    seed_exps = np.array([s["exp"] for s in per_seed_summaries])
    t_seed, p_seed = stats.ttest_1samp(seed_exps, 0.0)
    print(f"  seed-level t-test on {len(seed_exps)} per-seed mean expectancies: "
          f"mean=${seed_exps.mean():.2f} std=${seed_exps.std(ddof=1):.2f} t={t_seed:.3f} p={p_seed:.4g} "
          f"(positive seeds: {(seed_exps>0).sum()}/{len(seed_exps)})")

    # ---- LONG vs SHORT split: the core "is this really drift, not a trailing-stop edge" check ----
    long_t = combo[combo["direction"] == 1]["pnl"]
    short_t = combo[combo["direction"] == -1]["pnl"]
    print(f"\n{symbol} LONG vs SHORT split:")
    for label, series in [("LONG", long_t), ("SHORT", short_t)]:
        if len(series) == 0:
            print(f"  {label}: no trades")
            continue
        ts, ps = stats.ttest_1samp(series.values, 0.0)
        print(f"  {label}: n={len(series):,} win%={ (series>0).mean():.2%} "
              f"exp=${series.mean():,.2f} total=${series.sum():,.2f} t={ts:.3f} p={ps:.4g}")

    long_exp = long_t.mean() if len(long_t) else float("nan")
    short_exp = short_t.mean() if len(short_t) else float("nan")
    long_total = long_t.sum() if len(long_t) else 0.0
    short_total = short_t.sum() if len(short_t) else 0.0

    # crude underlying-drift proxy: buy-and-hold the whole span on 1m closes
    px_start = df1m["close"].iloc[0]
    px_end = df1m["close"].iloc[-1]
    pv = POINT_VALUE[symbol]
    drift_pts = px_end - px_start
    drift_dollars_per_contract = drift_pts * pv
    n_days_est = pd.Series(df1m.index.date).nunique()
    print(f"\n{symbol} UNDERLYING DRIFT CONTEXT:")
    print(f"  price at span start: {px_start:.2f}  price at span end: {px_end:.2f}  "
          f"raw drift: {drift_pts:+.2f} pts = {drift_pts/px_start:+.2%} over the span "
          f"({n_days_est:,} trading days)")
    print(f"  buy-and-hold 1 contract for the whole span would have made ${drift_dollars_per_contract:,.2f} "
          f"(before costs) -- {'UP' if drift_pts>0 else 'DOWN'}trend")

    return dict(symbol=symbol, n=n, winrate=winrate, avg_win=avg_win, avg_loss=avg_loss,
                expectancy=expectancy, t_stat=t_stat, p_val=p_val, t_seed=t_seed, p_seed=p_seed,
                long_exp=long_exp, short_exp=short_exp, long_n=len(long_t), short_n=len(short_t),
                long_total=long_total, short_total=short_total, drift_dollars=drift_dollars_per_contract,
                combo=combo)


if __name__ == "__main__":
    mnq_path = os.path.join("..", "data", "MNQ_CONTINUOUS.txt")
    mgc_path = os.path.join("..", "data", "MGC_CONTINUOUS.txt")

    mnq_res = audit_symbol("MNQ", mnq_path, RISK_DOLLAR, N_SEEDS)
    # supplementary: same exact random-entry+trail mechanism on Gold, at Gold's own
    # currently-recommended sizing, for the user's "both Nasdaq and Gold" ask -- NOTE
    # this is NOT MGC's actually-deployed strategy in this repo (that's round30b's
    # support/resistance bounce); this only checks whether THIS mechanism (random
    # entry, ATR trail) also shows a drift-driven long-bias pattern on gold.
    mgc_res = audit_symbol("MGC", mgc_path, 650, N_SEEDS)

    print(f"\n{'='*78}\nSUMMARY\n{'='*78}")
    for res in (mnq_res, mgc_res):
        s = res["symbol"]
        long_share = res["long_total"] / (res["long_total"] + res["short_total"]) if (res["long_total"]+res["short_total"]) != 0 else float("nan")
        print(f"{s}: n={res['n']:,} exp=${res['expectancy']:.2f} t={res['t_stat']:.2f} p={res['p_val']:.4g} | "
              f"seed-t={res['t_seed']:.2f} seed-p={res['p_seed']:.4g} | "
              f"long_exp=${res['long_exp']:.2f}(n={res['long_n']}) short_exp=${res['short_exp']:.2f}(n={res['short_n']}) | "
              f"long total ${res['long_total']:,.0f} vs short total ${res['short_total']:,.0f} | "
              f"buy&hold drift ${res['drift_dollars']:,.0f}")

    print("\nDONE.", flush=True)
