"""
Round 30: Swing-based support/resistance BOUNCE, MGC -- proper walk-forward validation
of the promising in-sample result found interactively (profit_factor=1.20, tail10=2.9%,
tail20=4.7% on the FULL period, no train/test split). This script re-tests it with this
campaign's actual standard: expanding-window 6-fold walk-forward, train-only parameter
grid search, real costs, buffer-safe sizing search, tail-concentration re-check per fold.

Swing points: causal K-bar fractal (a bar is a swing high/low only once K bars AFTER it
have closed -- the same lesson from Round 9c's lookahead-bug correction, applied from
the start this time, not discovered after the fact).
Entry: first touch of an active (unbroken) swing level, BOUNCE direction (fade the level).
Exit: same validated ATR-trailing stop as the rest of this campaign (Round 19-29),
no fixed target.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import pandas as pd
import numpy as np
from round11_fvg_bias import load_1m, resample_causal, POINT_VALUE, TICK_SIZE, COMMISSION_RT, FOLDS
from round19_random_entry import causal_atr15_lookup, resolve_trailing

RISK_LEVELS = (400, 600)
BUFFER = 4937.50
TRAIL_MULT = 1.5
STOP_ATR_MULT = 1.0
SWING_K_GRID = (3, 5, 8, 13)
TOL_GRID = (0.10, 0.25, 0.50)

def build_swing_touch_signals(df1m, h15, atr15, swing_k, tol_atr):
    hi = h15["high"].values; lo = h15["low"].values; idx15 = h15.index; n15 = len(h15)
    swing_highs, swing_lows = [], []
    for i in range(swing_k, n15 - swing_k):
        if hi[i] == hi[i-swing_k:i+swing_k+1].max():
            swing_highs.append((idx15[i+swing_k], hi[i]))
        if lo[i] == lo[i-swing_k:i+swing_k+1].min():
            swing_lows.append((idx15[i+swing_k], lo[i]))
    sh = pd.DataFrame(swing_highs, columns=["confirm_ts","price"]).sort_values("confirm_ts").reset_index(drop=True)
    sl = pd.DataFrame(swing_lows, columns=["confirm_ts","price"]).sort_values("confirm_ts").reset_index(drop=True)

    ts1 = df1m.index.values; hi1 = df1m["high"].values; lo1 = df1m["low"].values
    atr_ts = atr15.index.values
    def atr_at(ts):
        pos = np.searchsorted(atr_ts, ts, side="right") - 1
        return atr15.values[pos] if pos >= 0 else None

    def touches(levels_df, is_resistance):
        # FIXED 2026-09-20 (was a confirmed, quantified backtest-inflation bug):
        # the touch CONDITION fires as soon as price gets within `tol` of a
        # level, but the fill used to be credited at the idealized `lvl.price`
        # regardless of whether price actually reached it -- a phantom fill no
        # real resting order could obtain, worth ~half an R of impossible free
        # edge per trade on MGC at tol=0.50 (see EDGE_AUDIT_2026-09-20.md). Now
        # credited at the actual price printed on the touching bar, capped so
        # it can never be BETTER than the ideal level (standard limit-fill
        # convention: a resting order at `lvl.price` fills AT that price when
        # price trades through it, never at a worse-for-the-strategy price than
        # what was actually offered, and never at a better one than the level
        # itself when price only approached within tolerance).
        #
        # ADDED 2026-09-21 (additive, non-breaking -- existing ts/level/atr/
        # bounce_dir columns unchanged): confirm_ts, touch_lag_bars, and
        # pierce_frac are recorded per touch for confidence-based sizing
        # research (round56). All three are known exactly at the touch bar
        # itself -- no lookahead. pierce_frac = (level - raw extreme)/atr for
        # resistance, (raw extreme - level)/atr for support: positive means
        # price approached without reaching the level (shallow test), ~0 means
        # an exact touch, negative means price pierced through it (deep test).
        rows = []
        for lvl in levels_df.itertuples(index=False):
            start_pos = np.searchsorted(ts1, np.datetime64(lvl.confirm_ts), side="right")
            if start_pos >= len(ts1): continue
            a = atr_at(ts1[start_pos])
            if not a or a <= 0: continue
            tol = tol_atr * a
            end_pos = min(start_pos + 2000, len(ts1))
            for j in range(start_pos, end_pos):
                if is_resistance:
                    if hi1[j] >= lvl.price - tol:
                        fill = min(hi1[j], lvl.price)
                        pierce_frac = (lvl.price - hi1[j]) / a
                        rows.append((ts1[j], fill, a, -1, lvl.confirm_ts, j - start_pos, pierce_frac)); break
                else:
                    if lo1[j] <= lvl.price + tol:
                        fill = max(lo1[j], lvl.price)
                        pierce_frac = (lo1[j] - lvl.price) / a
                        rows.append((ts1[j], fill, a, 1, lvl.confirm_ts, j - start_pos, pierce_frac)); break
        return pd.DataFrame(rows, columns=["ts","level","atr","bounce_dir","confirm_ts","touch_lag_bars","pierce_frac"])

    t_r = touches(sh, True); t_s = touches(sl, False)
    t = pd.concat([t_r, t_s]).sort_values("ts").reset_index(drop=True)
    if t.empty:
        return pd.DataFrame(columns=["ts","direction","entry","stop","confirm_ts","touch_lag_bars","pierce_frac"])
    t["direction"] = t["bounce_dir"]
    stop_dist = STOP_ATR_MULT * t["atr"]
    t["entry"] = t["level"]
    t["stop"] = np.where(t["direction"]==1, t["entry"]-stop_dist, t["entry"]+stop_dist)
    return t[["ts","direction","entry","stop","confirm_ts","touch_lag_bars","pierce_frac"]]

def tail_conc(trades, n):
    total_profit = trades[trades["pnl"]>0]["pnl"].sum()
    if total_profit <= 0: return None
    top = trades.sort_values("pnl", ascending=False)["pnl"].head(n).clip(lower=0).sum()
    return top/total_profit

def main():
    symbol = "MGC"
    df1m = load_1m(f"../data/{symbol}_CONTINUOUS.txt")
    h15 = resample_causal(df1m, "15min")
    atr15 = causal_atr15_lookup(df1m)

    print(f"{symbol}: {len(df1m)} bars {df1m.index.min()} -> {df1m.index.max()}", flush=True)

    fold_results = []
    for fi, (train_end, test_end) in enumerate(FOLDS):
        train_end_ts = pd.Timestamp(train_end)
        test_end_ts = pd.Timestamp(min(pd.Timestamp(test_end), df1m.index.max()))
        if train_end_ts >= df1m.index.max():
            continue

        # train-only grid search: build signals on train-period data only, pick best (swing_k, tol) by expectancy
        train_df = df1m[df1m.index < train_end_ts]
        train_h15 = h15[h15.index < train_end_ts]
        train_atr = atr15[atr15.index < train_end_ts]
        best = None
        for sk in SWING_K_GRID:
            for tol in TOL_GRID:
                sig = build_swing_touch_signals(train_df, train_h15, train_atr, sk, tol)
                if len(sig) < 30:
                    continue
                tr = resolve_trailing(sig, train_df, symbol, 400, TRAIL_MULT)
                if len(tr) < 30:
                    continue
                exp = tr["pnl"].mean()
                if best is None or exp > best[0]:
                    best = (exp, sk, tol, len(tr))
        if best is None:
            print(f"fold {fi}: no viable train config, skipping")
            continue
        _, sk, tol, ntrain = best
        print(f"fold {fi} [{train_end}->{test_end}]: TRAIN-selected swing_k={sk} tol={tol} (n_train={ntrain})", flush=True)

        # OOS: test period only, causal signals built using test-period-only data (levels confirmed within test window)
        test_df = df1m[(df1m.index >= train_end_ts) & (df1m.index < test_end_ts)]
        test_h15 = h15[(h15.index >= train_end_ts) & (h15.index < test_end_ts)]
        test_atr = atr15[(atr15.index >= train_end_ts) & (atr15.index < test_end_ts)]
        if len(test_df) < 100:
            continue
        sig_oos = build_swing_touch_signals(test_df, test_h15, test_atr, sk, tol)
        for risk in RISK_LEVELS:
            tr_oos = resolve_trailing(sig_oos, test_df, symbol, risk, TRAIL_MULT)
            if tr_oos.empty:
                continue
            wins = tr_oos[tr_oos["pnl"]>0]; losses = tr_oos[tr_oos["pnl"]<0]
            exp = tr_oos["pnl"].mean()
            wr = len(wins)/len(tr_oos)
            peak = tr_oos["pnl"].cumsum().cummax()
            dd = tr_oos["pnl"].cumsum() - peak
            maxdd = dd.min()
            breach = maxdd <= -BUFFER
            t10 = tail_conc(tr_oos, 10); t20 = tail_conc(tr_oos, 20)
            fold_results.append({
                "fold": fi, "risk": risk, "swing_k": sk, "tol": tol, "n": len(tr_oos),
                "win_rate": wr, "exp": exp, "total_pnl": tr_oos["pnl"].sum(),
                "max_dd": maxdd, "breach": breach, "tail10": t10, "tail20": t20,
            })
            print(f"  OOS risk=${risk}: n={len(tr_oos)} win%={wr:.1%} exp=${exp:,.2f} "
                  f"total=${tr_oos['pnl'].sum():,.0f} maxdd=${maxdd:,.0f} breach={breach} "
                  f"tail10={t10} tail20={t20}", flush=True)

    res = pd.DataFrame(fold_results)
    res.to_csv("round30_sr_bounce_results.csv", index=False)
    print("\n=== SUMMARY (pooled across folds, per risk level) ===")
    for risk in RISK_LEVELS:
        sub = res[res["risk"]==risk]
        if sub.empty: continue
        total_n = sub["n"].sum()
        pooled_exp = (sub["exp"]*sub["n"]).sum()/total_n
        n_breaches = sub["breach"].sum()
        print(f"risk=${risk}: total_n={total_n} pooled_exp=${pooled_exp:,.2f} "
              f"folds_breaching={n_breaches}/{len(sub)} "
              f"win_rates={sub['win_rate'].round(3).tolist()}")
    print("\nDONE.")

if __name__ == "__main__":
    main()
