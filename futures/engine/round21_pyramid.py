"""
Round 21: does PYRAMIDING (scale-in) the exit convexity Round 19 validated change its
buffer-safe expectancy, in either direction?

Direct follow-up to Round 19 (found the campaign's one real, tail-clean edge: random
entries + ATR-trailing exit, 8/8 seeds positive on MNQ) and Round 20 (confirmed real
entries don't beat random -- the edge is purely in the exit -- then sized the random-
entry version down to $75/trade risk -> $20.47/trade expectancy to survive the real
$4,937.50 buffer, closing only 1.6-2.7% of the $767-1,279/trade pace needed before
October).

Standard CTA/trend-following practice for thin starting capital is to start with one
small unit and add units only once the trade has already moved favorably enough that
the addition is effectively live by locked-in open profit, not fresh account risk.
Each added unit gets its OWN trailing stop off the point it was added (a freshly
recomputed causal ATR distance at the add bar, not the original entry's distance) --
this is what could cap worst-case loss differently than a single flat-sized unit: if
price reverses right after an add, only the new unit's own stop is at risk from that
point forward, while unit 1's stop has typically already trailed up by the time an add
triggers. This has not been tested anywhere in Rounds 1-20. Whether it actually reduces
worst-case drawdown relative to flat sizing (Round 20's approach) is an empirical
question this round answers directly, not an assumption baked into the design.

Entries: reuses Round 19/20's random-entry basis unchanged (round19_random_entry
already established real entries make Round 20's tail concentration WORSE, not
better -- no need to re-litigate that here). Uses only seed=0 for the Part 1
head-to-head comparison against Round 20's flat-sizing numbers (single representative
seed, not the full 8-seed distribution -- Round 19/20 already established random
entry's aggregate behavior; this round's question is specifically "does the SIZING
STRUCTURE change the risk/reward shape," which doesn't require re-running the full
seed distribution to answer directionally) and the same fold structure as every prior
round.

Add-trigger grid: {0.5, 1.0, 1.5} x the initial ATR stop distance, train-only selected
per fold (identical convention to every rr-grid search in this campaign, e.g.
round12_fvg_confirmation.walk_forward_generic). trail_mult fixed at 1.5x (Round 19's
TRAIL_ATR_MULT, unchanged, so the exit's own trailing behavior is held constant and
only the pyramid add-rule is the new variable). max_units=2 (at most one add) --
deliberately not testing 3+ units until 2 is shown to help at all, per the task's own
scope instruction.
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
from round19_random_entry import (
    generate_random_entries, build_stop_signals, causal_atr15_lookup,
    resolve_trailing, STOP_ATR_MULT, TRAIL_ATR_MULT,
)

SYMBOL = "MNQ"
ADD_TRIGGER_GRID = (0.5, 1.0, 1.5)
MAX_UNITS = 2
SEED_FOR_COMPARISON = 0
RISK_LEVELS = (400, 600)


def resolve_pyramid(sig_df, df1m, symbol, risk_dollar, trail_mult, add_trigger_r, atr_series,
                     max_units=MAX_UNITS, max_hold_bars=390):
    """Unit 1: identical sizing/trailing to round19_random_entry.resolve_trailing. Once
    the favorable excursion from entry reaches add_trigger_r * unit 1's initial ATR stop
    distance, add unit 2 at that bar's close, sized off a FRESHLY recomputed causal ATR
    distance at the add bar (same atr_series lookup used for entry stops -- no lookahead),
    budgeted to the same risk_dollar as unit 1. Each unit trails and exits independently
    off its own entry/stop; total trade P&L/contracts = the sum across whichever units
    were actually opened. max_units=2 means at most one add is considered."""
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

    def atr_at(bar_ts):
        p = np.searchsorted(atr_ts, bar_ts, side="right") - 1
        return atr_vals[p] if p >= 0 else None

    results = []
    for r in sig_df.itertuples(index=False):
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        init_dist = abs(r.entry - r.stop)
        if init_dist <= 0:
            continue
        trail_dist1 = trail_mult * init_dist
        contracts1 = max(1, int(risk_dollar // (init_dist * pv)))
        commission1 = COMMISSION_RT * contracts1
        end_pos = min(pos + max_hold_bars, n - 1)

        cur_stop1 = r.entry - trail_dist1 if r.direction == 1 else r.entry + trail_dist1
        best1 = r.entry
        unit1_open = True
        unit1_pnl = 0.0

        unit2 = None
        n_units = 1
        add_trigger_dist = add_trigger_r * init_dist
        outcome_parts = []

        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo = hi[i], lo[i]

            if unit1_open:
                if r.direction == 1:
                    if bar_lo <= cur_stop1:
                        move = cur_stop1 - r.entry
                        unit1_pnl = move * pv * contracts1 - commission1 - slip_dollars_rt * contracts1
                        unit1_open = False
                        outcome_parts.append("u1_stop")
                    else:
                        best1 = max(best1, bar_hi)
                        cur_stop1 = max(cur_stop1, best1 - trail_dist1)
                else:
                    if bar_hi >= cur_stop1:
                        move = r.entry - cur_stop1
                        unit1_pnl = move * pv * contracts1 - commission1 - slip_dollars_rt * contracts1
                        unit1_open = False
                        outcome_parts.append("u1_stop")
                    else:
                        best1 = min(best1, bar_lo)
                        cur_stop1 = min(cur_stop1, best1 + trail_dist1)

            if unit1_open and unit2 is None and n_units < max_units:
                favorable = (best1 - r.entry) if r.direction == 1 else (r.entry - best1)
                if favorable >= add_trigger_dist:
                    a = atr_at(ts[i])
                    if a is not None and a > 0:
                        add_price = cl[i]
                        add_init_dist = STOP_ATR_MULT * a
                        add_contracts = max(1, int(risk_dollar // (add_init_dist * pv)))
                        add_trail_dist = trail_mult * add_init_dist
                        add_stop = (add_price - add_trail_dist if r.direction == 1
                                    else add_price + add_trail_dist)
                        unit2 = dict(entry=add_price, stop=add_stop, trail_dist=add_trail_dist,
                                     contracts=add_contracts, best=add_price, open=True, pnl=0.0)
                        n_units += 1
                        outcome_parts.append("added_u2")

            if unit2 is not None and unit2["open"]:
                if r.direction == 1:
                    if bar_lo <= unit2["stop"]:
                        move = unit2["stop"] - unit2["entry"]
                        c2 = COMMISSION_RT * unit2["contracts"]
                        unit2["pnl"] = move * pv * unit2["contracts"] - c2 - slip_dollars_rt * unit2["contracts"]
                        unit2["open"] = False
                        outcome_parts.append("u2_stop")
                    else:
                        unit2["best"] = max(unit2["best"], bar_hi)
                        unit2["stop"] = max(unit2["stop"], unit2["best"] - unit2["trail_dist"])
                else:
                    if bar_hi >= unit2["stop"]:
                        move = unit2["entry"] - unit2["stop"]
                        c2 = COMMISSION_RT * unit2["contracts"]
                        unit2["pnl"] = move * pv * unit2["contracts"] - c2 - slip_dollars_rt * unit2["contracts"]
                        unit2["open"] = False
                        outcome_parts.append("u2_stop")
                    else:
                        unit2["best"] = min(unit2["best"], bar_lo)
                        unit2["stop"] = min(unit2["stop"], unit2["best"] + unit2["trail_dist"])

            if not unit1_open and (unit2 is None or not unit2["open"]):
                break

        if unit1_open:
            exit_px = cl[end_pos]
            move = (exit_px - r.entry) if r.direction == 1 else (r.entry - exit_px)
            unit1_pnl = move * pv * contracts1 - commission1 - slip_dollars_rt * contracts1
            outcome_parts.append("u1_timeout")
        if unit2 is not None and unit2["open"]:
            exit_px = cl[end_pos]
            move = (exit_px - unit2["entry"]) if r.direction == 1 else (unit2["entry"] - exit_px)
            c2 = COMMISSION_RT * unit2["contracts"]
            unit2["pnl"] = move * pv * unit2["contracts"] - c2 - slip_dollars_rt * unit2["contracts"]
            outcome_parts.append("u2_timeout")

        total_contracts = contracts1 + (unit2["contracts"] if unit2 is not None else 0)
        total_pnl = unit1_pnl + (unit2["pnl"] if unit2 is not None else 0.0)
        added = unit2 is not None
        results.append((r.ts, symbol, r.direction, np.nan, risk_dollar, total_contracts, total_pnl,
                         "+".join(outcome_parts) if outcome_parts else "flat", added))
    return pd.DataFrame(results, columns=["ts", "symbol", "direction", "rr", "risk", "contracts",
                                           "pnl", "outcome", "added_unit"])


def walk_forward_pyramid(sig_all, df1m, symbol, atr_series, trail_mult=TRAIL_ATR_MULT,
                          add_grid=ADD_TRIGGER_GRID, risk_levels=RISK_LEVELS):
    """Train-only add_trigger_r selection per fold, applied unchanged OOS -- identical
    convention to round12_fvg_confirmation.walk_forward_generic's rr-grid search."""
    out = {}
    for risk in risk_levels:
        fold_rows = []
        for train_end, test_end in FOLDS:
            train_sig = sig_all[sig_all["ts"] < train_end]
            test_sig = sig_all[(sig_all["ts"] >= train_end) & (sig_all["ts"] < test_end)]
            if len(train_sig) < 20 or len(test_sig) == 0:
                fold_rows.append((train_end, test_end, None, None))
                continue
            best_trig, best_exp = None, -1e18
            for trig in add_grid:
                tr = resolve_pyramid(train_sig, df1m, symbol, risk, trail_mult, trig, atr_series)
                if len(tr) == 0:
                    continue
                exp = tr["pnl"].mean()
                if exp > best_exp:
                    best_exp, best_trig = exp, trig
            if best_trig is None:
                fold_rows.append((train_end, test_end, None, None))
                continue
            te = resolve_pyramid(test_sig, df1m, symbol, risk, trail_mult, best_trig, atr_series)
            fold_rows.append((train_end, test_end, best_trig, te))
        out[risk] = fold_rows
    return out


