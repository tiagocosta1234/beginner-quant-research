"""
Round 24: two extensions of the ONE validated finding (Round 19-23's random-entry +
ATR-trailing-stop exit on MNQ, $75 risk/trade, 1 trade/day, $17.27/day fully verified).

Part 1: Round 19 deliberately fixed the exit's own parameters (1.0x ATR(14) initial
stop, 1.5x ATR trailing multiplier) rather than grid-searching them, "a style-comparison
round, not another per-fold optimization" -- appropriate caution on first discovery.
Five rounds of scrutiny later (19-23) the effect is confirmed real, so it is now
legitimate, standard practice to grid-search its own parameters the same way R:R was
grid-searched in nearly every earlier round -- train-only selection per fold, applied
unchanged OOS, exactly this campaign's standing convention.

Part 2: Round 19 tested MGC with the same blanket all-session random-entry approach
that worked for MNQ's RTH-only trading and found no replication. But MGC trades near-24h
while MNQ is RTH-only -- a blanket all-session test on MGC is not a clean apples-to-apples
retest of what worked for MNQ. Tests whether restricting entries to MGC's own most-active
hours (confirmed from the raw data below, not assumed) changes the result.

Both parts reuse Round 19's exact entry generator, causal ATR lookup, and cost model
(import, not reimplement), and Round 23's validated vectorized trailing-stop resolver
(_resolve_one_vectorized) for tractable grid-search runtime -- the scalar resolve_trailing
takes ~51s per single seed/config (per Round 23's own finding), making a stop_mult x
trail_mult grid infeasible with it. The vectorized resolver is re-validated here against
Round 19's own scalar resolve_trailing at the ORIGINAL (1.0, 1.5) parameters before being
trusted for the grid, not assumed correct because Round 23 validated it for a different
purpose.
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, POINT_VALUE, TICK_SIZE, COMMISSION_RT, BUFFER, FOLDS, fold_stats, tail_concentration,
)
from round19_random_entry import (
    causal_atr15_lookup, generate_random_entries, resolve_trailing, SEEDS,
    STOP_ATR_MULT as BASELINE_STOP_MULT, TRAIL_ATR_MULT as BASELINE_TRAIL_MULT,
)
from round23_multi_trade_v2 import _resolve_one_vectorized, SIZING_GRID, SAFETY_MARGIN_TARGET, SEEDS_WIDE

STOP_MULT_GRID = (0.75, 1.0, 1.25, 1.5)
TRAIL_MULT_GRID = (1.0, 1.5, 2.0, 2.5)
RISK_MAIN = 400
MAX_HOLD_BARS = 390


# ---------------------------------------------------------------------------
# Shared: parametrized signal construction + vectorized resolution
# ---------------------------------------------------------------------------

def build_signals(raw_entries, atr_series, stop_atr_mult):
    """Attach an ATR-derived stop at an arbitrary multiplier (round19's
    build_stop_signals hardcodes STOP_ATR_MULT; this is the same logic,
    parametrized, so Part 1 can vary it)."""
    atr_ts = atr_series.index.values
    pos = np.searchsorted(atr_ts, raw_entries["ts"].values, side="right") - 1
    valid = pos >= 0
    s = raw_entries[valid].copy()
    pos = pos[valid]
    s["atr"] = atr_series.values[pos]
    s = s[s["atr"] > 0].copy()
    stop_dist = stop_atr_mult * s["atr"]
    s["stop"] = np.where(s["direction"] == 1, s["entry"] - stop_dist, s["entry"] + stop_dist)
    return s[["ts", "direction", "entry", "stop"]].reset_index(drop=True)


def resolve_vectorized(sig_df, df1m, symbol, risk_dollar, trail_mult):
    """Vectorized resolution matching round19_random_entry.resolve_trailing's exact
    semantics (entry priced at the signal's own close; stop-check loop starts at the
    bar strictly AFTER entry, via searchsorted(..., side='right'), same convention
    round19's resolve_trailing and round23's generate_and_resolve_multi both use)."""
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip = 2 * tick * pv
    ts = df1m.index.values
    hi = df1m["high"].values
    lo = df1m["low"].values
    cl = df1m["close"].values
    n = len(df1m)
    rows = []
    for r in sig_df.itertuples(index=False):
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        init_dist = abs(r.entry - r.stop)
        if init_dist <= 0:
            continue
        contracts = max(1, int(risk_dollar // (init_dist * pv)))
        commission = COMMISSION_RT * contracts
        exit_pos, exit_px, pnl, outcome = _resolve_one_vectorized(
            pos, r.direction, r.entry, r.stop, hi, lo, cl, n, pv, trail_mult,
            contracts, commission, slip, max_hold_bars=MAX_HOLD_BARS,
        )
        rows.append((r.ts, symbol, r.direction, risk_dollar, contracts, pnl, outcome))
    return pd.DataFrame(rows, columns=["ts", "symbol", "direction", "risk", "contracts", "pnl", "outcome"])


def validate_vectorized_reproduces_round19(df1m, atr15, symbol, seeds=(0, 1, 3)):
    """Gate before trusting resolve_vectorized for the grid: at the ORIGINAL
    (STOP_ATR_MULT, TRAIL_ATR_MULT), it must match round19_random_entry's own scalar
    resolve_trailing exactly (n and total pnl to the cent)."""
    for seed in seeds:
        raw = generate_random_entries(df1m, seed)
        sig_new = build_signals(raw, atr15, BASELINE_STOP_MULT)
        mine = resolve_vectorized(sig_new, df1m, symbol, RISK_MAIN, BASELINE_TRAIL_MULT)

        from round19_random_entry import build_stop_signals
        sig_orig = build_stop_signals(raw, atr15)
        theirs = resolve_trailing(sig_orig, df1m, symbol, RISK_MAIN, BASELINE_TRAIL_MULT)

        if len(mine) != len(theirs):
            raise AssertionError(f"seed={seed}: n mismatch mine={len(mine)} theirs={len(theirs)}")
        if abs(mine["pnl"].sum() - theirs["pnl"].sum()) > 0.01:
            raise AssertionError(
                f"seed={seed}: pnl sum mismatch mine={mine['pnl'].sum():.2f} theirs={theirs['pnl'].sum():.2f}"
            )
    return True


# ---------------------------------------------------------------------------
# Part 1: train-only grid search of (stop_mult, trail_mult) per fold
# ---------------------------------------------------------------------------

def resolve_all_combos(df1m, atr15, symbol, seeds, risk=RISK_MAIN):
    """One resolved trade set per (seed, stop_mult, trail_mult) combo, full dataset.
    Returned dict keyed by (seed, stop_mult, trail_mult) -> trades DataFrame (has 'ts'
    so callers can slice by fold date range for train/test without re-resolving)."""
    out = {}
    raw_by_seed = {seed: generate_random_entries(df1m, seed) for seed in seeds}
    for stop_mult in STOP_MULT_GRID:
        sig_by_seed = {seed: build_signals(raw_by_seed[seed], atr15, stop_mult) for seed in seeds}
        for trail_mult in TRAIL_MULT_GRID:
            for seed in seeds:
                trades = resolve_vectorized(sig_by_seed[seed], df1m, symbol, risk, trail_mult)
                out[(seed, stop_mult, trail_mult)] = trades
    return out


def fold_train_test_grid(all_combos, seeds, train_end, test_end):
    """Train-only selection: pool ts < train_end across all seeds for each combo,
    pick the combo with the highest mean training pnl/trade; return that combo plus
    the resulting per-seed OOS ([train_end, test_end)) trade sets."""
    train_end_ts = pd.Timestamp(train_end)
    test_end_ts = pd.Timestamp(test_end)
    best_combo, best_train_mean, best_train_n = None, -np.inf, 0
    for stop_mult in STOP_MULT_GRID:
        for trail_mult in TRAIL_MULT_GRID:
            pooled_train = pd.concat(
                [all_combos[(s, stop_mult, trail_mult)] for s in seeds], ignore_index=True
            )
            train_slice = pooled_train[pooled_train["ts"] < train_end_ts]
            if len(train_slice) < 20:  # too few training trades to trust a selection
                continue
            m = train_slice["pnl"].mean()
            if m > best_train_mean:
                best_train_mean, best_combo, best_train_n = m, (stop_mult, trail_mult), len(train_slice)
    if best_combo is None:
        return None, {}, None, 0
    stop_mult, trail_mult = best_combo
    oos_by_seed = {}
    for s in seeds:
        t = all_combos[(s, stop_mult, trail_mult)]
        oos_by_seed[s] = t[(t["ts"] >= train_end_ts) & (t["ts"] < test_end_ts)]
    return best_combo, oos_by_seed, best_train_mean, best_train_n


def run_part1(df1m, atr15, symbol, seeds=SEEDS, risk=RISK_MAIN):
    print(f"\n{'='*70}\nRound 24 Part 1: grid-search (stop_mult, trail_mult) on {symbol}", flush=True)
    all_combos = resolve_all_combos(df1m, atr15, symbol, seeds, risk)
    print(f"  resolved {len(all_combos)} (seed,stop_mult,trail_mult) combos over the full dataset", flush=True)

    fold_choices = []
    per_seed_oos_trades = {s: [] for s in seeds}
    for train_end, test_end in FOLDS:
        combo, oos_by_seed, train_mean, train_n = fold_train_test_grid(all_combos, seeds, train_end, test_end)
        fold_choices.append((train_end, test_end, combo, train_mean, train_n))
        print(f"  fold {train_end}->{test_end}: selected stop_mult={combo[0]} trail_mult={combo[1]} "
              f"(train n={train_n}, train mean pnl/trade=${train_mean:.2f})", flush=True)
        for s in seeds:
            per_seed_oos_trades[s].append(oos_by_seed.get(s, pd.DataFrame(columns=["pnl", "ts"])))

    per_seed_combined = {s: pd.concat(per_seed_oos_trades[s], ignore_index=True) for s in seeds}
    exps = [t["pnl"].mean() for t in per_seed_combined.values() if len(t) > 0]
    pooled = pd.concat([t for t in per_seed_combined.values() if len(t) > 0], ignore_index=True)

    # buffer-breach stats, per seed per fold, on the grid-selected OOS trades
    breach_rows = []
    for s in seeds:
        idx = 0
        for train_end, test_end in FOLDS:
            fold_trades = per_seed_oos_trades[s][idx]
            idx += 1
            if len(fold_trades) == 0:
                continue
            st = fold_stats(fold_trades)
            breach_rows.append((s, train_end, test_end, st["maxdd"], st["breach"]))
    n_breach = sum(1 for r in breach_rows if r[4])
    worst = max(breach_rows, key=lambda r: r[3]) if breach_rows else None

    tc10 = tail_concentration(pooled, 10) if len(pooled) else None
    tc20 = tail_concentration(pooled, 20) if len(pooled) else None

    print(f"\n  GRID-SELECTED (train-only, per fold) OOS result on {symbol}, risk=${risk}:", flush=True)
    print(f"    n={len(pooled)} mean_exp/trade=${np.mean(exps):.2f} (across {len(exps)} seeds) "
          f"total=${pooled['pnl'].sum():.2f}", flush=True)
    print(f"    tail10={tc10} tail20={tc20}", flush=True)
    print(f"    seed-fold windows breaching buffer: {n_breach}/{len(breach_rows)}, "
          f"worst maxdd=${worst[3]:.2f} (seed={worst[0]}, {worst[1]}->{worst[2]})" if worst else "    no folds", flush=True)

    # Baseline, computed through this SAME harness (not just quoting Round 19's numbers)
    # for a clean apples-to-apples comparison within one resolver implementation.
    base_per_seed = {s: all_combos[(s, BASELINE_STOP_MULT, BASELINE_TRAIL_MULT)] for s in seeds}
    base_exps = [t["pnl"].mean() for t in base_per_seed.values() if len(t) > 0]
    base_pooled = pd.concat([t for t in base_per_seed.values() if len(t) > 0], ignore_index=True)
    base_breach_rows = []
    for s in seeds:
        t = base_per_seed[s]
        for train_end, test_end in FOLDS:
            fold_t = t[(t["ts"] >= pd.Timestamp(train_end)) & (t["ts"] < pd.Timestamp(test_end))]
            if len(fold_t) == 0:
                continue
            st = fold_stats(fold_t)
            base_breach_rows.append((s, train_end, test_end, st["maxdd"], st["breach"]))
    base_n_breach = sum(1 for r in base_breach_rows if r[4])
    base_worst = max(base_breach_rows, key=lambda r: r[3]) if base_breach_rows else None

    print(f"\n  BASELINE (stop_mult={BASELINE_STOP_MULT}, trail_mult={BASELINE_TRAIL_MULT} fixed, no grid "
          f"search, same harness) on {symbol}, risk=${risk} -- this is the cross-check against Round 19's "
          f"published numbers:", flush=True)
    print(f"    n={len(base_pooled)} mean_exp/trade=${np.mean(base_exps):.2f} (across {len(base_exps)} seeds) "
          f"total=${base_pooled['pnl'].sum():.2f}", flush=True)
    print(f"    seed-fold windows breaching buffer: {base_n_breach}/{len(base_breach_rows)}, "
          f"worst maxdd=${base_worst[3]:.2f}" if base_worst else "    no folds", flush=True)

    # dominant fold choice, for the follow-up buffer-safe sizing search
    from collections import Counter
    choice_counts = Counter(c[2] for c in fold_choices if c[2] is not None)
    dominant = choice_counts.most_common(1)[0] if choice_counts else (None, 0)
    print(f"\n  fold-choice distribution: {dict(choice_counts)}", flush=True)
    print(f"  dominant choice: {dominant[0]} (won {dominant[1]}/{len(fold_choices)} folds)", flush=True)

    return dict(
        pooled=pooled, mean_exp=float(np.mean(exps)) if exps else None,
        tail10=tc10, tail20=tc20, n_breach=n_breach, n_folds=len(breach_rows),
        worst_maxdd=worst[3] if worst else None,
        baseline_mean_exp=float(np.mean(base_exps)) if base_exps else None,
        baseline_n_breach=base_n_breach, baseline_n_folds=len(base_breach_rows),
        baseline_worst_maxdd=base_worst[3] if base_worst else None,
        fold_choices=fold_choices, dominant_combo=dominant[0], dominant_count=dominant[1],
    )


def buffer_safe_search(df1m, atr15, symbol, stop_mult, trail_mult, seeds=SEEDS_WIDE):
    """Same 70%-of-real-buffer convention and SIZING_GRID as Round 20/22/23, reused
    directly (imported, not re-derived), applied to a fixed (stop_mult, trail_mult)
    pair at 1 trade/day -- Round 23 already closed the multi-trade/day question
    negatively, not reopened here."""
    rows = []
    raw_by_seed = {s: generate_random_entries(df1m, s) for s in seeds}
    for risk in SIZING_GRID:
        per_trade_exps, worst_dd = [], 0.0
        all_trades = []
        for s in seeds:
            sig = build_signals(raw_by_seed[s], atr15, stop_mult)
            trades = resolve_vectorized(sig, df1m, symbol, risk, trail_mult)
            if len(trades) == 0:
                continue
            all_trades.append(trades)
            per_trade_exps.append(trades["pnl"].mean())
            for train_end, test_end in FOLDS:
                fold_t = trades[(trades["ts"] >= pd.Timestamp(train_end)) & (trades["ts"] < pd.Timestamp(test_end))]
                if len(fold_t) == 0:
                    continue
                st = fold_stats(fold_t)
                worst_dd = max(worst_dd, st["maxdd"])
        if not all_trades:
            continue
        pooled = pd.concat(all_trades, ignore_index=True)
        exp_trade = float(np.mean(per_trade_exps))
        within_target = worst_dd <= SAFETY_MARGIN_TARGET
        within_full_buffer = worst_dd <= BUFFER
        rows.append(dict(stop_mult=stop_mult, trail_mult=trail_mult, risk=risk, n_seeds=len(seeds),
                          n=len(pooled), exp_trade=exp_trade, worst_maxdd=worst_dd,
                          within_70pct_target=within_target, within_full_buffer=within_full_buffer))
        print(f"  [sizing,{len(seeds)}seeds] stop_mult={stop_mult} trail_mult={trail_mult} risk=${risk}: "
              f"exp/trade=${exp_trade:.2f} worst_maxdd=${worst_dd:.2f} "
              f"within_70pct={within_target} within_full_buffer={within_full_buffer}", flush=True)
        if within_target:
            break
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Part 2: session-restricted MGC entries
# ---------------------------------------------------------------------------

def generate_random_entries_session(df1m, seed, hour_start, hour_end):
    """Same per-day scalar RNG draw shape as round19_random_entry.generate_random_entries
    (one rng.integers + one rng.random per day, day-iteration order) -- differs only in
    restricting the eligible-bar pool to [hour_start, hour_end) before the draw. Hours
    are in the data's native timestamp convention (confirmed US/Eastern via MNQ's RTH
    clustering -- see module-level data audit in this round's writeup)."""
    rng = np.random.default_rng(seed)
    dates = pd.Series(df1m.index.date, index=df1m.index)
    hour_of_day = pd.Series(df1m.index.hour, index=df1m.index)
    rows = []
    for day, day_idx in df1m.groupby(dates).groups.items():
        h = hour_of_day.loc[day_idx]
        eligible = day_idx[(h >= hour_start) & (h < hour_end)]
        if len(eligible) < 5:
            continue
        chosen_ts = eligible[rng.integers(0, len(eligible))]
        direction = 1 if rng.random() < 0.5 else -1
        entry_px = df1m.loc[chosen_ts, "close"]
        rows.append((chosen_ts, direction, entry_px))
    sig = pd.DataFrame(rows, columns=["ts", "direction", "entry"]).sort_values("ts").reset_index(drop=True)
    return sig


