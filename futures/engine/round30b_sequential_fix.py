"""
Round 30b: fixes a real gap found in Round 30's S/R bounce validation -- the signal
generator fired on every level touch independently (~14.5/day average), with no
"skip if already in a position" gate, unlike every other round in this campaign and
unlike live_bot's actual architecture (broker.has_open_position() gates every entry).
~45% of consecutive signals were within an hour of each other; this re-resolves the
identical swing-touch signals SEQUENTIALLY, skipping any signal that fires before the
prior accepted trade's own exit bar -- the real, enforceable "one position at a time"
constraint -- before trusting Round 30's numbers for anything deployable or for
combining with MNQ.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import numpy as np
import pandas as pd
from round11_fvg_bias import load_1m, resample_causal, POINT_VALUE, TICK_SIZE, COMMISSION_RT, FOLDS
from round19_random_entry import causal_atr15_lookup
from round30_support_resistance import build_swing_touch_signals

def resolve_trailing_sequential(sig_df, df1m, symbol, risk_dollar, trail_mult, max_hold_bars=390):
    """Same trailing-stop mechanics as round19's resolve_trailing, but processes
    signals in chronological order and SKIPS any signal whose entry bar is before
    the previous ACCEPTED trade's own exit bar -- real one-position-at-a-time
    enforcement, matching this campaign's standing convention everywhere else."""
    pv = POINT_VALUE[symbol]; tick = TICK_SIZE[symbol]
    slip_dollars_rt = 2 * tick * pv
    ts = df1m.index.values; hi = df1m["high"].values; lo = df1m["low"].values; cl = df1m["close"].values
    n = len(df1m)
    results = []
    next_free_pos = 0  # earliest bar index at which a new entry may be taken
    sig_df = sig_df.sort_values("ts").reset_index(drop=True)
    skipped_overlap = 0
    for r in sig_df.itertuples(index=False):
        pos = np.searchsorted(ts, np.datetime64(r.ts), side="right")
        if pos >= n:
            continue
        if pos < next_free_pos:
            skipped_overlap += 1
            continue  # would-be overlapping signal -- a real account would already be in a position
        init_dist = abs(r.entry - r.stop)
        if init_dist <= 0:
            continue
        trail_dist = trail_mult * init_dist
        contracts = max(1, int(risk_dollar // (init_dist * pv)))
        commission = COMMISSION_RT * contracts
        end_pos = min(pos + max_hold_bars, n - 1)
        cur_stop = r.entry - trail_dist if r.direction == 1 else r.entry + trail_dist
        best = r.entry; exit_px = None; outcome = "timeout"; exit_i = end_pos
        for i in range(pos, end_pos + 1):
            bar_hi, bar_lo = hi[i], lo[i]
            if r.direction == 1:
                if bar_lo <= cur_stop:
                    exit_px = cur_stop; outcome = "trail_stop"; exit_i = i; break
                best = max(best, bar_hi); cur_stop = max(cur_stop, best - trail_dist)
            else:
                if bar_hi >= cur_stop:
                    exit_px = cur_stop; outcome = "trail_stop"; exit_i = i; break
                best = min(best, bar_lo); cur_stop = min(cur_stop, best + trail_dist)
        if exit_px is None:
            exit_px = cl[end_pos]; outcome = "session_flatten"; exit_i = end_pos
        move = (exit_px - r.entry) if r.direction == 1 else (r.entry - exit_px)
        pnl = move * pv * contracts - commission - slip_dollars_rt * contracts
        results.append((r.ts, symbol, r.direction, np.nan, risk_dollar, contracts, pnl, outcome))
        next_free_pos = exit_i + 1  # flat again only after this trade's own exit bar
    out = pd.DataFrame(results, columns=["ts","symbol","direction","rr","risk","contracts","pnl","outcome"])
    return out, skipped_overlap


if __name__ == "__main__":
    RISK_LEVELS = (400, 600)
    BUFFER = 4937.50
    TRAIL_MULT = 1.5
    symbol = "MGC"
    df1m = load_1m(f"../data/{symbol}_CONTINUOUS.txt")
    h15 = resample_causal(df1m, "15min")
    atr15 = causal_atr15_lookup(df1m)
    print(f"{symbol}: {len(df1m)} bars {df1m.index.min()} -> {df1m.index.max()}", flush=True)

    # re-use Round 30's own train-selected (swing_k, tol) per fold -- don't re-run the grid search,
    # just re-resolve the SAME selected signals sequentially instead of independently
    prior = pd.read_csv("round30_sr_bounce_results.csv")
    fold_params = prior[prior["risk"]==400][["fold","swing_k","tol"]].drop_duplicates()

    fold_rows = []
    for _, row in fold_params.iterrows():
        fi = int(row["fold"]); sk = int(row["swing_k"]); tol = row["tol"]
        train_end, test_end = FOLDS[fi]
        train_end_ts = pd.Timestamp(train_end); test_end_ts = pd.Timestamp(min(pd.Timestamp(test_end), df1m.index.max()))
        test_df = df1m[(df1m.index >= train_end_ts) & (df1m.index < test_end_ts)]
        test_h15 = h15[(h15.index >= train_end_ts) & (h15.index < test_end_ts)]
        test_atr = atr15[(atr15.index >= train_end_ts) & (atr15.index < test_end_ts)]
        sig = build_swing_touch_signals(test_df, test_h15, test_atr, sk, tol)
        for risk in RISK_LEVELS:
            tr, skipped = resolve_trailing_sequential(sig, test_df, symbol, risk, TRAIL_MULT)
            if tr.empty: continue
            wins = tr[tr["pnl"]>0]; losses = tr[tr["pnl"]<0]
            exp = tr["pnl"].mean(); wr = len(wins)/len(tr)
            peak = tr["pnl"].cumsum().cummax(); dd = tr["pnl"].cumsum() - peak; maxdd = dd.min()
            total_profit = wins["pnl"].sum()
            sorted_pnl = tr.sort_values("pnl", ascending=False)["pnl"]
            t10 = sorted_pnl.head(10).clip(lower=0).sum()/total_profit if total_profit>0 else None
            t20 = sorted_pnl.head(20).clip(lower=0).sum()/total_profit if total_profit>0 else None
            fold_rows.append(dict(fold=fi, risk=risk, swing_k=sk, tol=tol, n=len(tr),
                                   n_skipped_overlap=skipped, win_rate=wr, exp=exp,
                                   total_pnl=tr["pnl"].sum(), max_dd=maxdd,
                                   breach=maxdd<=-BUFFER, tail10=t10, tail20=t20))
            print(f"fold {fi} risk=${risk}: n={len(tr)} (skipped {skipped} overlapping of "
                  f"{len(tr)+skipped} raw) win%={wr:.1%} exp=${exp:,.2f} total=${tr['pnl'].sum():,.0f} "
                  f"maxdd=${maxdd:,.0f} breach={maxdd<=-BUFFER} tail10={t10} tail20={t20}", flush=True)

    res = pd.DataFrame(fold_rows)
    res.to_csv("round30b_sequential_results.csv", index=False)
    print("\n=== SUMMARY (sequential, no-overlap) ===")
    for risk in RISK_LEVELS:
        sub = res[res["risk"]==risk]
        total_n = sub["n"].sum()
        pooled_exp = (sub["exp"]*sub["n"]).sum()/total_n
        print(f"risk=${risk}: total_n={total_n} pooled_exp=${pooled_exp:,.2f} "
              f"folds_breaching={sub['breach'].sum()}/{len(sub)}")
    print("DONE.")
