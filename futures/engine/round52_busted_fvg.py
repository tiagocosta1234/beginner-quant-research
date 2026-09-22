"""
Round 52: "busted FVG" -- trades the FAILURE of a Fair Value Gap, not the gap
itself. Prior FVG work in this repo (Rounds 11-13, 20) traded FVGs as support/
resistance zones directly (buy the gap) and Round 20 found that underperforms
random entry. This is a different mechanic: price must first TAP into a
confirmed FVG zone (the setup retail would enter on), then later CLOSE
completely through the OPPOSITE side of that same zone (the setup failing) --
trade in the direction of the failure/break, not the original gap direction.

LOOK-AHEAD CHECK: FVG confirmation is causal (round11_fvg_bias.detect_fvgs,
already verified elsewhere tonight). The tap and the bust-close are both
checked only against bars strictly after the zone's own confirm_ts. Entry is
at the bust-confirming bar's own close (the bar whose close triggers the
signal), not any earlier or future bar.
"""
import os, sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal, detect_fvgs, BUFFER, FOLDS, fold_stats
from round19_random_entry import causal_atr15_lookup, attach_atr, STOP_ATR_MULT, TRAIL_ATR_MULT
from round30b_sequential_fix import resolve_trailing_sequential

HTF_RULE = "15min"
MAX_ZONE_AGE_BARS = 40  # 15m bars a zone can still bust after (~10h)
RISK_SWEEP = [100, 200, 300, 400]
MIN_TRAIN = 20


def build_busted_fvg_signals(df1m, htf, fvgs, atr15, max_age_bars):
    htf_idx = htf.index.values
    htf_hi = htf["high"].values
    htf_lo = htf["low"].values
    htf_cl = htf["close"].values
    n = len(htf)
    rows = []
    for r in fvgs.itertuples(index=False):
        start_pos = np.searchsorted(htf_idx, np.datetime64(r.confirm_ts), side="right")
        end_pos = min(start_pos + max_age_bars, n)
        tapped = False
        for i in range(start_pos, end_pos):
            if not tapped:
                # tap = price trades into the zone
                if htf_lo[i] <= r.zone_hi and htf_hi[i] >= r.zone_lo:
                    tapped = True
                    continue
            else:
                # after tap, look for a close that fully busts through the OPPOSITE side
                if r.direction == 1:  # bullish FVG (support); bust = close below zone_lo
                    if htf_cl[i] < r.zone_lo:
                        rows.append((htf_idx[i], -1, htf_cl[i]))
                        break
                else:  # bearish FVG (resistance); bust = close above zone_hi
                    if htf_cl[i] > r.zone_hi:
                        rows.append((htf_idx[i], 1, htf_cl[i]))
                        break
    sig = pd.DataFrame(rows, columns=["ts", "direction", "entry"]).sort_values("ts").reset_index(drop=True)
    if len(sig) == 0:
        return sig
    sig = attach_atr(sig, atr15)
    sig = sig[sig["atr"] > 0].copy()
    stop_dist = STOP_ATR_MULT * sig["atr"]
    sig["stop"] = np.where(sig["direction"] == 1, sig["entry"] - stop_dist, sig["entry"] + stop_dist)
    return sig[["ts", "direction", "entry", "stop"]].reset_index(drop=True)


def run_symbol(symbol, path):
    print(f"\n{'='*78}\n{symbol} busted-FVG\n{'='*78}", flush=True)
    df1m = load_1m(path)
    atr15 = causal_atr15_lookup(df1m)
    htf = resample_causal(df1m, HTF_RULE)
    fvgs = detect_fvgs(htf)
    print(f"{symbol}: {len(fvgs)} FVGs detected on {HTF_RULE}", flush=True)

    sig_all = build_busted_fvg_signals(df1m, htf, fvgs, atr15, MAX_ZONE_AGE_BARS)
    print(f"{symbol}: {len(sig_all)} busted-FVG signals "
          f"({100*len(sig_all)/max(1,len(fvgs)):.1f}% of FVGs eventually busted after being tapped)", flush=True)
    if len(sig_all) < MIN_TRAIN:
        print("too few signals.", flush=True)
        return

    for risk in RISK_SWEEP:
        all_oos = []
        for train_end, test_end in FOLDS:
            train_sig = sig_all[sig_all["ts"] < train_end]
            test_sig = sig_all[(sig_all["ts"] >= train_end) & (sig_all["ts"] < test_end)]
            if len(train_sig) < MIN_TRAIN or len(test_sig) == 0:
                continue
            tr, _ = resolve_trailing_sequential(train_sig, df1m, symbol, risk, TRAIL_ATR_MULT)
            if len(tr) < MIN_TRAIN or tr["pnl"].mean() <= 0:
                continue  # train-selected: only trade OOS if train itself was positive at this risk
            te, _ = resolve_trailing_sequential(test_sig, df1m, symbol, risk, TRAIL_ATR_MULT)
            if len(te) > 0:
                all_oos.append(te)
        if not all_oos:
            print(f"  risk=${risk}: no fold had positive train expectancy", flush=True)
            continue
        pooled = pd.concat(all_oos, ignore_index=True)
        t_stat, p_val = stats.ttest_1samp(pooled["pnl"].values, popmean=0.0)
        worst_dd = max(fold_stats(t)["maxdd"] for t in all_oos)
        n_breach = sum(1 for t in all_oos if fold_stats(t)["breach"])
        print(f"  risk=${risk}: OOS n={len(pooled)} exp=${pooled['pnl'].mean():.2f} t={t_stat:.2f} "
              f"p={p_val:.2e} worst_dd=${worst_dd:.2f} breach={n_breach}/{len(all_oos)} "
              f"folds_traded={len(all_oos)}/6", flush=True)


if __name__ == "__main__":
    run_symbol("MNQ", os.path.join("..", "data", "MNQ_CONTINUOUS.txt"))
    run_symbol("MGC", os.path.join("..", "data", "MGC_CONTINUOUS.txt"))
    print("\nDONE.", flush=True)