SESSION_WINDOWS = {
    "RTH_equivalent_09_16": (9, 16),   # exactly MNQ's own RTH window, most direct retest
    "peak_activity_12_15": (12, 15),   # MGC's single highest-volume window in the raw data
}


def run_part2(df1m_mgc, atr15_mgc, seeds=SEEDS, risk=RISK_MAIN):
    print(f"\n{'='*70}\nRound 24 Part 2: session-restricted MGC entries", flush=True)
    results = {}
    for label, (h0, h1) in SESSION_WINDOWS.items():
        for stop_mult, trail_mult, tag in [
            (BASELINE_STOP_MULT, BASELINE_TRAIL_MULT, "baseline_params"),
        ]:
            per_seed_trades = []
            for s in seeds:
                raw = generate_random_entries_session(df1m_mgc, s, h0, h1)
                sig = build_signals(raw, atr15_mgc, stop_mult)
                trades = resolve_vectorized(sig, df1m_mgc, "MGC", risk, trail_mult)
                per_seed_trades.append(trades)
            exps = [t["pnl"].mean() for t in per_seed_trades if len(t) > 0]
            pooled = pd.concat([t for t in per_seed_trades if len(t) > 0], ignore_index=True)
            n_pos = sum(1 for t in per_seed_trades if len(t) > 0 and t["pnl"].mean() > 0)
            breach_rows = []
            for s, t in zip(seeds, per_seed_trades):
                for train_end, test_end in FOLDS:
                    fold_t = t[(t["ts"] >= pd.Timestamp(train_end)) & (t["ts"] < pd.Timestamp(test_end))]
                    if len(fold_t) == 0:
                        continue
                    st = fold_stats(fold_t)
                    breach_rows.append((s, train_end, test_end, st["maxdd"], st["breach"]))
            n_breach = sum(1 for r in breach_rows if r[4])
            tc10 = tail_concentration(pooled, 10) if len(pooled) else None
            print(f"  window={label} ({h0}:00-{h1}:00) params={tag} risk=${risk}: n={len(pooled)} "
                  f"mean_exp/trade=${np.mean(exps):.2f} positive_seeds={n_pos}/{len(exps)} "
                  f"folds_breaching={n_breach}/{len(breach_rows)} tail10={tc10}", flush=True)
            results[(label, tag)] = dict(n=len(pooled), mean_exp=float(np.mean(exps)) if exps else None,
                                          n_pos=n_pos, n_seeds=len(exps), n_breach=n_breach,
                                          n_folds=len(breach_rows), tail10=tc10)
    return results


