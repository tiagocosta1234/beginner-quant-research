"""
Round 19: Random entry + managed exit -- decoupling "is the entry-timing any good"
from "is the exit/management any good", a question every prior round (1-18)
conflated by testing a specific entry condition together with a fairly simple exit.

Entries: exactly one per RTH trading day, uniformly random bar and direction (50/50
long/short), independent of price -- i.e. zero entry-timing skill by construction.
Run across 8 independent seeds per instrument so results are a distribution, not one
lucky/unlucky draw.

Exit variants (the actual variable under test):
  A. Fixed R:R (rr in {1.0, 1.5, 2.0}, train-only selected per fold) -- the
     null-hypothesis control, same shape as almost every prior round.
  B. A + breakeven-stop-move at 1.0R (reuses round12_fvg_confirmation.resolve_outcomes_be
     unchanged).
  C. ATR-based trailing stop, no fixed target -- a genuinely different exit
     philosophy from anything in Rounds 1-18. trail_mult fixed at 1.5x ATR(14@15m),
     not grid-searched (kept fixed deliberately, same precedent as Round 14's
     ATR_MULT -- avoids a per-fold combinatorial explosion for a style-comparison
     round, and a fixed exit-only knob cannot itself be overfit to a fold).
  D. Time-based exit -- flatten unconditionally after 30 minutes regardless of P&L
     (a hard ATR stop still applies for risk containment/sizing, matching every
     other variant's risk model), independent of C.

Initial stop distance for all variants = 1.0 x ATR(14) on causal 15-min bars, the
most recently *closed* 15m bar as of the entry bar (same causal-lookup pattern as
round11_fvg_bias.attach_trend). This is what makes contract sizing at $400/$600 risk
well-defined even though there's no chart structure to derive a stop from.

Walk-forward: same FOLDS (expanding-window, 6 OOS windows, 2024-01 -> 2026-09), same
costs ($1.24/contract round-trip commission, 2-tick round-trip slippage), same
risk levels ($400/$600), same one-trade/day/instrument convention (trivially true
here since entries are already exactly 1/day by construction), same tail-concentration
check on anything showing positive aggregate profit.
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, resample_causal, POINT_VALUE, TICK_SIZE, COMMISSION_RT, BUFFER, FOLDS,
    fold_stats, tail_concentration,
)
from round12_fvg_confirmation import resolve_outcomes_plain, resolve_outcomes_be, walk_forward_generic, print_results
from round14_meanreversion import atr_causal

SEEDS = list(range(8))
STOP_ATR_MULT = 1.0
TRAIL_ATR_MULT = 1.5
TIME_EXIT_MINUTES = 30
RR_GRID = (1.0, 1.5, 2.0)
BE_TRIGGER_R = 1.0
RISK_LEVELS = (400, 600)


def causal_atr15_lookup(df1m):
    """15m ATR(14), then a lookup Series usable the same way as attach_trend: given a
    1m timestamp, find the value of the most recently CLOSED 15m bar as of that ts."""
    h15 = resample_causal(df1m, "15min")
    atr = atr_causal(h15, n=14)
    return atr.dropna()


def attach_atr(signals, atr_series):
    atr_ts = atr_series.index.values
    pos = np.searchsorted(atr_ts, signals["ts"].values, side="right") - 1
    out = signals.copy()
    valid = pos >= 0
    out = out[valid].copy()
    pos = pos[valid]
    out["atr"] = atr_series.values[pos]
    return out.reset_index(drop=True)


def generate_random_entries(df1m, seed):
    """Exactly one random (bar, direction) per RTH trading day. Entry price = that
    bar's own close. Direction/time are pure noise draws, independent of price, so
    causality is trivial here (nothing is derived FROM price to pick the entry)."""
    rng = np.random.default_rng(seed)
    dates = pd.Series(df1m.index.date, index=df1m.index)
    rows = []
    for day, day_idx in df1m.groupby(dates).groups.items():
        if len(day_idx) < 30:
            continue
        chosen_ts = day_idx[rng.integers(0, len(day_idx))]
        direction = 1 if rng.random() < 0.5 else -1
        entry_px = df1m.loc[chosen_ts, "close"]
        rows.append((chosen_ts, direction, entry_px))
    sig = pd.DataFrame(rows, columns=["ts", "direction", "entry"]).sort_values("ts").reset_index(drop=True)
    return sig


def build_stop_signals(sig, atr_series):
    """Attach ATR-derived stop to raw random entries -> (ts, direction, entry, stop),
    the shape resolve_outcomes_plain/resolve_outcomes_be expect."""
    s = attach_atr(sig, atr_series)
    s = s[s["atr"] > 0].copy()
    stop_dist = STOP_ATR_MULT * s["atr"]
    s["stop"] = np.where(s["direction"] == 1, s["entry"] - stop_dist, s["entry"] + stop_dist)
    return s[["ts", "direction", "entry", "stop"]].reset_index(drop=True)


def resolve_trailing(sig_df, df1m, symbol, risk_dollar, trail_mult, max_hold_bars=390):
    """No fixed target. Trail the stop by trail_mult * (the ATR-derived initial stop
    distance, fixed at entry -- not re-computed bar by bar, kept simple/deterministic)
    as price moves favorably; stop only ever tightens, never loosens. Exit on stop hit,
    or flatten at the last bar's close if max_hold_bars/session elapses first (approximates
    this account's real same-day-flatten rule, same simplification every prior round's
    max_hold_bars=390 already used)."""
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values
    hi = df1m["high"].values
    lo = df1m["low"].values
    cl = df1m["close"].values
    n = len(df1m)
    results = []
    for r in sig_df.itertuples(index=False):
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        init_dist = abs(r.entry - r.stop)
        if init_dist <= 0:
            continue
        trail_dist = trail_mult * init_dist
        contracts = max(1, int(risk_dollar // (init_dist * pv)))
        commission = COMMISSION_RT * contracts
        end_pos = min(pos + max_hold_bars, n - 1)
        cur_stop = r.entry - trail_dist if r.direction == 1 else r.entry + trail_dist
        best = r.entry
        exit_px = None
        outcome = "timeout"
        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo = hi[i], lo[i]
            if r.direction == 1:
                if bar_lo <= cur_stop:
                    exit_px = cur_stop
                    outcome = "trail_stop"
                    break
                best = max(best, bar_hi)
                cur_stop = max(cur_stop, best - trail_dist)
            else:
                if bar_hi >= cur_stop:
                    exit_px = cur_stop
                    outcome = "trail_stop"
                    break
                best = min(best, bar_lo)
                cur_stop = min(cur_stop, best + trail_dist)
        if exit_px is None:
            exit_px = cl[end_pos]
            outcome = "session_flatten"
        move = (exit_px - r.entry) if r.direction == 1 else (r.entry - exit_px)
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, symbol, r.direction, np.nan, risk_dollar, contracts, pnl, outcome))
    return pd.DataFrame(results, columns=["ts", "symbol", "direction", "rr", "risk", "contracts",
                                           "pnl", "outcome"])


def resolve_time_exit(sig_df, df1m, symbol, risk_dollar, hold_minutes, max_hold_bars=390):
    """Hard ATR stop for risk containment (same sizing convention as every other
    variant); otherwise flatten unconditionally at `hold_minutes` after entry (or the
    session cap, whichever is sooner) regardless of P&L -- tests whether just
    shortening TIME-in-trade helps a random entry on its own."""
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values
    hi = df1m["high"].values
    lo = df1m["low"].values
    cl = df1m["close"].values
    n = len(df1m)
    hold_bars = max(1, hold_minutes)  # data is 1-min bars, so minutes == bars 1:1
    results = []
    for r in sig_df.itertuples(index=False):
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        stop_dist = abs(r.entry - r.stop)
        if stop_dist <= 0:
            continue
        stop_px = r.stop
        contracts = max(1, int(risk_dollar // (stop_dist * pv)))
        commission = COMMISSION_RT * contracts
        end_pos = min(pos + min(hold_bars, max_hold_bars), n - 1)
        exit_px = None
        outcome = "time_exit"
        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo = hi[i], lo[i]
            if r.direction == 1 and bar_lo <= stop_px:
                exit_px = stop_px
                outcome = "stop"
                break
            if r.direction == -1 and bar_hi >= stop_px:
                exit_px = stop_px
                outcome = "stop"
                break
        if exit_px is None:
            exit_px = cl[end_pos]
        move = (exit_px - r.entry) if r.direction == 1 else (r.entry - exit_px)
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, symbol, r.direction, np.nan, risk_dollar, contracts, pnl, outcome))
    return pd.DataFrame(results, columns=["ts", "symbol", "direction", "rr", "risk", "contracts",
                                           "pnl", "outcome"])


def walk_forward_fixed(sig_all, df1m, symbol, resolve_fn, resolve_kwargs, risk_levels=RISK_LEVELS):
    """Same FOLDS date-slicing as walk_forward_generic, but for exit styles with no
    per-fold-selected parameter (nothing to grid-search) -- every fold's date window is
    resolved directly, still reported fold-by-fold in the same shape as everywhere else."""
    out = {}
    for risk in risk_levels:
        fold_rows = []
        for train_end, test_end in FOLDS:
            test_sig = sig_all[(sig_all["ts"] >= train_end) & (sig_all["ts"] < test_end)]
            if len(test_sig) == 0:
                fold_rows.append((train_end, test_end, None, None))
                continue
            te = resolve_fn(test_sig, df1m, symbol, risk, **resolve_kwargs)
            fold_rows.append((train_end, test_end, None, te))
        out[risk] = fold_rows
    return out


def summarize_across_seeds(all_seed_results, risk):
    """all_seed_results: list of per-seed aggregate trade DataFrames (already the
    combined-across-folds trades for one exit variant at one risk level). Returns the
    across-seed distribution of aggregate expectancy/trade, not a single draw."""
    exps = []
    for trades in all_seed_results:
        if trades is not None and len(trades) > 0:
            exps.append(trades["pnl"].mean())
    if not exps:
        return None
    exps = np.array(exps)
    return dict(n_seeds=len(exps), mean=exps.mean(), std=exps.std(), min=exps.min(), max=exps.max(),
                n_positive=int((exps > 0).sum()))


def run_symbol(symbol, path):
    print(f"\n{'='*70}\nLoading {symbol} from {path} ...", flush=True)
    df1m = load_1m(path)
    print(f"{symbol}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)
    atr15 = causal_atr15_lookup(df1m)
    print(f"{symbol}: computed causal 15m ATR(14), {len(atr15)} values", flush=True)

    variant_seed_trades = {
        "A_fixed_rr": {400: [], 600: []},
        "B_fixed_rr_plus_be": {400: [], 600: []},
        "C_atr_trailing": {400: [], 600: []},
        "D_time_exit_30m": {400: [], 600: []},
    }
    variant_seed_fold_breaches = {
        "A_fixed_rr": {400: [], 600: []},
        "B_fixed_rr_plus_be": {400: [], 600: []},
        "C_atr_trailing": {400: [], 600: []},
        "D_time_exit_30m": {400: [], 600: []},
    }

    for seed in SEEDS:
        raw = generate_random_entries(df1m, seed)
        sig = build_stop_signals(raw, atr15)
        print(f"\n--- {symbol} seed={seed}: {len(raw)} random entries -> {len(sig)} with valid ATR stop ---",
              flush=True)

        res_a = walk_forward_generic(sig, df1m, symbol, resolve_outcomes_plain, {}, rr_grid=RR_GRID,
                                      risk_levels=RISK_LEVELS)
        res_b = walk_forward_generic(sig, df1m, symbol, resolve_outcomes_be, {"be_trigger_r": BE_TRIGGER_R},
                                      rr_grid=RR_GRID, risk_levels=RISK_LEVELS)
        res_c = walk_forward_fixed(sig, df1m, symbol, resolve_trailing, {"trail_mult": TRAIL_ATR_MULT})
        res_d = walk_forward_fixed(sig, df1m, symbol, resolve_time_exit, {"hold_minutes": TIME_EXIT_MINUTES})

        for label, res, store, breach_store in [
            ("A", res_a, variant_seed_trades["A_fixed_rr"], variant_seed_fold_breaches["A_fixed_rr"]),
            ("B", res_b, variant_seed_trades["B_fixed_rr_plus_be"], variant_seed_fold_breaches["B_fixed_rr_plus_be"]),
            ("C", res_c, variant_seed_trades["C_atr_trailing"], variant_seed_fold_breaches["C_atr_trailing"]),
            ("D", res_d, variant_seed_trades["D_time_exit_30m"], variant_seed_fold_breaches["D_time_exit_30m"]),
        ]:
            for risk, fold_rows in res.items():
                trades_list = [te for (_, _, _, te) in fold_rows if te is not None and len(te) > 0]
                combo = pd.concat(trades_list, ignore_index=True) if trades_list else None
                store[risk].append(combo)
                fold_breaches = []
                for (te_start, te_end, _rr, te) in fold_rows:
                    if te is None or len(te) == 0:
                        continue
                    st = fold_stats(te)
                    fold_breaches.append((te_start, te_end, st["maxdd"], st["breach"]))
                breach_store[risk].extend(fold_breaches)
                worst_fold = max(fold_breaches, key=lambda x: x[2]) if fold_breaches else None
                n_breach = sum(1 for f in fold_breaches if f[3])
                if combo is not None:
                    print(f"  seed={seed} variant={label} risk=${risk} n={len(combo)} "
                          f"exp=${combo['pnl'].mean():.2f} total=${combo['pnl'].sum():.2f} "
                          f"win%={(combo['pnl']>0).mean():.1%} "
                          f"folds_breaching_buffer={n_breach}/{len(fold_breaches)} "
                          f"worst_fold_maxdd=${worst_fold[2]:.2f} ({worst_fold[0]}->{worst_fold[1]})",
                          flush=True)

    print(f"\n### {symbol}: ACROSS-SEED SUMMARY ({len(SEEDS)} seeds) ###", flush=True)
    summary = {}
    for variant, per_risk in variant_seed_trades.items():
        summary[variant] = {}
        for risk, seed_trades in per_risk.items():
            dist = summarize_across_seeds(seed_trades, risk)
            summary[variant][risk] = dist
            fold_breaches = variant_seed_fold_breaches[variant][risk]
            n_fold_windows = len(fold_breaches)
            n_breach = sum(1 for f in fold_breaches if f[3])
            worst = max(fold_breaches, key=lambda x: x[2]) if fold_breaches else None
            if dist:
                print(f"  {variant} risk=${risk}: mean_exp=${dist['mean']:.2f} std=${dist['std']:.2f} "
                      f"min=${dist['min']:.2f} max=${dist['max']:.2f} "
                      f"positive_seeds={dist['n_positive']}/{dist['n_seeds']} | "
                      f"seed-fold windows breaching buffer={n_breach}/{n_fold_windows} "
                      f"worst_maxdd=${worst[2]:.2f} ({worst[0]}->{worst[1]})", flush=True)
                # tail-concentration on the pooled (all-seeds) trade set, for context,
                # only meaningful if pooled aggregate is positive
                pooled = pd.concat([t for t in seed_trades if t is not None], ignore_index=True)
                if len(pooled) > 0 and pooled["pnl"].sum() > 0:
                    tc10 = tail_concentration(pooled, 10)
                    tc20 = tail_concentration(pooled, 20)
                    print(f"    pooled n={len(pooled)} total=${pooled['pnl'].sum():.2f} "
                          f"tail10={tc10:.1f}% tail20={tc20:.1f}%", flush=True)
            else:
                print(f"  {variant} risk=${risk}: no trades", flush=True)
    return summary


if __name__ == "__main__":
    results = {}
    results["MNQ"] = run_symbol("MNQ", os.path.join(os.path.dirname(__file__), "..", "data", "MNQ_CONTINUOUS.txt"))
    results["MGC"] = run_symbol("MGC", os.path.join(os.path.dirname(__file__), "..", "data", "MGC_CONTINUOUS.txt"))
    print("\n\nDONE.", flush=True)
