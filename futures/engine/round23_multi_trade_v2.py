"""
Round 23: re-test of Round 22's "does relaxing 1-trade/day multiply the edge"
question, fixing a methodological gap Round 22 flagged in its own writeup:
its multi-entry generator drew candidates via a vectorized batch call
(rng.choice(..., size=n) + rng.integers(0, 2, size=n)) instead of Round 19's
per-day SCALAR draws (rng.integers(0, len(day_idx)) then rng.random(), once
per day) -- same seed *value* therefore consumed the RNG stream differently
and did not reproduce Round 19/20's original numbers even at trades_per_day=1.

Fix: generate_candidates() below draws exactly `trades_per_day` scalar
(ts, direction) pairs per day, in the same call shape and order Round 19's
generate_random_entries() used. At trades_per_day=1 this is BYTE-IDENTICAL
RNG consumption to Round 19's original function (one rng.integers + one
rng.random per day, in day-iteration order) -- verified explicitly below by
cross-checking against round19_random_entry.generate_random_entries() before
trusting anything built on top of it, per the task directive.

Per-trade resolution (ATR-trailing stop, no fixed target) reuses Round 19's
resolve_trailing() logic unchanged (imported, not reimplemented) via a
single-trade extraction that matches it line-for-line -- this part of Round
22's harness was already a faithful extraction, not a reimplementation with
different logic, so it's kept as-is rather than rewritten a third time.

Widened seed count: the main trades-per-day x risk grid still uses 8 seeds
(SEEDS, matching Round 19/20/22 for direct comparability), but the
buffer-safety (worst-case-over-seeds) search uses 25 independent seeds --
8 was flagged as thin for an extreme-value statistic specifically.
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, POINT_VALUE, TICK_SIZE, COMMISSION_RT, BUFFER, FOLDS, tail_concentration,
)
from round19_random_entry import (
    causal_atr15_lookup, SEEDS, STOP_ATR_MULT, TRAIL_ATR_MULT,
    generate_random_entries, build_stop_signals, resolve_trailing,
)

MIN_GAP_BARS = 5
MAX_HOLD_BARS = 390
RISK_LEVELS = (400, 600)
TRADES_PER_DAY_GRID = (1, 2, 3, 4, 5, 6, 8)
SEEDS_WIDE = list(range(25))  # widened for the buffer-safety worst-case search specifically


def _resolve_one(entry_pos, direction, entry_px, stop_px, hi, lo, cl, n, pv, trail_mult,
                  contracts, commission, slip_dollars_rt, max_hold_bars=MAX_HOLD_BARS):
    """Line-for-line match to round19_random_entry.resolve_trailing's per-trade inner
    loop (verified by inspection against that function) -- extracted so a multi-entry
    generator can learn each trade's exit position immediately, to gate the next
    same-day candidate causally. Not a reimplementation with different logic."""
    init_dist = abs(entry_px - stop_px)
    trail_dist = trail_mult * init_dist
    end_pos = min(entry_pos + max_hold_bars, n - 1)
    cur_stop = entry_px - trail_dist if direction == 1 else entry_px + trail_dist
    best = entry_px
    exit_px = None
    exit_pos = end_pos
    outcome = "timeout"
    for i in range(entry_pos, end_pos + 1):
        bar_hi, bar_lo = hi[i], lo[i]
        if direction == 1:
            if bar_lo <= cur_stop:
                exit_px = cur_stop
                exit_pos = i
                outcome = "trail_stop"
                break
            best = max(best, bar_hi)
            cur_stop = max(cur_stop, best - trail_dist)
        else:
            if bar_hi >= cur_stop:
                exit_px = cur_stop
                exit_pos = i
                outcome = "trail_stop"
                break
            best = min(best, bar_lo)
            cur_stop = min(cur_stop, best + trail_dist)
    if exit_px is None:
        exit_px = cl[end_pos]
        exit_pos = end_pos
        outcome = "session_flatten"
    move = (exit_px - entry_px) if direction == 1 else (entry_px - exit_px)
    pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
    return exit_pos, exit_px, pnl, outcome


def _resolve_one_vectorized(entry_pos, direction, entry_px, stop_px, hi, lo, cl, n, pv, trail_mult,
                             contracts, commission, slip_dollars_rt, max_hold_bars=MAX_HOLD_BARS):
    """Vectorized equivalent of _resolve_one -- same semantics, needed because the
    scalar bar-by-bar Python loop is the dominant cost (~51s per single seed/tpd/risk
    config, making the planned grid infeasible; ~1000x too slow at this scale).

    Derivation: at bar i, resolve_trailing checks bar i's low/high against a stop
    level computed from bests-through-bar-(i-1) (the update to `best`/`cur_stop` using
    bar i's own high/low happens AFTER that bar's check, for the NEXT iteration) --
    i.e. applicable_stop[i] = max(entry, running_max_of_high[entry_pos:i]) - trail_dist
    for a long (running max EXCLUSIVE of bar i itself), symmetric for a short with
    running min of low and a `+ trail_dist`. This is computed here as a cummax/cummin
    shifted by one bar, matching that exactly -- validated against the scalar
    _resolve_one on real trade batches before being trusted (see
    validate_vectorized_matches_scalar below), not assumed correct from the derivation
    alone.
    """
    init_dist = abs(entry_px - stop_px)
    trail_dist = trail_mult * init_dist
    end_pos = min(entry_pos + max_hold_bars, n - 1)
    if entry_pos > end_pos:
        return end_pos, cl[min(entry_pos, n - 1)], 0.0, "no_bars"
    seg_hi = hi[entry_pos:end_pos + 1]
    seg_lo = lo[entry_pos:end_pos + 1]
    m = len(seg_hi)

    if direction == 1:
        cm = np.maximum.accumulate(seg_hi)
        best_before = np.empty(m)
        best_before[0] = entry_px
        if m > 1:
            best_before[1:] = np.maximum(entry_px, cm[:-1])
        applicable_stop = best_before - trail_dist
        hit = seg_lo <= applicable_stop
    else:
        cmn = np.minimum.accumulate(seg_lo)
        best_before = np.empty(m)
        best_before[0] = entry_px
        if m > 1:
            best_before[1:] = np.minimum(entry_px, cmn[:-1])
        applicable_stop = best_before + trail_dist
        hit = seg_hi >= applicable_stop

    hit_idx = np.argmax(hit) if hit.any() else -1
    if hit_idx >= 0:
        exit_pos = entry_pos + hit_idx
        exit_px = applicable_stop[hit_idx]
        outcome = "trail_stop"
    else:
        exit_pos = end_pos
        exit_px = cl[end_pos]
        outcome = "session_flatten"
    move = (exit_px - entry_px) if direction == 1 else (entry_px - exit_px)
    pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
    return exit_pos, exit_px, pnl, outcome


def validate_vectorized_matches_scalar(df1m, atr15, symbol, seed=0, risk=400, n_check=200):
    """Runs both resolvers on the same real candidate stream and requires exact
    agreement (pnl to the cent, same outcome, same exit_pos) on n_check trades before
    the vectorized path is used for anything reported. Not a spot-check assumption --
    an explicit gate."""
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip = 2 * tick * pv
    ts = df1m.index.values
    hi = df1m["high"].values
    lo = df1m["low"].values
    cl = df1m["close"].values
    n = len(df1m)
    atr_ts = atr15.index.values
    atr_vals = atr15.values

    cands = generate_candidates(df1m, seed, 1)  # tpd=1 gives one clean candidate/day to sample from
    checked = 0
    for row in cands.itertuples(index=False):
        if checked >= n_check:
            break
        cpos = int(np.searchsorted(ts, np.datetime64(row.ts)))
        direction = row.direction
        apos = np.searchsorted(atr_ts, ts[cpos], side="right") - 1
        if apos < 0 or not (atr_vals[apos] > 0):
            continue
        entry_px = cl[cpos]
        stop_dist = STOP_ATR_MULT * atr_vals[apos]
        stop_px = entry_px - stop_dist if direction == 1 else entry_px + stop_dist
        if abs(entry_px - stop_px) <= 0:
            continue
        contracts = max(1, int(risk // (abs(entry_px - stop_px) * pv)))
        commission = COMMISSION_RT * contracts
        entry_pos = cpos + 1
        if entry_pos >= n:
            continue
        a = _resolve_one(entry_pos, direction, entry_px, stop_px, hi, lo, cl, n, pv, TRAIL_ATR_MULT,
                          contracts, commission, slip)
        b = _resolve_one_vectorized(entry_pos, direction, entry_px, stop_px, hi, lo, cl, n, pv, TRAIL_ATR_MULT,
                                     contracts, commission, slip)
        if a[3] != b[3] or a[0] != b[0] or abs(a[2] - b[2]) > 0.01:
            raise AssertionError(f"scalar vs vectorized mismatch at cpos={cpos}: scalar={a} vectorized={b}")
        checked += 1
    if checked == 0:
        raise AssertionError("validate_vectorized_matches_scalar checked 0 trades -- test is vacuous")
    return checked


def generate_candidates(df1m, seed, trades_per_day):
    """Draw `trades_per_day` scalar (ts, direction) candidates per day, in Round 19's
    exact per-day call shape (rng.integers(0, len(day_idx)) then rng.random()),
    repeated trades_per_day times per day. At trades_per_day=1 this is the same RNG
    call sequence as round19_random_entry.generate_random_entries -- see
    verify_tpd1_reproduces_round19() below, which checks this explicitly rather than
    assuming it."""
    rng = np.random.default_rng(seed)
    dates = pd.Series(df1m.index.date, index=df1m.index)
    rows = []
    for day, day_idx in df1m.groupby(dates).groups.items():
        if len(day_idx) < 30:
            continue
        for _ in range(trades_per_day):
            chosen_ts = day_idx[rng.integers(0, len(day_idx))]
            direction = 1 if rng.random() < 0.5 else -1
            rows.append((day, chosen_ts, direction))
    return pd.DataFrame(rows, columns=["day", "ts", "direction"])


def verify_tpd1_reproduces_round19(df1m, seed=0):
    """Direct cross-check: generate_candidates(..., trades_per_day=1) must draw the
    exact same (ts, direction) pairs as round19_random_entry.generate_random_entries,
    for the same seed. Raises if not -- this is the correctness gate for everything
    else in this file."""
    mine = generate_candidates(df1m, seed, 1)[["ts", "direction"]].reset_index(drop=True)
    theirs = generate_random_entries(df1m, seed)[["ts", "direction"]].reset_index(drop=True)
    if len(mine) != len(theirs):
        raise AssertionError(f"length mismatch: mine={len(mine)} theirs={len(theirs)}")
    if not (mine["ts"].values == theirs["ts"].values).all():
        raise AssertionError("timestamp mismatch between generate_candidates(tpd=1) and round19's generator")
    if not (mine["direction"].values == theirs["direction"].values).all():
        raise AssertionError("direction mismatch between generate_candidates(tpd=1) and round19's generator")
    return True


def _day_bounds(df1m):
    """Precompute {date: (first_bar_pos, last_bar_pos)} ONCE per df1m -- module-level
    cache keyed by id(df1m), since df1m is the same object across every call in a run
    and this was previously (a real bug, not a style choice) recomputed by converting
    the ENTIRE multi-year datetime index to Python date objects on every single day of
    every call, ~1500x more work than necessary and the actual dominant cost (~51s per
    seed/tpd/risk config) -- not the resolver, which is fast once vectorized."""
    cache = _day_bounds.__dict__.setdefault("_cache", {})
    key = id(df1m)
    if key in cache:
        return cache[key]
    dates = pd.Series(df1m.index.date, index=df1m.index)
    groups = df1m.groupby(dates).groups
    ts = df1m.index.values
    bounds = {}
    for day, idx in groups.items():
        positions = np.searchsorted(ts, idx.values)
        bounds[day] = (int(positions.min()), int(positions.max()))
    cache[key] = bounds
    return bounds


def generate_and_resolve_multi(df1m, atr_series, seed, trades_per_day, risk_dollar, symbol,
                                trail_mult=TRAIL_ATR_MULT):
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values
    hi = df1m["high"].values
    lo = df1m["low"].values
    cl = df1m["close"].values
    n = len(df1m)
    atr_ts = atr_series.index.values
    atr_vals = atr_series.values
    day_bounds = _day_bounds(df1m)

    cands = generate_candidates(df1m, seed, trades_per_day)
    rows = []
    daily_counts = []
    for day, group in cands.groupby("day", sort=True):
        group = group.sort_values("ts")
        day_positions = np.searchsorted(ts, group["ts"].values)
        bounds = day_bounds.get(day)
        if bounds is None:
            continue
        _day_start_pos, day_end_pos = bounds

        available_from = _day_start_pos
        n_accepted = 0
        for cpos, direction in zip(day_positions, group["direction"].values):
            cpos = int(cpos)
            if cpos < available_from or cpos > day_end_pos:
                continue
            cand_ts = ts[cpos]
            apos = np.searchsorted(atr_ts, cand_ts, side="right") - 1
            if apos < 0:
                continue
            atr_val = atr_vals[apos]
            if not (atr_val > 0):
                continue
            entry_px = cl[cpos]
            stop_dist = STOP_ATR_MULT * atr_val
            stop_px = entry_px - stop_dist if direction == 1 else entry_px + stop_dist
            init_dist = abs(entry_px - stop_px)
            if init_dist <= 0:
                continue
            contracts = max(1, int(risk_dollar // (init_dist * pv)))
            commission = COMMISSION_RT * contracts
            # Round 19's resolve_trailing starts its stop-check loop at
            # searchsorted(ts, entry_ts, side="right") == cpos+1 (the bar AFTER entry),
            # not at the entry bar itself -- entry_px is already priced off the entry
            # bar's own close, so the earliest a stop/trail can trigger is the next bar.
            # cpos here comes from a side="left" search (correct for pricing/gating),
            # so cpos+1 must be passed to match that convention exactly.
            # Uses the vectorized resolver (validated exact-match against the scalar
            # _resolve_one on 600 real trades across 2 seeds/risk levels before use --
            # see validate_vectorized_matches_scalar) because the scalar version takes
            # ~51s per single seed/tpd/risk config, making the planned grid infeasible.
            exit_pos, exit_px, pnl, outcome = _resolve_one_vectorized(
                cpos + 1, direction, entry_px, stop_px, hi, lo, cl, n, pv, trail_mult,
                contracts, commission, slip_dollars_rt,
            )
            rows.append((cand_ts, symbol, direction, risk_dollar, contracts, pnl, outcome, str(day)))
            n_accepted += 1
            available_from = min(exit_pos, day_end_pos) + MIN_GAP_BARS
        daily_counts.append(n_accepted)

    trades = pd.DataFrame(rows, columns=["ts", "symbol", "direction", "risk", "contracts",
                                          "pnl", "outcome", "day"])
    return trades, daily_counts


def fold_slice(trades, train_end, test_end):
    return trades[(trades["ts"] >= pd.Timestamp(train_end)) & (trades["ts"] < pd.Timestamp(test_end))]


def daily_pnl_series(trades):
    return trades.groupby("day")["pnl"].sum()


def maxdd_of(pnl_values):
    equity = pd.Series(pnl_values).cumsum()
    peak = equity.cummax()
    return float((peak - equity).max()) if len(equity) else 0.0


def verify_tpd1_matches_resolve_trailing(df1m, atr15, symbol, seed=0, risk=400):
    """Second correctness gate: tpd=1 output from generate_and_resolve_multi must match
    running Round 19's own generate_random_entries -> build_stop_signals -> resolve_trailing
    pipeline directly on the SAME seed, trade for trade (same pnl sum and same n)."""
    mine, _ = generate_and_resolve_multi(df1m, atr15, seed, 1, risk, symbol)
    raw = generate_random_entries(df1m, seed)
    sig = build_stop_signals(raw, atr15)
    theirs = resolve_trailing(sig, df1m, symbol, risk, TRAIL_ATR_MULT)
    if len(mine) != len(theirs):
        raise AssertionError(f"n mismatch: mine={len(mine)} theirs={len(theirs)}")
    mine_sum = mine["pnl"].sum()
    theirs_sum = theirs["pnl"].sum()
    if abs(mine_sum - theirs_sum) > 0.01:
        raise AssertionError(f"pnl sum mismatch: mine={mine_sum:.2f} theirs={theirs_sum:.2f}")
    return True, len(mine), mine_sum


def run_grid(symbol, path):
    print(f"\n{'='*70}\nRound 23: {symbol} from {path}", flush=True)
    df1m = load_1m(path)
    atr15 = causal_atr15_lookup(df1m)
    print(f"{symbol}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)

    print("Verifying tpd=1 reproduces Round 19's exact RNG draws (candidate generation)...", flush=True)
    for seed in [0, 1, 3, 7]:
        verify_tpd1_reproduces_round19(df1m, seed)
    print("  PASS: candidate generation identical to round19_random_entry for tpd=1, seeds [0,1,3,7]", flush=True)

    print("Verifying tpd=1 full pipeline (entries+resolution) matches Round 19's resolve_trailing exactly "
          "(2 seeds -- this check calls Round 19's own slow scalar resolver as ground truth, ~50s/seed, kept "
          "short deliberately; the vectorized resolver used for the actual grid below is separately validated "
          "against the scalar _resolve_one on 600 sampled trades, see validate_vectorized_matches_scalar)...",
          flush=True)
    for seed in [0, 1]:
        ok, n_chk, sum_chk = verify_tpd1_matches_resolve_trailing(df1m, atr15, symbol, seed=seed, risk=400)
        print(f"  PASS seed={seed}: n={n_chk} pnl_sum=${sum_chk:.2f} matches Round 19's own pipeline exactly",
              flush=True)
    n_vec_checked = validate_vectorized_matches_scalar(df1m, atr15, symbol, seed=0, risk=400, n_check=300)
    n_vec_checked += validate_vectorized_matches_scalar(df1m, atr15, symbol, seed=3, risk=600, n_check=300)
    print(f"  PASS: vectorized resolver exact-matches scalar on {n_vec_checked} sampled real trades "
          f"(2 seed/risk combos)", flush=True)

    summary_rows = []
    for tpd in TRADES_PER_DAY_GRID:
        for risk in RISK_LEVELS:
            per_trade_exps, per_day_exps, worst_dd_over_seeds = [], [], 0.0
            all_seed_trades = []
            all_seed_actual_tpd = []
            for seed in SEEDS:
                trades, daily_counts = generate_and_resolve_multi(df1m, atr15, seed, tpd, risk, symbol)
                if len(trades) == 0:
                    continue
                all_seed_trades.append(trades)
                all_seed_actual_tpd.append(np.mean(daily_counts) if daily_counts else 0.0)
                per_trade_exps.append(trades["pnl"].mean())
                daily = daily_pnl_series(trades)
                per_day_exps.append(daily.mean())
                fold_dds = []
                for train_end, test_end in FOLDS:
                    fs = fold_slice(trades, train_end, test_end)
                    if len(fs) == 0:
                        continue
                    fold_dds.append(maxdd_of(daily_pnl_series(fs).values))
                if fold_dds:
                    worst_dd_over_seeds = max(worst_dd_over_seeds, max(fold_dds))
            if not all_seed_trades:
                continue
            pooled = pd.concat(all_seed_trades, ignore_index=True)
            mean_exp_trade = float(np.mean(per_trade_exps))
            mean_exp_day = float(np.mean(per_day_exps))
            mean_actual_tpd = float(np.mean(all_seed_actual_tpd))
            tc10 = tail_concentration(pooled, 10)
            tc20 = tail_concentration(pooled, 20)
            print(f"tpd_target={tpd} risk=${risk}: actual_tpd={mean_actual_tpd:.2f} "
                  f"n_trades_pooled={len(pooled)} exp/trade=${mean_exp_trade:.2f} "
                  f"exp/day=${mean_exp_day:.2f} worst_day_maxdd(8 seeds x 6 folds)=${worst_dd_over_seeds:.2f} "
                  f"tail10={tc10} tail20={tc20}", flush=True)
            summary_rows.append(dict(tpd_target=tpd, risk=risk, actual_tpd=mean_actual_tpd,
                                      n=len(pooled), exp_trade=mean_exp_trade, exp_day=mean_exp_day,
                                      worst_day_maxdd=worst_dd_over_seeds, tail10=tc10, tail20=tc20))
    return pd.DataFrame(summary_rows), df1m, atr15


SIZING_GRID = (400, 300, 200, 150, 125, 100, 75, 50, 25)
SAFETY_MARGIN_TARGET = 0.70 * BUFFER


def buffer_safe_search_wide(df1m, atr15, symbol, tpd, seeds=SEEDS_WIDE):
    """Same 70%-of-real-buffer convention as Round 20/22, but with a widened seed
    count (25, not 8) specifically because worst-case-over-seeds is an extreme-value
    statistic that 8 samples estimates poorly."""
    rows = []
    for risk in SIZING_GRID:
        per_trade_exps, per_day_exps, worst_dd = [], [], 0.0
        all_trades = []
        for seed in seeds:
            trades, daily_counts = generate_and_resolve_multi(df1m, atr15, seed, tpd, risk, symbol)
            if len(trades) == 0:
                continue
            all_trades.append(trades)
            per_trade_exps.append(trades["pnl"].mean())
            per_day_exps.append(daily_pnl_series(trades).mean())
            for train_end, test_end in FOLDS:
                fs = fold_slice(trades, train_end, test_end)
                if len(fs) == 0:
                    continue
                worst_dd = max(worst_dd, maxdd_of(daily_pnl_series(fs).values))
        if not all_trades:
            continue
        pooled = pd.concat(all_trades, ignore_index=True)
        exp_trade = float(np.mean(per_trade_exps))
        exp_day = float(np.mean(per_day_exps))
        within_target = worst_dd <= SAFETY_MARGIN_TARGET
        within_full_buffer = worst_dd <= BUFFER
        rows.append(dict(tpd_target=tpd, risk=risk, n_seeds=len(seeds), n=len(pooled),
                          exp_trade=exp_trade, exp_day=exp_day, worst_day_maxdd=worst_dd,
                          within_70pct_target=within_target, within_full_buffer=within_full_buffer))
        print(f"  [sizing-wide,{len(seeds)}seeds] tpd={tpd} risk=${risk}: exp/day=${exp_day:.2f} "
              f"worst_day_maxdd=${worst_dd:.2f} within_70pct={within_target} within_full_buffer={within_full_buffer}",
              flush=True)
        if within_target:
            break
    return pd.DataFrame(rows)


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "..", "data", "MNQ_CONTINUOUS.txt")
    res_grid, df1m, atr15 = run_grid("MNQ", path)
    print("\n\n=== MNQ GRID (tpd 1..8, $400/$600) ===")
    print(res_grid.to_string(index=False))
    res_grid.to_csv(os.path.join(os.path.dirname(__file__), "round23_mnq_grid.csv"), index=False)

    print(f"\n\n=== BUFFER-SAFE SIZING SEARCH, {len(SEEDS_WIDE)} SEEDS (per trades/day target) ===", flush=True)
    all_sizing = []
    for tpd in TRADES_PER_DAY_GRID:
        print(f"\n--- tpd_target={tpd} ---", flush=True)
        sizing_df = buffer_safe_search_wide(df1m, atr15, "MNQ", tpd)
        all_sizing.append(sizing_df)
    sizing_all = pd.concat(all_sizing, ignore_index=True)
    print("\n\n=== FULL SIZING TABLE ===")
    print(sizing_all.to_string(index=False))
    sizing_all.to_csv(os.path.join(os.path.dirname(__file__), "round23_sizing_search.csv"), index=False)
    print("\nDONE.", flush=True)
