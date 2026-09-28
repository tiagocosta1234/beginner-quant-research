"""
Round 198: "we need a strategy that fits our plan" -- resumed the idea-hunt
with a genuinely new construction, checked against IDEA_LEDGER.md first
(k=379): no round has tried META-LABELING. Every ML round so far (149's
walk-forward logistic/GBM, batch F/O) used ML to predict RAW PRICE
DIRECTION from market features -- a different, harder target that found
nothing (~54% direction accuracy, erased by costs). Meta-labeling (Lopez de
Prado) is a different technique: don't predict direction at all -- take an
EXISTING signal's own trades (Round 178's POC reversion, already-generated
entries/stops/targets) and train a classifier to predict whether THAT
SPECIFIC trade will win or lose, using features known at signal time, then
only take the trades the model is confident about. If POC reversion's win
rate varies with real, knowable conditions (how far from POC, how volatile
the recent market, day of week) even though raw price direction doesn't,
this could filter out the signal's worst trades without needing a new
signal at all.

Step 0, honest before running: this ledger's own ML rounds already found
essentially no real predictive edge in market features for raw price
direction. Meta-labeling changes the TARGET (win/loss of an existing rule,
not price direction), which could behave differently, but there's no
strong reason to expect it will -- if POC reversion's daily win/loss were
cleanly predictable from calendar/volatility features, that predictability
would itself likely already show up as a usable filter this campaign's
other rounds (calm-regime filters, day-of-week, confluence) would have
partially captured. Tested because it's a genuinely different technique
from anything tried, not because prior odds are good.

Method: NQ POC reversion (Round 178) trades only (the single largest real
leg). Features per trade, all causal (known at the signal's own timestamp,
no look-ahead): |open-POC| / S (the trigger's own z-like strength), S
itself (recent volatility level), day-of-week, month, trailing 20-trade
win rate of this same signal as of that trade, trailing 20-day realized
range change. Label: trade pnl > 0. Walk-forward: train ONLY on IS
(< 2025-07-01, matching this ledger's own OOS_START), predict OOS,
gradient-boosted trees (same model class Round 149 already used, for a
fair comparison). Test: does filtering OOS trades to the model's top-
confidence half/third beat taking every OOS trade, on win rate and R?

Not a fixed-parameter ledger row (this is a filter test on an already-
ledgered signal, same convention as Round 173's exit-reshaping check) --
reports honestly whether the filter helps, win-rate and R-multiple before
and after, IS AUC as a sanity check that the model learned anything at all
before trusting any OOS filter result.
"""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round171_databento_orb_replication import load_days_databento
from round178_volume_profile_poc import session_poc
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score

FLAT_TIME = dt.time(16, 0)  # match Round 178's own convention exactly, for a fair comparison
RANGE_WINDOW = 20
STOP_MULT = 0.15
WIN_TRAIL = 20


def build_signals_with_features(days, tick):
    ranges = pd.Series({d["tday"]: (d["session"]["high"].max() - d["session"]["low"].min())
                        for d in days if not d["session"].empty})
    avg_range = ranges.rolling(RANGE_WINDOW, min_periods=10).mean().shift(1)
    range_change = ranges.pct_change(RANGE_WINDOW).shift(1)

    out, prev_poc = [], None
    for d in days:
        s = d["session"]
        tday = d["tday"]
        S = avg_range.get(tday, np.nan)
        if s.empty or prev_poc is None or not (S > 0):
            prev_poc = session_poc(s, tick)
            continue
        open_px = s["open"].iloc[0]
        dist = prev_poc - open_px
        if abs(dist) >= STOP_MULT * S:
            direction = int(np.sign(dist))
            sl = open_px - direction * STOP_MULT * S
            out.append(dict(ts=s.index[0], direction=direction, entry=open_px, sl=sl, tp=prev_poc,
                           strength=abs(dist) / S, S=S, dow=tday.dayofweek, month=tday.month,
                           range_chg=range_change.get(tday, np.nan)))
        prev_poc = session_poc(s, tick)
    return pd.DataFrame(out)


def edge_stats(pnl, n_boot=20000, seed=0):
    if len(pnl) == 0:
        return dict(n=0, exp=np.nan, p_pos=np.nan)
    rng = np.random.default_rng(seed)
    boot_means = rng.choice(pnl, size=(n_boot, len(pnl)), replace=True).mean(axis=1)
    return dict(n=len(pnl), exp=float(pnl.mean()), p_pos=float((boot_means > 0).mean()))


