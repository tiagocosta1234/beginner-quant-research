"""
Round 13: refinements to Round 12's confirmation-candle FVG entry. MNQ (Nasdaq) only,
per the trader's "keep pushing on it" instruction following Round 12.

Round 12 found: confirmation-candle entry (wait for a full-bodied close back outside
the zone before entering) beats first-touch by 20-45% smaller average loss, but never
flips positive; a breakeven-management overlay didn't reliably help further.

This round tests three specific, mechanically-motivated refinements on top of that:

Refinement 1 - tighter stop: use the confirmation candle's own extreme (low for a
long, high for a short) instead of the zone's far edge inherited from the first-touch
baseline. A confirmation entry by construction only fires after price has already
moved away from the zone, so the zone edge is a looser stop than necessary. A minimum
stop-distance floor (4 ticks = 1.0pt for MNQ) is applied to avoid degenerate,
noise-level candle ranges producing unrealistic position sizing -- documented here
explicitly rather than left as a silent edge case.

Refinement 2 - confirmation strictness grid: Round 12 fixed min_body_ratio=0.60 and
required the close strictly beyond the zone edge (beyond_frac=0.0). Grid-searched here
(train-only per fold, applied unchanged OOS, same discipline as the R:R grid in every
prior round) across body_ratio in {0.5, 0.6, 0.75} x beyond_frac in {0.0, 0.15, 0.30}
(beyond_frac = required close distance past the zone edge, as a fraction of zone
height). Uses the zone-edge stop (unchanged from Round 12) to isolate the
confirmation-strictness variable from Refinement 1's stop-placement change.

Refinement 3 - 4H gap-reaction context, from the 2026-04-06 journal win note ("used
stdv for this one + 4h gap reaction") -- never tested in any round so far (1-12 used
15m/30m HTF zones only). Causal 4H gap: |4H bar's open - prior 4H bar's close| >
12 ticks (3.0pt for MNQ, an explicit stated threshold). Direction is genuinely
ambiguous from a single note, so both interpretations are tested: FILL (entry
direction opposes the most recently closed 4H gap) and CONTINUATION (entry direction
matches it). Applied as a filter on top of the winning stop/strictness combo from
Refinements 1+2.

Built causally throughout (Round 9c lesson): confirmation-candle and gap
classification logic only ever use bars that have already closed as of the signal.
"""
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, resample_causal, detect_fvgs, POINT_VALUE, TICK_SIZE,
    COMMISSION_RT, BUFFER, FOLDS, one_per_day, fold_stats, tail_concentration,
)
from round12_fvg_confirmation import (
    first_touch_positions, resolve_outcomes_plain, walk_forward_generic, print_results,
)

MIN_STOP_TICKS = {"MNQ": 4}   # floor for tight-stop variant; documented, not silent
GAP_TICKS_MIN = 12            # 4H gap significance threshold (3.0pt for MNQ)


def confirmed_entries_v2(fvg_df, df1m, min_body_ratio, beyond_frac, symbol,
                          touch_lookahead=480, confirm_lookahead=60, tight_stop=False):
    """Generalizes Round 12's confirmed_entries(): configurable body-ratio and
    beyond-zone-edge strictness, plus an optional tight (confirmation-candle-extreme)
    stop instead of the zone-edge stop."""
    touches = first_touch_positions(fvg_df, df1m, touch_lookahead)
    if not touches:
        return pd.DataFrame(columns=["ts", "direction", "entry", "stop"])

    ts = df1m.index.values
    o = df1m["open"].values
    h = df1m["high"].values
    l = df1m["low"].values
    c = df1m["close"].values
    n = len(df1m)
    tick = TICK_SIZE[symbol]
    min_stop_dist = MIN_STOP_TICKS[symbol] * tick

    rows = []
    for touch_pos, direction, zone_lo, zone_hi in touches:
        zone_h = zone_hi - zone_lo
        req_dist = beyond_frac * zone_h
        end_pos = min(touch_pos + confirm_lookahead, n)
        found = None
        for i in range(touch_pos, end_pos):
            rng = h[i] - l[i]
            if rng <= 0:
                continue
            body = abs(c[i] - o[i])
            if body / rng < min_body_ratio:
                continue
            if direction == 1 and c[i] > zone_hi + req_dist:
                found = i
                break
            if direction == -1 and c[i] < zone_lo - req_dist:
                found = i
                break
        if found is None:
            continue
        if tight_stop:
            stop = l[found] if direction == 1 else h[found]
            stop_dist = abs(c[found] - stop)
            if stop_dist < min_stop_dist:
                stop = c[found] - direction * min_stop_dist
        else:
            stop = zone_lo if direction == 1 else zone_hi
        rows.append((ts[found], direction, c[found], stop))
    return pd.DataFrame(rows, columns=["ts", "direction", "entry", "stop"])


