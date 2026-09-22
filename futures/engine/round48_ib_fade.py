"""
Round 48: Initial Balance (IB) fade -- genuinely different mechanic from
everything tried so far. ORB (opening-range BREAKOUT, trading WITH the range
break) was already tried and rejected per docs/EDGE_VALIDATION_RESULTS.md's
running total. This is the opposite: fade a FALSE breakout of the first-hour
range (9:30-10:30 ET for MNQ; session-open+60min for MGC) once price sweeps
outside it and closes back in -- a mean-reversion/trap-reversal mechanic, not
a continuation one, and a different window/definition than tonight's earlier
overnight-gap fade (Round 42).

Methodology: IB = high/low of each session's first 60 minutes (causal --
known in full once minute 60 closes). After that, scan forward bar-by-bar
(train-selected sweep margin, in ATR units, and reclaim window in bars) for
the FIRST sweep-then-reclaim event of the day: price exceeds IB by the margin,
then a later bar within the reclaim window closes back inside IB -- fade in
the reversal direction at that reclaim bar's own close. One trade/day (first
qualifying event, whichever side), same convention as every other round.
Exit: same validated ATR-trailing mechanics (resolve_trailing_sequential),
not a new invalidation-based stop -- keeps this comparable to every other
round's risk profile rather than introducing an unvalidated stop rule.
"""
import os, sys
import datetime as dt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, BUFFER, FOLDS, fold_stats
from round19_random_entry import causal_atr15_lookup, attach_atr, STOP_ATR_MULT, TRAIL_ATR_MULT
from round30b_sequential_fix import resolve_trailing_sequential
from round39_gap_open_drive import build_rth_sessions, build_gap_detected_sessions

MARGIN_GRID = [0.10, 0.25, 0.50, 1.0]   # in ATR units
RECLAIM_BARS_GRID = [5, 15, 30, 60]
RISK_SWEEP = [100, 200, 300, 400, 600]
MIN_TRAIN = 15


def build_ib_fade_signals(df1m, sess, atr15, margin_atr, reclaim_bars, ib_minutes=60):
    ts_all = df1m.index.values
    hi_all = df1m["high"].values
    lo_all = df1m["low"].values
    cl_all = df1m["close"].values
    rows = []
    for r in sess.itertuples(index=False):
        start_pos = np.searchsorted(ts_all, np.datetime64(r.open_ts), side="left")
        ib_end_ts = np.datetime64(r.open_ts) + np.timedelta64(ib_minutes, "m")
        ib_end_pos = np.searchsorted(ts_all, ib_end_ts, side="left")
        sess_end_pos = np.searchsorted(ts_all, np.datetime64(r.close_ts), side="right")
        if ib_end_pos <= start_pos or ib_end_pos >= sess_end_pos:
            continue
        ib_hi = hi_all[start_pos:ib_end_pos].max()
        ib_lo = lo_all[start_pos:ib_end_pos].min()
        a = None
        pos = np.searchsorted(atr15.index.values, ts_all[ib_end_pos], side="right") - 1
        if pos < 0:
            continue
        a = atr15.values[pos]
        if not a or a <= 0:
            continue
        margin = margin_atr * a
        found = False
        for j in range(ib_end_pos, sess_end_pos):
            if found:
                break
            if hi_all[j] >= ib_hi + margin:
                for k in range(j + 1, min(j + 1 + reclaim_bars, sess_end_pos)):
                    if cl_all[k] < ib_hi:
                        rows.append((ts_all[k], -1, cl_all[k]))
                        found = True
                        break
                if found:
                    break
            if lo_all[j] <= ib_lo - margin:
                for k in range(j + 1, min(j + 1 + reclaim_bars, sess_end_pos)):
                    if cl_all[k] > ib_lo:
                        rows.append((ts_all[k], 1, cl_all[k]))
                        found = True
                        break
                if found:
                    break
    sig = pd.DataFrame(rows, columns=["ts", "direction", "entry"]).sort_values("ts").reset_index(drop=True)
    if len(sig) == 0:
        return sig
    sig = attach_atr(sig, atr15)
    sig = sig[sig["atr"] > 0].copy()
    stop_dist = STOP_ATR_MULT * sig["atr"]
    sig["stop"] = np.where(sig["direction"] == 1, sig["entry"] - stop_dist, sig["entry"] + stop_dist)
    return sig[["ts", "direction", "entry", "stop"]].reset_index(drop=True)


