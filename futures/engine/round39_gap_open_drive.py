"""
Round 39: Overnight-gap / opening-drive CONTINUATION -- a price-gap-triggered entry,
genuinely different from every entry family tried in Rounds 1-38 (random timing,
swing-touch S/R bounce, FVG+bias, ORB, ADX-regime, GEX zones, liquidity sweeps, VWAP,
session breakouts, trend-following). See docs/EDGE_VALIDATION_RESULTS.md's running
total before assuming this is untested ground -- it is not, this is the first round to
test it.

Hypothesis: measure the gap between a session's OWN open print and the PRIOR session's
close. If the gap exceeds some threshold (in ATR units, train-only selected per fold),
trade IN THE DIRECTION of the gap (long a gap-up, short a gap-down) -- an "opening
drive continuation" bet, the opposite hypothesis from a gap-fade/mean-reversion play.

Exit: the SAME validated ATR-trailing mechanics this campaign already uses --
`resolve_trailing_sequential` (round30b_sequential_fix.py, itself built on
`resolve_trailing`'s mechanics from round19_random_entry.py) -- imported and called
unchanged, not reimplemented. Initial stop = 1.0x causal 15m ATR(14) (round19's
STOP_ATR_MULT), trail = 1.5x that initial distance (round19's TRAIL_ATR_MULT). No
fixed target. max_hold_bars stays at the shared default (390 = one RTH session's worth
of 1m bars), the same simplification round11/19/30b already use for BOTH instruments
(including MGC, despite its near-24h data -- this round does not invent a new exit
convention).

SESSION DEFINITION (the thing this round has to define that prior rounds didn't need):
  - MNQ_CONTINUOUS.txt is already RTH-only (1m bars from 09:30:00 to ~16:00:00 local
    exchange time, confirmed directly against the raw file: 950/963 calendar days
    start exactly at 09:30:00). So "session" = calendar trading day; session open =
    the OPEN of that day's first 1m bar; session close = the CLOSE of that day's last
    1m bar.
  - MGC_CONTINUOUS.txt is near-24h. Confirmed directly against the raw file: bar
    density collapses to ~30% of normal during the hour-of-day bucket 21:00-22:00 UTC
    on the majority of days and 22:00-23:00 UTC on the rest -- a daily ~61-minute gap
    (698 occurrences of an exact 61.0-minute inter-bar gap) whose UTC hour shifts
    between 21 and 22 across the year. That is exactly what CME's real 5:00-6:00pm ET
    daily metals maintenance break looks like once converted to a FIXED-OFFSET (UTC)
    timestamp: 17:00 ET is 21:00 UTC in EDT and 22:00 UTC in EST, so a genuine
    fixed-local-time daily break shows up at a shifting UTC clock hour -- confirming
    (a) these timestamps are UTC (not DST-adjusted local time, unlike MNQ's file) and
    (b) the low-density hour is a real exchange session boundary, not a data artifact.
    Rather than hardcode a single clock time that would be wrong for half the year,
    sessions are detected DIRECTLY from the data: any inter-bar gap >= 30 minutes ends
    a session (this single threshold cleanly separates the ~61min daily breaks and the
    ~2941min weekly weekend gap from ordinary quiet-market minutes -- gaps below 30min
    are rare in the data and never longer than ~20min, gaps above 30min cluster tightly
    at ~55-65min or ~2900+min, see the exploratory check this file's author ran before
    writing this). This is itself a real, data-driven session boundary, not a random
    round-number clock-time guess.

LOOK-AHEAD CHECK (explicit, per the task's requirement):
  - The gap signal uses ONLY: (a) the prior session's CLOSE price (fully known once
    that session ended, long before the next session opens), and (b) the current
    session's OWN OPEN price -- which by construction is known the instant the
    session's first bar begins printing, i.e. AT that bar's open, not before it and
    not from any future bar.
  - The strategy does not enter at that instantaneous open print. It enters at the
    CLOSE of that same first bar (one full minute later) using that bar's own close
    as the fill price -- a deliberately conservative extra buffer against claiming an
    unrealistic fill at the exact print used to compute the signal. `entry.ts` passed
    to resolve_trailing_sequential is that first bar's own timestamp; because
    resolve_trailing_sequential's internal `np.searchsorted(ts, entry.ts, side="right")`
    finds the position strictly AFTER that bar, the trailing-stop simulation itself
    only ever walks bars AFTER the entry bar -- identical convention to every prior
    round in this campaign, so the entry bar's own high/low can never be used against
    itself for the exit either.
  - The initial-stop ATR and the gap-size-in-ATR-units threshold both use
    `causal_atr15_lookup` + `attach_atr` (round19_random_entry.py, unmodified): the
    most recently CLOSED 15m bar strictly before the entry timestamp. Never same-bar,
    never future.

Walk-forward: the SAME FOLDS as every other round (round11_fvg_bias.FOLDS, expanding
window, 6 OOS windows). Per fold, the gap-size-in-ATR-units threshold is grid-searched
on TRAIN data only (signals with ts < the fold's train_end) by training-period mean
pnl at that risk level, then applied UNCHANGED to that fold's OOS test period -- same
train/test discipline as round11's walk_forward and round19/30b's per-fold selection.
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from round11_fvg_bias import (
    load_1m, resample_causal, POINT_VALUE, TICK_SIZE, COMMISSION_RT, BUFFER, FOLDS,
)
from round19_random_entry import causal_atr15_lookup, attach_atr, resolve_trailing, STOP_ATR_MULT, TRAIL_ATR_MULT
from round30b_sequential_fix import resolve_trailing_sequential

THRESH_GRID = [0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 3.00]
RISK_LEVELS = (200, 300, 400, 500, 600, 800, 1000)
MIN_TRAIN_TRADES = 10
MGC_SESSION_GAP_MIN = 30  # minutes; see module docstring for how this was chosen


# ---------------------------------------------------------------------------
# Session construction
# ---------------------------------------------------------------------------

def build_rth_sessions(df1m):
    """MNQ: one session per calendar trading day. open = first bar's OPEN (the real
    print the gap is measured against); open_bar_close = that SAME first bar's CLOSE
    (the actual fill price used for entry, one minute after the open print -- see
    module docstring's look-ahead section); close = last bar's CLOSE."""
    dates = pd.Series(df1m.index.date, index=df1m.index)
    rows = []
    for day, day_idx in df1m.groupby(dates).groups.items():
        if len(day_idx) < 30:
            continue
        first_ts, last_ts = day_idx[0], day_idx[-1]
        rows.append((first_ts, df1m.loc[first_ts, "open"], df1m.loc[first_ts, "close"],
                     last_ts, df1m.loc[last_ts, "close"]))
    sess = pd.DataFrame(rows, columns=["open_ts", "open_price", "open_bar_close", "close_ts", "close_price"])
    return sess.sort_values("open_ts").reset_index(drop=True)


def build_gap_detected_sessions(df1m, gap_minutes=MGC_SESSION_GAP_MIN):
    """MGC: sessions detected directly from the data's own inter-bar gaps (see module
    docstring). A new session starts at any bar preceded by a gap >= gap_minutes (or
    the very first bar in the file)."""
    idx = df1m.index
    diffs = idx.to_series().diff().dt.total_seconds().values / 60.0
    is_new = np.ones(len(df1m), dtype=bool)
    is_new[1:] = diffs[1:] >= gap_minutes
    sid = np.cumsum(is_new) - 1
    d = df1m.copy()
    d["sid"] = sid
    d["ts_col"] = d.index
    first = d.groupby("sid").first()
    last = d.groupby("sid").last()
    sess = pd.DataFrame({
        "open_ts": first["ts_col"].values,
        "open_price": first["open"].values,
        "open_bar_close": first["close"].values,
        "close_ts": last["ts_col"].values,
        "close_price": last["close"].values,
    })
    # drop degenerate fragment sessions (data glitches shorter than 5 minutes)
    span_min = (sess["close_ts"] - sess["open_ts"]).dt.total_seconds() / 60.0
    sess = sess[span_min >= 5]
    return sess.sort_values("open_ts").reset_index(drop=True)


def compute_gaps(sess):
    sess = sess.copy()
    sess["prev_close"] = sess["close_price"].shift(1)
    sess = sess.dropna(subset=["prev_close"]).reset_index(drop=True)
    sess["gap"] = sess["open_price"] - sess["prev_close"]
    return sess


def build_gap_signals(sess, atr_series):
    """sess (with 'gap' already computed) -> signal rows shaped exactly like every
    other round's (ts, direction, entry, stop), plus gap/gap_atr for threshold
    filtering. direction = sign(gap): trading WITH the gap (continuation), never
    against it, per the task's specific direction."""
    tmp = sess.rename(columns={"open_ts": "ts"})
    tmp = attach_atr(tmp, atr_series)  # causal: most recently CLOSED 15m bar before ts
    tmp = tmp[tmp["atr"] > 0].copy()
    tmp["gap_atr"] = tmp["gap"].abs() / tmp["atr"]
    tmp["direction"] = np.sign(tmp["gap"]).astype(int)
    tmp = tmp[tmp["direction"] != 0].copy()
    stop_dist = STOP_ATR_MULT * tmp["atr"]
    tmp["entry"] = tmp["open_bar_close"]  # fill = close of the session's own opening bar
    tmp["stop"] = np.where(tmp["direction"] == 1, tmp["entry"] - stop_dist, tmp["entry"] + stop_dist)
    return tmp[["ts", "direction", "entry", "stop", "gap", "gap_atr"]].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Walk-forward with train-only threshold selection