def walk_forward_strictness_grid(fvg_df, df1m, symbol, body_grid, beyond_grid, rr_grid,
                                  risk_levels, tight_stop=False):
    """Grid-searches (body_ratio, beyond_frac, rr) jointly, train-only selection per
    fold applied unchanged OOS -- same discipline as every prior round's R:R grid,
    extended to the two new confirmation-strictness parameters."""
    sig_cache = {}
    for br in body_grid:
        for bf in beyond_grid:
            sig = confirmed_entries_v2(fvg_df, df1m, br, bf, symbol, tight_stop=tight_stop)
            sig_cache[(br, bf)] = one_per_day(sig)

    out = {}
    for risk in risk_levels:
        fold_rows = []
        for train_end, test_end in FOLDS:
            best_key, best_exp = None, -1e18
            for (br, bf), sig in sig_cache.items():
                train_sig = sig[sig["ts"] < train_end]
                if len(train_sig) < 20:
                    continue
                for rr in rr_grid:
                    tr = resolve_outcomes_plain(train_sig, df1m, symbol, rr, risk)
                    if len(tr) == 0:
                        continue
                    exp = tr["pnl"].mean()
                    if exp > best_exp:
                        best_exp, best_key = exp, (br, bf, rr)
            if best_key is None:
                fold_rows.append((train_end, test_end, None, None))
                continue
            br, bf, rr = best_key
            test_sig = sig_cache[(br, bf)]
            test_sig = test_sig[(test_sig["ts"] >= train_end) & (test_sig["ts"] < test_end)]
            if len(test_sig) == 0:
                fold_rows.append((train_end, test_end, (br, bf, rr), None))
                continue
            te = resolve_outcomes_plain(test_sig, df1m, symbol, rr, risk)
            fold_rows.append((train_end, test_end, (br, bf, rr), te))
        out[risk] = fold_rows
    return out


def print_grid_results(label, res):
    for risk, fold_rows in res.items():
        print(f"-- {label} risk=${risk} --", flush=True)
        all_trades = []
        for train_end, test_end, params, te in fold_rows:
            if te is None:
                print(f"  {train_end}->{test_end}: no signals (params={params})", flush=True)
                continue
            st = fold_stats(te)
            print(f"  {train_end}->{test_end} params(body,beyond,rr)={params} n={st['n']} "
                  f"win%={st['winrate']:.1%} exp=${st['expectancy']:.2f} total=${st['total']:.2f} "
                  f"maxdd=${st['maxdd']:.2f} breach={st['breach']}", flush=True)
            all_trades.append(te)
        if all_trades:
            combo = pd.concat(all_trades, ignore_index=True)
            tc10 = tail_concentration(combo, 10)
            tc20 = tail_concentration(combo, 20)
            print(f"  AGGREGATE n={len(combo)} total=${combo['pnl'].sum():.2f} "
                  f"exp=${combo['pnl'].mean():.2f} win%={(combo['pnl']>0).mean():.1%} "
                  f"tail10={tc10} tail20={tc20}", flush=True)


