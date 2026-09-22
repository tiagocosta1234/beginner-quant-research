"""
Round 12: Confirmation-candle FVG reaction (vs. Round 11's first-touch baseline) + breakeven
management overlay. Nasdaq (MNQ) only, per the trader's explicit go-ahead ("test it, on the nasdaq").

Hypothesis (from visual review of 819-trade backtesting_journal, logged in TRADING_JOURNAL.md
"full local backtesting_journal review" entry, 2026-09-19): every visually-inspected loss was a
first-touch entry where price sliced straight through the FVG zone with no rejection; every win
showed a full-bodied candle closing back OUTSIDE the zone before the move ran. Round 10 and
Round 11 both entered on first touch. This is the untested piece.

Arms (all MNQ, both 15m and 30m HTF zones, same costs/sizing/folds as Round 11 for comparability):
  A. Baseline, first-touch -- NOT rerun here, reused directly from Round 11's MNQ "unfiltered"
     results (identical zone definition, identical walk-forward, identical costs -- a rerun would
     be pure duplication of already-verified numbers).
  B. Confirmation entry -- after price first touches the zone, wait for the first subsequent 1m
     candle (within a lookahead window) whose body is >=60% of its own range AND whose close is
     outside the zone in the FVG's direction. Entry = that candle's CLOSE (consistent with this
     repo's Round 10 precedent of "entry at CHoCH close"). Stop unchanged: zone's far edge. This
     isolates the entry-trigger change from every other variable.
  C. Confirmation entry (arm B) + breakeven-stop-move once price reaches a fixed favorable
     multiple (0.5R or 1R) of the ORIGINAL stop distance. Requires true bar-by-bar state (the stop
     level itself changes mid-trade), unlike Round 11's vectorized argmax approach.

Built causally throughout: confirmation candle logic only uses that candle's own OHLC once it has
closed; breakeven-trigger check only uses bars already elapsed. Per the standing Round 9c lesson.
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

MIN_BODY_RATIO = 0.60
CONFIRM_LOOKAHEAD_BARS = 60   # 1 hour max to wait for a confirming close after first touch


def first_touch_positions(fvg_df, df1m, max_lookahead_bars=480):
    """Same touch-finding logic as Round 11's first_touch(), but returns the 1m bar
    POSITION (integer index) of the touch, not just price -- needed here so arm B can
    keep scanning forward from that position for a confirmation candle."""
    ts = df1m.index.values
    lo_arr = df1m["low"].values
    hi_arr = df1m["high"].values
    n = len(df1m)
    start_positions = np.searchsorted(ts, fvg_df["confirm_ts"].values, side="right")

    out = []
    for row, start_pos in zip(fvg_df.itertuples(index=False), start_positions):
        if start_pos >= n:
            continue
        end_pos = min(start_pos + max_lookahead_bars, n)
        seg_lo = lo_arr[start_pos:end_pos]
        seg_hi = hi_arr[start_pos:end_pos]
        mask = (seg_lo <= row.zone_hi) & (seg_hi >= row.zone_lo)
        hit = np.argmax(mask) if mask.any() else -1
        if hit == -1:
            continue
        touch_pos = start_pos + hit
        out.append((touch_pos, row.direction, row.zone_lo, row.zone_hi))
    return out


def confirmed_entries(fvg_df, df1m, touch_lookahead=480, confirm_lookahead=CONFIRM_LOOKAHEAD_BARS,
                       min_body_ratio=MIN_BODY_RATIO):
    """Arm B signal generation: touch the zone, then require a full-bodied close back
    OUTSIDE the zone in the FVG's direction within confirm_lookahead bars of the touch.
    Entry = that confirming candle's close. Stop = zone's far edge (unchanged vs arm A)."""
    touches = first_touch_positions(fvg_df, df1m, touch_lookahead)
    if not touches:
        return pd.DataFrame(columns=["ts", "direction", "entry", "stop"])

    ts = df1m.index.values
    o = df1m["open"].values
    h = df1m["high"].values
    l = df1m["low"].values
    c = df1m["close"].values
    n = len(df1m)

    rows = []
    for touch_pos, direction, zone_lo, zone_hi in touches:
        end_pos = min(touch_pos + confirm_lookahead, n)
        found = None
        for i in range(touch_pos, end_pos):
            rng = h[i] - l[i]
            if rng <= 0:
                continue
            body = abs(c[i] - o[i])
            body_ratio = body / rng
            if body_ratio < min_body_ratio:
                continue
            if direction == 1 and c[i] > zone_hi:
                found = i
                break
            if direction == -1 and c[i] < zone_lo:
                found = i
                break
        if found is None:
            continue
        stop = zone_lo if direction == 1 else zone_hi
        rows.append((ts[found], direction, c[found], stop))
    return pd.DataFrame(rows, columns=["ts", "direction", "entry", "stop"])


def resolve_outcomes_plain(sig_df, df1m, symbol, rr, risk_dollar, max_hold_bars=390):
    """Same fixed-R:R, first-touch-of-target-or-stop resolution as Round 11 (no breakeven
    move) -- used for arm B."""
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values
    hi = df1m["high"].values
    lo = df1m["low"].values
    n = len(df1m)
    results = []
    for r in sig_df.itertuples(index=False):
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        stop_dist = abs(r.entry - r.stop)
        if stop_dist <= 0:
            continue
        target_dist = rr * stop_dist
        if r.direction == 1:
            target_px = r.entry + target_dist
            stop_px = r.stop
        else:
            target_px = r.entry - target_dist
            stop_px = r.stop
        end_pos = min(pos + max_hold_bars, n)
        seg_hi = hi[pos:end_pos]
        seg_lo = lo[pos:end_pos]
        if r.direction == 1:
            hit_stop = seg_lo <= stop_px
            hit_target = seg_hi >= target_px
        else:
            hit_stop = seg_hi >= stop_px
            hit_target = seg_lo <= target_px
        first_stop = np.argmax(hit_stop) if hit_stop.any() else n
        first_target = np.argmax(hit_target) if hit_target.any() else n
        contracts = max(1, int(risk_dollar // (stop_dist * pv)))
        commission = COMMISSION_RT * contracts
        if first_stop == n and first_target == n:
            pnl = -commission
            outcome = "timeout"
        elif first_target <= first_stop:
            pnl = target_dist * pv * contracts - commission - slip_dollars_rt * contracts
            outcome = "target"
        else:
            pnl = -stop_dist * pv * contracts - commission - slip_dollars_rt * contracts
            outcome = "stop"
        results.append((r.ts, symbol, r.direction, rr, risk_dollar, contracts, pnl, outcome))
    return pd.DataFrame(results, columns=["ts", "symbol", "direction", "rr", "risk", "contracts",
                                           "pnl", "outcome"])


def resolve_outcomes_be(sig_df, df1m, symbol, rr, risk_dollar, be_trigger_r, max_hold_bars=390):
    """Arm C: true bar-by-bar walk. Original stop moves to breakeven (entry price) the
    first bar where favorable excursion reaches be_trigger_r * original_stop_dist, IF that
    happens before the original stop is hit. Causal: the move only applies to bars AFTER
    the triggering bar's close is known, i.e. we check trigger and stop-hit using the SAME
    bar's high/low (conservative: if a single bar both reaches the BE trigger distance and
    would have hit the pre-move stop, we count it as a stop-out at the ORIGINAL stop, since
    intrabar sequencing within one bar is not knowable -- worst-case/no-lookahead assumption)."""
    pv = POINT_VALUE[symbol]
    tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values
    hi = df1m["high"].values
    lo = df1m["low"].values
    n = len(df1m)
    results = []
    for r in sig_df.itertuples(index=False):
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        stop_dist = abs(r.entry - r.stop)
        if stop_dist <= 0:
            continue
        target_dist = rr * stop_dist
        be_trigger_dist = be_trigger_r * stop_dist
        if r.direction == 1:
            target_px = r.entry + target_dist
            orig_stop_px = r.stop
            be_trigger_px = r.entry + be_trigger_dist
        else:
            target_px = r.entry - target_dist
            orig_stop_px = r.stop
            be_trigger_px = r.entry - be_trigger_dist

        cur_stop_px = orig_stop_px
        moved_to_be = False
        end_pos = min(pos + max_hold_bars, n)
        outcome = "timeout"
        pnl = None
        for i in range(pos, end_pos):
            bar_hi, bar_lo = hi[i], lo[i]
            if r.direction == 1:
                hit_cur_stop = bar_lo <= cur_stop_px
                hit_target = bar_hi >= target_px
                reaches_be_trigger = bar_hi >= be_trigger_px
            else:
                hit_cur_stop = bar_hi >= cur_stop_px
                hit_target = bar_lo <= target_px
                reaches_be_trigger = bar_lo <= be_trigger_px

            if hit_cur_stop and not (reaches_be_trigger and not moved_to_be):
                # stop hit this bar, and either BE wasn't newly triggered this same bar
                # or it was already moved previously -- either way this stop level holds
                exit_dist = stop_dist if not moved_to_be else 0.0
                contracts = max(1, int(risk_dollar // (stop_dist * pv)))
                commission = COMMISSION_RT * contracts
                pnl = -exit_dist * pv * contracts - commission - slip_dollars_rt * contracts
                outcome = "stop" if not moved_to_be else "breakeven"
                break
            if hit_target:
                contracts = max(1, int(risk_dollar // (stop_dist * pv)))
                commission = COMMISSION_RT * contracts
                pnl = target_dist * pv * contracts - commission - slip_dollars_rt * contracts
                outcome = "target"
                break
            if reaches_be_trigger and not moved_to_be:
                moved_to_be = True
                cur_stop_px = r.entry
                # after moving to BE, re-check this same bar against the NEW stop too
                # (conservative causal handling: if the bar's range also breached the new
                # BE stop, exit at BE this bar rather than assume survival)
                if r.direction == 1 and bar_lo <= cur_stop_px:
                    contracts = max(1, int(risk_dollar // (stop_dist * pv)))
                    commission = COMMISSION_RT * contracts
                    pnl = 0.0 - commission - slip_dollars_rt * contracts
                    outcome = "breakeven"
                    break
                if r.direction == -1 and bar_hi >= cur_stop_px:
                    contracts = max(1, int(risk_dollar // (stop_dist * pv)))
                    commission = COMMISSION_RT * contracts
                    pnl = 0.0 - commission - slip_dollars_rt * contracts
                    outcome = "breakeven"
                    break
        if pnl is None:
            contracts = max(1, int(risk_dollar // (stop_dist * pv)))
            commission = COMMISSION_RT * contracts
            pnl = -commission
            outcome = "timeout"
        results.append((r.ts, symbol, r.direction, rr, risk_dollar, contracts, pnl, outcome))
    return pd.DataFrame(results, columns=["ts", "symbol", "direction", "rr", "risk", "contracts",
                                           "pnl", "outcome"])


def walk_forward_generic(sig_all, df1m, symbol, resolve_fn, resolve_kwargs,
                          rr_grid=(1.5, 2.0), risk_levels=(400, 600)):
    out = {}
    for risk in risk_levels:
        fold_rows = []
        for train_end, test_end in FOLDS:
            train_sig = sig_all[sig_all["ts"] < train_end]
            test_sig = sig_all[(sig_all["ts"] >= train_end) & (sig_all["ts"] < test_end)]
            if len(train_sig) < 20 or len(test_sig) == 0:
                fold_rows.append((train_end, test_end, None, None))
                continue
            best_rr, best_exp = None, -1e18
            for rr in rr_grid:
                tr = resolve_fn(train_sig, df1m, symbol, rr, risk, **resolve_kwargs)
                if len(tr) == 0:
                    continue
                exp = tr["pnl"].mean()
                if exp > best_exp:
                    best_exp, best_rr = exp, rr
            if best_rr is None:
                fold_rows.append((train_end, test_end, None, None))
                continue
            te = resolve_fn(test_sig, df1m, symbol, best_rr, risk, **resolve_kwargs)
            fold_rows.append((train_end, test_end, best_rr, te))
        out[risk] = fold_rows
    return out


def print_results(label, res):
    for risk, fold_rows in res.items():
        print(f"-- {label} risk=${risk} --", flush=True)
        all_trades = []
        for train_end, test_end, rr, te in fold_rows:
            if te is None:
                print(f"  {train_end}->{test_end}: no signals", flush=True)
                continue
            st = fold_stats(te)
            print(f"  {train_end}->{test_end} rr={rr} n={st['n']} win%={st['winrate']:.1%} "
                  f"exp=${st['expectancy']:.2f} total=${st['total']:.2f} maxdd=${st['maxdd']:.2f} "
                  f"breach={st['breach']}", flush=True)
            all_trades.append(te)
        if all_trades:
            combo = pd.concat(all_trades, ignore_index=True)
            tc10 = tail_concentration(combo, 10)
            tc20 = tail_concentration(combo, 20)
            print(f"  AGGREGATE n={len(combo)} total=${combo['pnl'].sum():.2f} "
                  f"exp=${combo['pnl'].mean():.2f} win%={(combo['pnl']>0).mean():.1%} "
                  f"tail10={tc10} tail20={tc20}", flush=True)


if __name__ == "__main__":
    symbol = "MNQ"
    path = sys.argv[1] if len(sys.argv) > 1 else "../data/MNQ_CONTINUOUS.txt"
    print(f"Loading {symbol} from {path} ...", flush=True)
    df1m = load_1m(path)
    print(f"{symbol}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)

    for htf_rule, htf_name in [("15min", "15m"), ("30min", "30m")]:
        htf = resample_causal(df1m, htf_rule)
        fvgs = detect_fvgs(htf)
        print(f"\n### {symbol} HTF={htf_name}: {len(fvgs)} FVGs detected ###", flush=True)

        sig_b = confirmed_entries(fvgs, df1m)
        sig_b = one_per_day(sig_b)
        print(f"Arm B (confirmation) signal count after 1/day cap: {len(sig_b)}", flush=True)

        res_b = walk_forward_generic(sig_b, df1m, symbol, resolve_outcomes_plain, {})
        print_results(f"ARM B confirmation HTF={htf_name}", res_b)

        for be_r in (0.5, 1.0):
            res_c = walk_forward_generic(sig_b, df1m, symbol, resolve_outcomes_be, {"be_trigger_r": be_r})
            print_results(f"ARM C confirmation+BE({be_r}R) HTF={htf_name}", res_c)