# ---------------------------------------------------------------------------

def walk_forward_gap(sig_all, df1m, symbol, risk, thresh_grid=THRESH_GRID, min_train_trades=MIN_TRAIN_TRADES):
    """Per FOLDS window: grid-search gap_atr threshold on TRAIN-only signals (by mean
    training-period pnl at this risk level), then apply that SAME threshold unchanged
    to the fold's OOS test signals. Exit = resolve_trailing_sequential, unmodified."""
    fold_rows = []
    for train_end, test_end in FOLDS:
        train_sig = sig_all[sig_all["ts"] < train_end]
        test_sig = sig_all[(sig_all["ts"] >= train_end) & (sig_all["ts"] < test_end)]
        if len(test_sig) == 0:
            fold_rows.append(dict(train_end=train_end, test_end=test_end, threshold=None, trades=None, skipped=0))
            continue
        best_th, best_exp = None, -1e18
        for th in thresh_grid:
            tr_f = train_sig[train_sig["gap_atr"] >= th]
            if len(tr_f) < min_train_trades:
                continue
            tr, _ = resolve_trailing_sequential(tr_f, df1m, symbol, risk, TRAIL_ATR_MULT)
            if len(tr) == 0:
                continue
            exp = tr["pnl"].mean()
            if exp > best_exp:
                best_exp, best_th = exp, th
        if best_th is None:
            fold_rows.append(dict(train_end=train_end, test_end=test_end, threshold=None, trades=None, skipped=0))
            continue
        te_f = test_sig[test_sig["gap_atr"] >= best_th]
        te, skipped = resolve_trailing_sequential(te_f, df1m, symbol, risk, TRAIL_ATR_MULT)
        fold_rows.append(dict(train_end=train_end, test_end=test_end, threshold=best_th, trades=te, skipped=skipped))
    return fold_rows