def summarize(label, res):
    print(f"\n=== {label} ===", flush=True)
    out = {}
    for risk, fold_rows in res.items():
        all_trades = []
        worst_dd = 0.0
        for train_end, test_end, trig, te in fold_rows:
            if te is None or len(te) == 0:
                print(f"  risk=${risk} {train_end}->{test_end}: no trades", flush=True)
                continue
            st = fold_stats(te)
            n_added = int(te["added_unit"].sum())
            print(f"  risk=${risk} {train_end}->{test_end} add_trig={trig} n={st['n']} "
                  f"(added_2nd_unit={n_added}) win%={st['winrate']:.1%} exp=${st['expectancy']:.2f} "
                  f"total=${st['total']:.2f} maxdd=${st['maxdd']:.2f} breach={st['breach']}", flush=True)
            all_trades.append(te)
            worst_dd = max(worst_dd, st["maxdd"])
        if all_trades:
            combo = pd.concat(all_trades, ignore_index=True)
            exp = combo["pnl"].mean()
            n_added_total = int(combo["added_unit"].sum())
            entry = dict(n=len(combo), exp=exp, total=combo["pnl"].sum(),
                         winrate=(combo["pnl"] > 0).mean(), worst_maxdd=worst_dd,
                         n_added=n_added_total, pct_added=n_added_total / len(combo) * 100)
            if combo["pnl"].sum() > 0:
                entry["tail10"] = tail_concentration(combo, 10)
                entry["tail20"] = tail_concentration(combo, 20)
            print(f"  AGGREGATE risk=${risk} n={entry['n']} exp=${entry['exp']:.2f} "
                  f"total=${entry['total']:.2f} win%={entry['winrate']:.1%} "
                  f"worst_maxdd=${entry['worst_maxdd']:.2f} "
                  f"2nd-unit added on {entry['n_added']}/{entry['n']} ({entry['pct_added']:.1f}%) " +
                  (f"tail10={entry.get('tail10'):.1f}% tail20={entry.get('tail20'):.1f}%"
                   if "tail10" in entry else "(no tail check: aggregate not positive)"), flush=True)
            out[risk] = entry
        else:
            out[risk] = None
    return out