if __name__ == "__main__":
    mnq_path = os.path.join(os.path.dirname(__file__), "..", "data", "MNQ_CONTINUOUS.txt")
    mgc_path = os.path.join(os.path.dirname(__file__), "..", "data", "MGC_CONTINUOUS.txt")

    print("Loading MNQ...", flush=True)
    df_mnq = load_1m(mnq_path)
    atr_mnq = causal_atr15_lookup(df_mnq)
    print(f"MNQ: {len(df_mnq)} bars {df_mnq.index.min()} -> {df_mnq.index.max()}", flush=True)

    print("\nValidating vectorized resolver reproduces Round 19's scalar resolve_trailing "
          "at the ORIGINAL (1.0, 1.5) parameters...", flush=True)
    validate_vectorized_reproduces_round19(df_mnq, atr_mnq, "MNQ")
    print("  PASS: exact match (n and total pnl to the cent) across seeds [0,1,3]", flush=True)

    part1 = run_part1(df_mnq, atr_mnq, "MNQ")

    print(f"\n{'='*70}\nBuffer-safe sizing search on the DOMINANT grid choice vs. baseline", flush=True)
    dom = part1["dominant_combo"]
    if dom is not None and dom != (BASELINE_STOP_MULT, BASELINE_TRAIL_MULT):
        print(f"\n--- dominant grid choice: stop_mult={dom[0]} trail_mult={dom[1]} ---", flush=True)
        sizing_dom = buffer_safe_search(df_mnq, atr_mnq, "MNQ", dom[0], dom[1])
    else:
        print("\n  dominant choice equals baseline or is undefined -- skipping a redundant sizing search "
              "(baseline sizing search below covers this case).", flush=True)
        sizing_dom = pd.DataFrame()
    print(f"\n--- baseline: stop_mult={BASELINE_STOP_MULT} trail_mult={BASELINE_TRAIL_MULT} "
          f"(re-derivation of Round 23's own $75/$17.27 result, as a sanity check) ---", flush=True)
    sizing_base = buffer_safe_search(df_mnq, atr_mnq, "MNQ", BASELINE_STOP_MULT, BASELINE_TRAIL_MULT)

    sizing_all = pd.concat([sizing_dom, sizing_base], ignore_index=True) if len(sizing_dom) else sizing_base
    sizing_all.to_csv(os.path.join(os.path.dirname(__file__), "round24_sizing_search.csv"), index=False)

    print("\nLoading MGC...", flush=True)
    df_mgc = load_1m(mgc_path)
    atr_mgc = causal_atr15_lookup(df_mgc)
    print(f"MGC: {len(df_mgc)} bars {df_mgc.index.min()} -> {df_mgc.index.max()}", flush=True)
    part2 = run_part2(df_mgc, atr_mgc)

    print("\n\nDONE.", flush=True)