def fold_summary(fold_rows):
    rows = []
    for f in fold_rows:
        te = f["trades"]
        if te is None or len(te) == 0:
            rows.append(dict(train_end=f["train_end"], test_end=f["test_end"], threshold=f["threshold"],
                              n=0, exp=np.nan, total=0.0, winrate=np.nan, maxdd=0.0, breach=False))
            continue
        pnl = te["pnl"]
        equity = pnl.cumsum()
        maxdd = (equity.cummax() - equity).max()
        rows.append(dict(train_end=f["train_end"], test_end=f["test_end"], threshold=f["threshold"],
                          n=len(te), exp=pnl.mean(), total=pnl.sum(), winrate=(pnl > 0).mean(),
                          maxdd=maxdd, breach=bool(maxdd > BUFFER)))
    return pd.DataFrame(rows)


def one_sample_tstat(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 2:
        return 0.0
    sd = x.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(x.mean() / (sd / np.sqrt(n)))


def pooled_stats(fold_rows):
    trades = [f["trades"] for f in fold_rows if f["trades"] is not None and len(f["trades"]) > 0]
    if not trades:
        return dict(n=0, exp=0.0, total=0.0, tstat=0.0, winrate=np.nan)
    pooled = pd.concat(trades, ignore_index=True)
    return dict(n=len(pooled), exp=pooled["pnl"].mean(), total=pooled["pnl"].sum(),
                tstat=one_sample_tstat(pooled["pnl"].values), winrate=(pooled["pnl"] > 0).mean())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_symbol(symbol, path, session_builder):
    print(f"\n{'='*78}\n{symbol}: loading {path}", flush=True)
    df1m = load_1m(path)
    print(f"{symbol}: {len(df1m)} 1m bars, {df1m.index.min()} -> {df1m.index.max()}", flush=True)
    atr15 = causal_atr15_lookup(df1m)

    sess = session_builder(df1m)
    print(f"{symbol}: {len(sess)} sessions detected", flush=True)
    sess = compute_gaps(sess)
    sig_all = build_gap_signals(sess, atr15)
    print(f"{symbol}: {len(sig_all)} gap signals with valid causal ATR "
          f"(median |gap| in ATR units = {sig_all['gap_atr'].median():.2f})", flush=True)

    # quick diagnostic, both directions unfiltered (threshold=0), NOT the reported
    # headline -- just a sanity gut-check on raw continuation tendency before any
    # threshold optimization, and a cross-check that resolve_trailing (non-sequential,
    # round19) and resolve_trailing_sequential (round30b) agree when signals can't
    # overlap by construction (one signal per session, sessions don't overlap in time).
    diag_seq, diag_skipped = resolve_trailing_sequential(sig_all, df1m, symbol, 400, TRAIL_ATR_MULT)
    diag_plain = resolve_trailing(sig_all, df1m, symbol, 400, TRAIL_ATR_MULT)
    print(f"{symbol}: diagnostic unfiltered/unselected @ $400 risk -- sequential n={len(diag_seq)} "
          f"exp=${diag_seq['pnl'].mean():.2f} (skipped_overlap={diag_skipped}) | "
          f"non-sequential n={len(diag_plain)} exp=${diag_plain['pnl'].mean():.2f} "
          f"(should match: sessions cannot overlap by construction)", flush=True)

    per_risk = {}
    for risk in RISK_LEVELS:
        fold_rows = walk_forward_gap(sig_all, df1m, symbol, risk)
        fs = fold_summary(fold_rows)
        pooled = pooled_stats(fold_rows)
        per_risk[risk] = dict(fold_rows=fold_rows, fold_summary=fs, pooled=pooled)
        print(f"\n--- {symbol} risk=${risk} ---", flush=True)
        for _, r in fs.iterrows():
            print(f"  {r['train_end']}->{r['test_end']} thresh={r['threshold']} n={r['n']} "
                  f"win%={r['winrate']:.1%} exp=${r['exp']:.2f} total=${r['total']:.2f} "
                  f"maxdd=${r['maxdd']:.2f} breach={r['breach']}" if r['n'] > 0 else
                  f"  {r['train_end']}->{r['test_end']}: no OOS trades (thresh={r['threshold']})", flush=True)
        print(f"  POOLED OOS: n={pooled['n']} exp=${pooled['exp']:.2f} total=${pooled['total']:.2f} "
              f"t-stat={pooled['tstat']:.2f} win%={pooled['winrate']:.1%} "
              f"worst_fold_maxdd=${fs['maxdd'].max():.2f} folds_breaching={int(fs['breach'].sum())}/{len(fs)}",
              flush=True)

    return sig_all, per_risk


def buffer_safe_sweep(symbol, sig_all, df1m, risk_grid):
    """Finer risk sweep, same walk_forward_gap machinery (own train-only threshold
    selection at each risk level, not reused from a single benchmark risk), used only
    to find the largest risk/trade keeping every fold's OOS max drawdown under BUFFER."""
    rows = []
    for risk in risk_grid:
        fold_rows = walk_forward_gap(sig_all, df1m, symbol, risk)
        fs = fold_summary(fold_rows)
        pooled = pooled_stats(fold_rows)
        worst_dd = fs["maxdd"].max() if len(fs) else 0.0
        rows.append(dict(risk=risk, worst_fold_maxdd=worst_dd, breach=bool(worst_dd > BUFFER),
                          pooled_exp=pooled["exp"], pooled_n=pooled["n"], pooled_tstat=pooled["tstat"]))
        print(f"  sweep {symbol} risk=${risk}: worst_fold_maxdd=${worst_dd:.2f} breach={worst_dd > BUFFER} "
              f"pooled_exp=${pooled['exp']:.2f} pooled_n={pooled['n']} t={pooled['tstat']:.2f}", flush=True)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    engine_dir = os.path.dirname(__file__)
    data_dir = os.path.join(engine_dir, "..", "data")

    mnq_sig, mnq_results = run_symbol("MNQ", os.path.join(data_dir, "MNQ_CONTINUOUS.txt"), build_rth_sessions)
    mgc_sig, mgc_results = run_symbol("MGC", os.path.join(data_dir, "MGC_CONTINUOUS.txt"), build_gap_detected_sessions)

    print(f"\n\n{'#'*78}\nBUFFER-SAFE SIZING SWEEP (only meaningful if an OOS edge was found above)\n{'#'*78}", flush=True)
    mnq_df1m = load_1m(os.path.join(data_dir, "MNQ_CONTINUOUS.txt"))
    mgc_df1m = load_1m(os.path.join(data_dir, "MGC_CONTINUOUS.txt"))
    fine_grid = list(range(50, 2001, 50))

    print("\nMNQ sweep:", flush=True)
    mnq_sweep = buffer_safe_sweep("MNQ", mnq_sig, mnq_df1m, fine_grid)
    mnq_sweep.to_csv(os.path.join(engine_dir, "round39_mnq_sweep.csv"), index=False)

    print("\nMGC sweep:", flush=True)
    mgc_sweep = buffer_safe_sweep("MGC", mgc_sig, mgc_df1m, fine_grid)
    mgc_sweep.to_csv(os.path.join(engine_dir, "round39_mgc_sweep.csv"), index=False)

    for symbol, sweep in [("MNQ", mnq_sweep), ("MGC", mgc_sweep)]:
        safe = sweep[~sweep["breach"]]
        if len(safe) > 0:
            best = safe.loc[safe["risk"].idxmax()]
            print(f"\n{symbol}: largest buffer-safe risk/trade = ${best['risk']:.0f} "
                  f"(worst_fold_maxdd=${best['worst_fold_maxdd']:.2f}, pooled_exp=${best['pooled_exp']:.2f}, "
                  f"pooled_n={best['pooled_n']:.0f}, t={best['pooled_tstat']:.2f})", flush=True)
        else:
            print(f"\n{symbol}: NO risk level in the sweep stays under the buffer.", flush=True)

    print("\nDONE.", flush=True)