def find_buffer_safe_risk_pyramid(sig_df, df1m, symbol, atr_series, candidate_risks, margin_frac=0.70):
    target = margin_frac * BUFFER
    print(f"\n=== Pyramid buffer-safe sizing search (target worst maxdd <= ${target:.2f} = "
          f"{margin_frac:.0%} of ${BUFFER:.2f}) ===", flush=True)
    best = None
    for risk in candidate_risks:
        res = walk_forward_pyramid(sig_df, df1m, symbol, atr_series, risk_levels=(risk,))[risk]
        all_trades = []
        worst_dd = 0.0
        for train_end, test_end, trig, te in res:
            if te is None or len(te) == 0:
                continue
            st = fold_stats(te)
            worst_dd = max(worst_dd, st["maxdd"])
            all_trades.append(te)
        if not all_trades:
            print(f"  risk=${risk}: no trades", flush=True)
            continue
        combo = pd.concat(all_trades, ignore_index=True)
        exp = combo["pnl"].mean()
        ok = worst_dd <= target
        print(f"  risk=${risk}: n={len(combo)} exp=${exp:.2f} worst_maxdd=${worst_dd:.2f} "
              f"within_target={ok}", flush=True)
        if ok and (best is None or risk > best[0]):
            best = (risk, exp, worst_dd, len(combo))
    return best