def gap_direction_series(df1m, symbol, gap_ticks_min=GAP_TICKS_MIN):
    """Causal 4H gap classification: compares each 4H bar's open to the PRIOR 4H bar's
    close (both already known/closed as of the current bar's open). +1 = gapped up,
    -1 = gapped down, 0 = no significant gap."""
    h4 = resample_causal(df1m, "4h")
    prev_close = h4["close"].shift(1)
    gap = h4["open"] - prev_close
    tick = TICK_SIZE[symbol]
    direction = pd.Series(0, index=h4.index)
    direction[gap > gap_ticks_min * tick] = 1
    direction[gap < -gap_ticks_min * tick] = -1
    return direction


def attach_gap(signals, gap_dir):
    gts = gap_dir.index.values
    pos = np.searchsorted(gts, signals["ts"].values, side="right") - 1
    pos = np.clip(pos, 0, len(gap_dir) - 1)
    signals = signals.copy()
    signals["gap"] = gap_dir.values[pos]
    signals.loc[pos < 0, "gap"] = 0
    return signals


if __name__ == "__main__":
    symbol = "MNQ"
    path = sys.argv[1] if len(sys.argv) > 1 else "../data/MNQ_CONTINUOUS.txt"
    print(f"Loading {symbol} from {path} ...", flush=True)
    df1m = load_1m(path)
    print(f"{symbol}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)

    gap_dir = gap_direction_series(df1m, symbol)
    n_gaps = int((gap_dir != 0).sum())
    print(f"4H bars: {len(gap_dir)}, significant gaps (>{GAP_TICKS_MIN} ticks): {n_gaps}", flush=True)

    for htf_rule, htf_name in [("15min", "15m"), ("30min", "30m")]:
        htf = resample_causal(df1m, htf_rule)
        fvgs = detect_fvgs(htf)
        print(f"\n############ {symbol} HTF={htf_name}: {len(fvgs)} FVGs ############", flush=True)

        # ---- Refinement 1: stop placement ablation (Round 12's exact body/beyond params) ----
        print(f"\n=== REFINEMENT 1: stop placement, HTF={htf_name} (body=0.60, beyond=0.0, matches Round 12 Arm B) ===", flush=True)
        sig_zoneedge = one_per_day(confirmed_entries_v2(fvgs, df1m, 0.60, 0.0, symbol, tight_stop=False))
        sig_tight = one_per_day(confirmed_entries_v2(fvgs, df1m, 0.60, 0.0, symbol, tight_stop=True))
        print(f"signal counts: zone-edge={len(sig_zoneedge)} tight-stop={len(sig_tight)}", flush=True)
        res_zoneedge = walk_forward_generic(sig_zoneedge, df1m, symbol, resolve_outcomes_plain, {})
        print_results(f"R1 zone-edge-stop HTF={htf_name}", res_zoneedge)
        res_tight = walk_forward_generic(sig_tight, df1m, symbol, resolve_outcomes_plain, {})
        print_results(f"R1 tight-stop HTF={htf_name}", res_tight)

        # ---- Refinement 2: confirmation strictness grid (zone-edge stop, isolates this variable) ----
        print(f"\n=== REFINEMENT 2: confirmation strictness grid, HTF={htf_name} (zone-edge stop) ===", flush=True)
        res_grid = walk_forward_strictness_grid(
            fvgs, df1m, symbol,
            body_grid=(0.5, 0.6, 0.75), beyond_grid=(0.0, 0.15, 0.30),
            rr_grid=(1.5, 2.0), risk_levels=(400, 600), tight_stop=False,
        )
        print_grid_results(f"R2 strictness-grid HTF={htf_name}", res_grid)

    print("\n\n############ Phase 1/2 complete for both HTFs -- see stdout above for best combo selection ############", flush=True)
