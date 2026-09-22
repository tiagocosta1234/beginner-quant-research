"""
Round 45: cross-instrument lead-lag -- genuinely different mechanism class from
everything else tried in this repo (checked docs/EDGE_VALIDATION_RESULTS.md's
running total: every prior round trades ONE instrument off its OWN price
history; MNQ and MGC have only ever been combined for portfolio risk sizing,
never used as a SIGNAL for each other). Hypothesis: does one instrument's
session return predict the OTHER instrument's next session direction (either
continuation -- risk-on/risk-off correlation -- or reversal -- safe-haven flow
out of one into the other)? Both directions and both lead instruments are
tested; train-only selection per fold picks whichever (if any) has positive
train expectancy, applied unchanged to OOS. Exit: same validated ATR-trailing
mechanics (resolve_trailing_sequential), no fixed target.

LOOK-AHEAD: the predictor is instrument A's CLOSED session return (fully known
once that session ends); the entry is instrument B's NEXT session strictly
after A's session closed, filled at that session's own first-bar close (same
conservative one-bar-late convention as Round 39's gap study). Zero use of
target-instrument price data before entry.
"""
import os, sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, BUFFER, FOLDS, fold_stats
from round19_random_entry import causal_atr15_lookup, attach_atr, STOP_ATR_MULT, TRAIL_ATR_MULT
from round30b_sequential_fix import resolve_trailing_sequential
from round39_gap_open_drive import build_rth_sessions, build_gap_detected_sessions

RISK_SWEEP = [100, 200, 300, 400, 600, 800]
MIN_TRAIN = 20


def build_predictor_signals(lead_sess, lag_sess, lag_atr, invert):
    """For each lead session (fully closed), find the FIRST lag-instrument session
    whose open_ts is strictly after the lead session's close_ts. direction = sign of
    lead session's own return (or flipped if invert). Entry = that lag session's own
    first-bar close; stop = STOP_ATR_MULT * causal ATR at entry."""
    lead_sess = lead_sess.copy()
    lead_sess["ret"] = lead_sess["close_price"] - lead_sess["open_price"]
    lag_open = lag_sess["open_ts"].values
    rows = []
    for r in lead_sess.itertuples(index=False):
        if r.ret == 0:
            continue
        pos = np.searchsorted(lag_open, np.datetime64(r.close_ts), side="right")
        if pos >= len(lag_sess):
            continue
        target = lag_sess.iloc[pos]
        direction = int(np.sign(r.ret))
        if invert:
            direction = -direction
        rows.append((target["open_ts"], direction, target["open_bar_close"]))
    sig = pd.DataFrame(rows, columns=["ts", "direction", "entry"]).sort_values("ts").reset_index(drop=True)
    sig = attach_atr(sig, lag_atr)
    sig = sig[sig["atr"] > 0].copy()
    stop_dist = STOP_ATR_MULT * sig["atr"]
    sig["stop"] = np.where(sig["direction"] == 1, sig["entry"] - stop_dist, sig["entry"] + stop_dist)
    return sig[["ts", "direction", "entry", "stop"]].reset_index(drop=True)


def walk_forward(sig_all, df1m, symbol, risk):
    fold_rows = []
    for train_end, test_end in FOLDS:
        train_sig = sig_all[sig_all["ts"] < train_end]
        test_sig = sig_all[(sig_all["ts"] >= train_end) & (sig_all["ts"] < test_end)]
        if len(train_sig) < MIN_TRAIN or len(test_sig) == 0:
            continue
        tr, _ = resolve_trailing_sequential(train_sig, df1m, symbol, risk, TRAIL_ATR_MULT)
        if len(tr) < MIN_TRAIN:
            continue
        if tr["pnl"].mean() <= 0:
            continue  # train-selected: only trade this config OOS if train itself was positive
        te, _ = resolve_trailing_sequential(test_sig, df1m, symbol, risk, TRAIL_ATR_MULT)
        if len(te) > 0:
            fold_rows.append(te)
    return fold_rows


if __name__ == "__main__":
    print("Loading data...", flush=True)
    mnq_1m = load_1m(os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
    mgc_1m = load_1m(os.path.join("..", "data", "MGC_CONTINUOUS.txt"))
    mnq_atr = causal_atr15_lookup(mnq_1m)
    mgc_atr = causal_atr15_lookup(mgc_1m)
    mnq_sess = build_rth_sessions(mnq_1m)
    mgc_sess = build_gap_detected_sessions(mgc_1m)
    print(f"MNQ sessions: {len(mnq_sess)}, MGC sessions: {len(mgc_sess)}", flush=True)

    configs = [
        ("MNQ_leads_MGC_continuation", mnq_sess, mgc_sess, mgc_atr, mgc_1m, "MGC", False),
        ("MNQ_leads_MGC_reversal", mnq_sess, mgc_sess, mgc_atr, mgc_1m, "MGC", True),
        ("MGC_leads_MNQ_continuation", mgc_sess, mnq_sess, mnq_atr, mnq_1m, "MNQ", False),
        ("MGC_leads_MNQ_reversal", mgc_sess, mnq_sess, mnq_atr, mnq_1m, "MNQ", True),
    ]

    for name, lead, lag, lag_atr, lag_1m, lag_symbol, invert in configs:
        sig = build_predictor_signals(lead, lag, lag_atr, invert)
        print(f"\n{'='*78}\n{name}: {len(sig)} signals\n{'='*78}", flush=True)
        if len(sig) < MIN_TRAIN:
            print("  too few signals, skipping", flush=True)
            continue
        for risk in RISK_SWEEP:
            fold_trades = walk_forward(sig, lag_1m, lag_symbol, risk)
            if not fold_trades:
                print(f"  risk=${risk}: no fold had positive train expectancy (or no OOS trades)", flush=True)
                continue
            pooled = pd.concat(fold_trades, ignore_index=True)
            t_stat, p_val = stats.ttest_1samp(pooled["pnl"].values, popmean=0.0)
            worst_dd = max(fold_stats(t)["maxdd"] for t in fold_trades)
            n_breach = sum(1 for t in fold_trades if fold_stats(t)["breach"])
            print(f"  risk=${risk:>4}: OOS n={len(pooled):>4} exp=${pooled['pnl'].mean():>8.2f} "
                  f"t={t_stat:>6.2f} p={p_val:.2e} worst_dd=${worst_dd:>8.2f} "
                  f"breach={n_breach}/{len(fold_trades)} folds_traded={len(fold_trades)}/6", flush=True)

    print("\nDONE.", flush=True)