def main():
    print(f"Loading {SYMBOL}...", flush=True)
    df1m = load_1m(os.path.join(os.path.dirname(__file__), "..", "data", f"{SYMBOL}_CONTINUOUS.txt"))
    print(f"{SYMBOL}: {len(df1m)} 1m bars, {df1m.index[0]} -> {df1m.index[-1]}", flush=True)
    atr15 = causal_atr15_lookup(df1m)

    # --- Baseline sanity check: reproduce Round 20's flat 1-contract, $75-risk config ---
    raw = generate_random_entries(df1m, SEED_FOR_COMPARISON)
    sig = build_stop_signals(raw, atr15)
    print(f"\nseed={SEED_FOR_COMPARISON}: {len(raw)} random entries -> {len(sig)} with valid ATR stop", flush=True)

    print("\n### BASELINE SANITY CHECK: flat sizing (Round 19's resolve_trailing), seed=0 only ###", flush=True)
    flat_results = {}
    for risk in (400, 75):
        fold_rows = []
        for train_end, test_end in FOLDS:
            test_sig = sig[(sig["ts"] >= train_end) & (sig["ts"] < test_end)]
            te = resolve_trailing(test_sig, df1m, SYMBOL, risk, TRAIL_ATR_MULT) if len(test_sig) else None
            fold_rows.append((train_end, test_end, te))
        all_trades = [te for (_, _, te) in fold_rows if te is not None and len(te) > 0]
        if all_trades:
            combo = pd.concat(all_trades, ignore_index=True)
            worst_dd = max(fold_stats(te)["maxdd"] for (_, _, te) in fold_rows if te is not None and len(te) > 0)
            print(f"  FLAT (seed=0 only) risk=${risk}: n={len(combo)} exp=${combo['pnl'].mean():.2f} "
                  f"worst_maxdd=${worst_dd:.2f}", flush=True)
            flat_results[risk] = dict(exp=combo["pnl"].mean(), worst_maxdd=worst_dd, n=len(combo))

    # --- Part 1: pyramid vs flat, same seed, $400/$600 (head-to-head against Round 19/20 numbers) ---
    print("\n\n### PART 1: PYRAMID (max 2 units) vs FLAT, seed=0, $400/$600 risk ###", flush=True)
    pyramid_results = walk_forward_pyramid(sig, df1m, SYMBOL, atr15, risk_levels=RISK_LEVELS)
    summary_400_600 = summarize("Pyramid, add-trigger grid {0.5,1.0,1.5}xATR, max_units=2", pyramid_results)

    # --- Part 2: buffer-safe sizing search for the pyramid version ---
    print("\n\n### PART 2: buffer-safe sizing search for pyramid version ###", flush=True)
    candidates = [400, 300, 250, 200, 150, 125, 100, 75, 50]
    best = find_buffer_safe_risk_pyramid(sig, df1m, SYMBOL, atr15, candidates)
    if best:
        risk, exp, worst_dd, n = best
        required_low, required_high = 767, 1279
        frac_low = exp / required_low * 100
        frac_high = exp / required_high * 100
        print(f"\nPyramid buffer-safe size: risk=${risk}/trade, n={n}, exp=${exp:.2f}/trade, "
              f"worst_maxdd=${worst_dd:.2f} (within 70% margin of ${BUFFER:.2f})", flush=True)
        print(f"Compare to Round 20's flat-sizing result: risk=$75/trade, exp=$20.47/trade.", flush=True)
        print(f"This pyramid result closes {frac_low:.1f}%-{frac_high:.1f}% of the $767-1,279/trade "
              f"required pace.", flush=True)
    else:
        print("No pyramid risk level found whose worst-fold maxdd clears the buffer-safe target.", flush=True)

    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