if __name__ == "__main__":
    days = load_days_databento("NQ")
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    sig = build_signals_with_features(days, H.TK["NQ"])
    tr = H.resolve_bracket(sig[["ts", "direction", "entry", "sl", "tp"]], bars, "NQ", flat_time=FLAT_TIME)
    tr = tr.reset_index(drop=True)
    sig = sig.reset_index(drop=True)
    assert len(tr) == len(sig), f"{len(tr)} trades vs {len(sig)} signals -- resolve_bracket dropped some"
    tr["cost"] = tr["contracts"] * H.cost_per_contract("NQ")

    df = pd.concat([sig[["strength", "S", "dow", "month", "range_chg"]], tr[["entry_ts", "pnl", "r"]]], axis=1)
    df["win"] = (df["pnl"] > 0).astype(int)
    df["trail_winrate"] = df["win"].shift(1).rolling(WIN_TRAIL, min_periods=WIN_TRAIL).mean()
    df = df.dropna()

    is_mask = df["entry_ts"] < J.OOS_START
    feat_cols = ["strength", "S", "dow", "month", "range_chg", "trail_winrate"]
    X_is, y_is = df.loc[is_mask, feat_cols], df.loc[is_mask, "win"]
    X_oos, y_oos = df.loc[~is_mask, feat_cols], df.loc[~is_mask, "win"]
    oos = df.loc[~is_mask].copy()

    print(f"n_is={len(X_is)} n_oos={len(X_oos)}, base win rate IS {y_is.mean():.1%} OOS {y_oos.mean():.1%}\n")

    print("=== GradientBoostingClassifier (Round 149's own model class) ===")
    gbm = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=0).fit(X_is, y_is)
    auc_is_gbm = roc_auc_score(y_is, gbm.predict_proba(X_is)[:, 1])
    oos_pred_gbm = gbm.predict_proba(X_oos)[:, 1]
    auc_oos_gbm = roc_auc_score(y_oos, oos_pred_gbm)
    print(f"IS AUC {auc_is_gbm:.3f} -> OOS AUC {auc_oos_gbm:.3f} "
          f"({'severe IS/OOS gap -- overfitting, not a real filter' if auc_is_gbm - auc_oos_gbm > 0.15 else 'consistent'})\n")

    print("=== LogisticRegression (simpler, far less capacity to overfit 1,079 samples/6 features) ===")
    scaler = StandardScaler().fit(X_is)
    logit = LogisticRegression(max_iter=1000).fit(scaler.transform(X_is), y_is)
    auc_is_log = roc_auc_score(y_is, logit.predict_proba(scaler.transform(X_is))[:, 1])
    oos["pred"] = logit.predict_proba(scaler.transform(X_oos))[:, 1]
    auc_oos_log = roc_auc_score(y_oos, oos["pred"])
    print(f"IS AUC {auc_is_log:.3f} -> OOS AUC {auc_oos_log:.3f} (much closer together -- more trustworthy)")
    print(f"coefficients: {dict(zip(feat_cols, logit.coef_[0].round(3)))}\n")

    print(f"{'filter':<20} {'n':>4} {'win rate':>9} {'net $/trade':>12} {'P(edge>0)':>10}")
    st = edge_stats(oos["pnl"].values)
    print(f"{'baseline (all OOS)':<20} {st['n']:>4} {oos['win'].mean():>8.1%} {st['exp']:>+11.1f} {st['p_pos']:>10.3f}")
    results = {"baseline": st}
    for frac, label in [(0.5, "top 50% confidence"), (0.33, "top 33% confidence")]:
        thresh = np.quantile(oos["pred"], 1 - frac)
        sub = oos[oos["pred"] >= thresh]
        st = edge_stats(sub["pnl"].values)
        print(f"{label:<20} {st['n']:>4} {sub['win'].mean():>8.1%} {st['exp']:>+11.1f} {st['p_pos']:>10.3f}")
        results[label] = st

    with open(os.path.join(H.HERE, "round198_results.json"), "w") as f:
        json.dump(dict(auc_is_gbm=auc_is_gbm, auc_oos_gbm=auc_oos_gbm, auc_is_log=auc_is_log,
                       auc_oos_log=auc_oos_log, filters=results), f, indent=1, default=str)
