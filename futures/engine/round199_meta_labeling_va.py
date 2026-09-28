"""
Round 199: extends Round 198's meta-labeling construction to the Value Area
REJECTION leg (Round 184, continuation=False -- the variant Round 186's own
NQ combo actually uses), per the trader's direct follow-on after Round 198 found
a real but underpowered (n=82 OOS) filter effect on POC reversion alone.
Directly motivated by Round 198's own real-history finding: the filtered
POC-only signal fires just 67x/year, too infrequently to build the
reinvestment plan fast within a fixed calendar year even though its
per-trade stats are good -- adding the VA leg's own trades is the natural
fix (more real trades, same meta-labeling idea, not a new construction).

Same method as Round 198, same discipline (GBM overfitting check first,
logistic regression as the trustworthy model, bootstrap IS/OOS edge stats,
honest ledger row regardless of outcome): causal features known at signal
time (how far beyond VAH/VAL the open is, normalized by VA width; VA width
itself; day-of-week; month; recent range change; trailing 20-trade win
rate of this same VA-rejection signal), walk-forward split at this ledger's
own OOS_START, filter to the model's top-confidence trades, compare against
taking every VA-rejection trade.

Not a fixed-parameter ledger row (a filter test on an already-ledgered
signal, same convention as Round 198) -- reports honestly.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round171_databento_orb_replication import load_days_databento
from round198_meta_labeling_poc import FLAT_TIME, WIN_TRAIL, RANGE_WINDOW, edge_stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score


def session_value_area(session, tick):
    if session.empty:
        return np.nan, np.nan, np.nan
    px = np.round(session["close"] / tick).astype(int) * tick
    profile = pd.Series(session["vol"].values, index=px.values).groupby(level=0).sum().sort_index()
    if len(profile) < 2:
        v = float(profile.index[0])
        return v, v, v
    poc = profile.idxmax()
    levels = profile.index.to_list()
    poc_idx = levels.index(poc)
    target = 0.70 * profile.sum()
    lo = hi = poc_idx
    vol_sum = profile.iloc[poc_idx]
    while vol_sum < target and (lo > 0 or hi < len(levels) - 1):
        vol_below = profile.iloc[lo - 1] if lo > 0 else -1
        vol_above = profile.iloc[hi + 1] if hi < len(levels) - 1 else -1
        if vol_below >= vol_above:
            lo -= 1
            vol_sum += profile.iloc[lo]
        else:
            hi += 1
            vol_sum += profile.iloc[hi]
    return float(poc), float(levels[lo]), float(levels[hi])


def build_signals_with_features(days, tick):
    ranges = pd.Series({d["tday"]: (d["session"]["high"].max() - d["session"]["low"].min())
                        for d in days if not d["session"].empty})
    range_change = ranges.pct_change(RANGE_WINDOW).shift(1)

    rows, prev = [], None
    for d in days:
        s = d["session"]
        tday = d["tday"]
        if s.empty:
            continue
        if prev is not None:
            poc, val, vah = prev
            open_px = s["open"].iloc[0]
            va_width = vah - val
            if va_width > 0:
                if open_px > vah:
                    direction, sl, tp = -1, open_px + (open_px - vah), poc
                    strength = (open_px - vah) / va_width
                elif open_px < val:
                    direction, sl, tp = 1, open_px - (val - open_px), poc
                    strength = (val - open_px) / va_width
                else:
                    prev = session_value_area(s, tick)
                    continue
                rows.append(dict(ts=s.index[0], direction=direction, entry=open_px, sl=sl, tp=tp,
                               strength=strength, va_width=va_width, dow=tday.dayofweek, month=tday.month,
                               range_chg=range_change.get(tday, np.nan)))
        prev = session_value_area(s, tick)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    days = load_days_databento("NQ")
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    sig = build_signals_with_features(days, H.TK["NQ"])
    tr = H.resolve_bracket(sig[["ts", "direction", "entry", "sl", "tp"]], bars, "NQ", flat_time=FLAT_TIME)
    tr = tr.reset_index(drop=True)
    sig = sig.reset_index(drop=True)
    assert len(tr) == len(sig), f"{len(tr)} trades vs {len(sig)} signals -- resolve_bracket dropped some"
    tr["cost"] = tr["contracts"] * H.cost_per_contract("NQ")

    df = pd.concat([sig[["strength", "va_width", "dow", "month", "range_chg"]], tr[["entry_ts", "pnl", "r"]]], axis=1)
    df["win"] = (df["pnl"] > 0).astype(int)
    df["trail_winrate"] = df["win"].shift(1).rolling(WIN_TRAIL, min_periods=WIN_TRAIL).mean()
    df = df.dropna()

    is_mask = df["entry_ts"] < J.OOS_START
    feat_cols = ["strength", "va_width", "dow", "month", "range_chg", "trail_winrate"]
    X_is, y_is = df.loc[is_mask, feat_cols], df.loc[is_mask, "win"]
    X_oos, y_oos = df.loc[~is_mask, feat_cols], df.loc[~is_mask, "win"]
    oos = df.loc[~is_mask].copy()

    print(f"n_is={len(X_is)} n_oos={len(X_oos)}, base win rate IS {y_is.mean():.1%} OOS {y_oos.mean():.1%}\n")

    print("=== GradientBoostingClassifier (same overfitting check as Round 198) ===")
    gbm = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=0).fit(X_is, y_is)
    auc_is_gbm = roc_auc_score(y_is, gbm.predict_proba(X_is)[:, 1])
    auc_oos_gbm = roc_auc_score(y_oos, gbm.predict_proba(X_oos)[:, 1])
    print(f"IS AUC {auc_is_gbm:.3f} -> OOS AUC {auc_oos_gbm:.3f} "
          f"({'overfitting' if auc_is_gbm - auc_oos_gbm > 0.15 else 'consistent'})\n")

    print("=== LogisticRegression ===")
    scaler = StandardScaler().fit(X_is)
    logit = LogisticRegression(max_iter=1000).fit(scaler.transform(X_is), y_is)
    auc_is_log = roc_auc_score(y_is, logit.predict_proba(scaler.transform(X_is))[:, 1])
    oos["pred"] = logit.predict_proba(scaler.transform(X_oos))[:, 1]
    auc_oos_log = roc_auc_score(y_oos, oos["pred"])
    print(f"IS AUC {auc_is_log:.3f} -> OOS AUC {auc_oos_log:.3f}")
    print(f"coefficients: {dict(zip(feat_cols, logit.coef_[0].round(3)))}\n")

    isd = df.loc[is_mask].copy()
    isd["pred"] = logit.predict_proba(scaler.transform(X_is))[:, 1]

    print(f"{'filter':<20} {'n':>4} {'win rate':>9} {'net $/trade':>12} {'IS P(edge>0)':>13} {'OOS P(edge>0)':>13}")
    st_oos = edge_stats(oos["pnl"].values)
    st_is = edge_stats(isd["pnl"].values)
    print(f"{'baseline (all)':<20} {st_oos['n']:>4} {oos['win'].mean():>8.1%} {st_oos['exp']:>+11.1f} "
          f"{st_is['p_pos']:>13.3f} {st_oos['p_pos']:>13.3f}")
    results = {"baseline": dict(is_=st_is, oos=st_oos)}
    for frac, label in [(0.5, "top 50% confidence"), (0.33, "top 33% confidence")]:
        thresh_oos = np.quantile(oos["pred"], 1 - frac)
        sub_oos = oos[oos["pred"] >= thresh_oos]
        st_oos_f = edge_stats(sub_oos["pnl"].values)
        thresh_is = np.quantile(isd["pred"], 1 - frac)
        sub_is = isd[isd["pred"] >= thresh_is]
        st_is_f = edge_stats(sub_is["pnl"].values)
        print(f"{label:<20} {st_oos_f['n']:>4} {sub_oos['win'].mean():>8.1%} {st_oos_f['exp']:>+11.1f} "
              f"{st_is_f['p_pos']:>13.3f} {st_oos_f['p_pos']:>13.3f}")
        results[label] = dict(is_=st_is_f, oos=st_oos_f)

    with open(os.path.join(H.HERE, "round199_results.json"), "w") as f:
        json.dump(dict(auc_is_gbm=auc_is_gbm, auc_oos_gbm=auc_oos_gbm, auc_is_log=auc_is_log,
                       auc_oos_log=auc_oos_log, filters=results), f, indent=1, default=str)