def run_symbol(symbol, df1m, sess, atr15):
    print(f"\n{'='*78}\n{symbol} IB fade\n{'='*78}", flush=True)
    all_oos = []
    chosen_log = []
    for train_end, test_end in FOLDS:
        best = None
        for margin in MARGIN_GRID:
            for rb in RECLAIM_BARS_GRID:
                sig = build_ib_fade_signals(df1m, sess[sess["open_ts"] < train_end], atr15, margin, rb)
                if len(sig) < MIN_TRAIN:
                    continue
                tr, _ = resolve_trailing_sequential(sig, df1m, symbol, 300, TRAIL_ATR_MULT)
                if len(tr) < MIN_TRAIN:
                    continue
                exp = tr["pnl"].mean()
                if best is None or exp > best[0]:
                    best = (exp, margin, rb, len(tr))
        if best is None:
            continue
        exp, margin, rb, ntrain = best
        chosen_log.append((train_end, margin, rb, exp, ntrain))
        test_sess = sess[(sess["open_ts"] >= train_end) & (sess["open_ts"] < test_end)]
        test_sig = build_ib_fade_signals(df1m, test_sess, atr15, margin, rb)
        if len(test_sig) == 0:
            continue
        te, _ = resolve_trailing_sequential(test_sig, df1m, symbol, 300, TRAIL_ATR_MULT)
        if len(te) > 0:
            all_oos.append(te)

    print("Selected (margin_atr, reclaim_bars), train-only:", flush=True)
    for te, m, rb, exp, n in chosen_log:
        print(f"  {te}: margin={m} reclaim_bars={rb} (train_exp=${exp:.2f}, n={n})", flush=True)

    if not all_oos:
        print(f"{symbol}: no OOS trades.", flush=True)
        return None
    pooled = pd.concat(all_oos, ignore_index=True)
    t_stat, p_val = stats.ttest_1samp(pooled["pnl"].values, popmean=0.0)
    print(f"\n{symbol} OOS @ $300 risk: n={len(pooled)} exp=${pooled['pnl'].mean():.2f} "
          f"t={t_stat:.2f} p={p_val:.2e}", flush=True)

    # risk sweep using the SAME selection already made (avoid re-selecting per risk level
    # -- the setup itself, not its dollar sizing, is what's being screened here)
    print(f"\n{symbol} risk sweep (same selected setup per fold):", flush=True)
    for risk in RISK_SWEEP:
        oos_r = []
        for te, m, rb, _, _ in chosen_log:
            test_end = [f[1] for f in FOLDS if f[0] == te][0]
            test_sess = sess[(sess["open_ts"] >= te) & (sess["open_ts"] < test_end)]
            test_sig = build_ib_fade_signals(df1m, test_sess, atr15, m, rb)
            if len(test_sig) == 0:
                continue
            tr, _ = resolve_trailing_sequential(test_sig, df1m, symbol, risk, TRAIL_ATR_MULT)
            if len(tr) > 0:
                oos_r.append(tr)
        if not oos_r:
            continue
        pooled_r = pd.concat(oos_r, ignore_index=True)
        worst_dd = max(fold_stats(t)["maxdd"] for t in oos_r)
        n_breach = sum(1 for t in oos_r if fold_stats(t)["breach"])
        t_r, p_r = stats.ttest_1samp(pooled_r["pnl"].values, popmean=0.0)
        print(f"  risk=${risk}: n={len(pooled_r)} exp=${pooled_r['pnl'].mean():.2f} t={t_r:.2f} "
              f"worst_dd=${worst_dd:.2f} breach={n_breach}/{len(oos_r)}", flush=True)
    return pooled


if __name__ == "__main__":
    mnq_1m = load_1m(os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
    mnq_atr = causal_atr15_lookup(mnq_1m)
    mnq_sess = build_rth_sessions(mnq_1m)
    run_symbol("MNQ", mnq_1m, mnq_sess, mnq_atr)

    mgc_1m = load_1m(os.path.join("..", "data", "MGC_CONTINUOUS.txt"))
    mgc_atr = causal_atr15_lookup(mgc_1m)
    mgc_sess = build_gap_detected_sessions(mgc_1m)
    run_symbol("MGC", mgc_1m, mgc_sess, mgc_atr)

    print("\nDONE.", flush=True)
