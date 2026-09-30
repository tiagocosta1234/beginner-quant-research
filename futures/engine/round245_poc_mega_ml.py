"""
Round 245 (2026-09-30): the "mega ML" meta-labeling filter on the POC leg.
the trader: "start building the mega ML on the POC leg". Design frame:
futures/docs/NEXT_STRATEGY_MINDSET.md (three videos, same day).
PRE-REGISTRATION -- every design decision below is fixed BEFORE any label, P&L
or model output is looked at. Reported however it lands.

WHY THIS BASE. The live eval bot's POC-reversion leg (disciplined_bracket_strategy,
VA leg off per Round 230) is the leg with the most evidence in this repo (Round 178
IS P 0.98, 8/8 robustness perturbations positive, Round 244's narrow-day lead lives
here) and it is the eval-stage bot, where the one-month pass constraint binds.
Previous ML on this signal: Round 198 (6 features, logistic, OOS top-33% $287/trade,
P 0.938, not significant; that model is live in the Combined bot). This round is
the bigger version the mindset doc allows: more features, two model families, pooled
NQ+ES training for sample size -- with every safeguard from the checklist.

STEP 0 (pass-speed screen, honest): the unfiltered leg's daily Sharpe is ~0.03-0.05.
A filter keeps a subset of the same trades, so it can raise the mean per trade but
cuts trade count; reaching the ~0.3 daily Sharpe a one-month pass needs would take a
per-trade lift far beyond anything seen in this repo (Round 198's best: ~2x $/trade).
Expectation going in: the filter may improve $/trade; clearing the one-month bar is
very unlikely. Run anyway because it is the one base with evidence of edge.

BASE TRADES. Round 229/230's replay of the live bot's own code (signal_poc_only +
run_variant), $50K sizing ($300 risk, $1,650 win cap, <= 50 micros, DLL $1,000), net
of costs, flat by 16:10 ET, Databento 1-min 2019-10..2026-09. NQ (MNQ $2/pt) is the
deployment market; ES (MES $5/pt) is pooled into training and used as replication.
The consecutive-losing-days governor rule is switched OFF so every signal gets a
label (CONSEC_DAYS_LIMIT = 1e9); disclosed. One POC trade per market per day.

LABEL. y = 1 if net trade P&L > 0 (triple barrier = the bot's own stop, capped
target, session flat). R = pnl / $300.

FEATURES (30, fixed; all known at the 09:30 ET entry; daily ones from completed
sessions only; standardized on TRAIN rows only):
  geometry  strength (|open-prevPOC|/S), rr_plan (planned capped reward / $300),
            capped (win cap bound), dirn, open_in_va, va_width_S, poc_loc (prev POC
            position in prev range), prevclose_poc (dirn*(prev close-prev POC)/S)
  session   gap_S (dirn*(open-prev close)/S), on_rng_S, on_rng_rel (vs median of
            prior 20 overnights), on_move_S (dirn*(open-overnight open)/S),
            open_vs_on_mid (dirn*(open-overnight mid)/S), on_vol_rel
  regime    prev_rng_rel (prev range/SMA20), rv_rel (rv20/its 250d median),
            trend20_S (dirn*(prev close-SMA20)/S), ret5_S (dirn*5-day change/S),
            S_bps (S/prev close*1e4), vix_rel (prior VIX/250d median), vix_chg5,
            range_chg (Round 198's), lead244 (narrow & not low-vol)
  history   trail_wr, trail_R (last 20 POC trades of that market, all closed)
  calendar  dow_sin/cos, month_sin/cos
  market    is_nq
S = mean of the last 20 RTH ranges (the bot's own). Rows with any NaN feature
(warm-up) are dropped before any split.

MODELS (hyperparameters fixed a priori, never tuned):
  M0 "R198"  LogisticRegression (default L2, C=1) on Round 198's 6 features
             (strength, S points, dow, month, range_chg, trail_wr), NQ-only training
             -- the live Combined bot's model family, as the simple baseline.
  M1 "L1"    LogisticRegression(penalty="l1", solver="liblinear", C=0.1), 30 features,
             NQ+ES pooled.
  M2 "HGB"   HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05,
             max_iter=150, min_samples_leaf=40, l2_regularization=1.0,
             random_state=0), 30 features, pooled.
  MEGA       mean of M1 and M2 probabilities.  <-- PRIMARY
DECISION RULE (all models, parameter-free, "judge by $"): take iff
  EV = p * w * rr_plan + (1 - p) * l > 0,
where w = mean(realized R / rr_plan) over TRAIN winners and l = mean realized R over
TRAIN losers (captures flat-at-close partial wins/losses and costs).

VALIDATION.
  * Expanding walk-forward, 8 half-year test folds 2021-07-01 .. 2025-07-01; train =
    all trades (both markets) before the fold start. Trades close the same day and
    features use prior days only, so no label straddles a split (purge is trivially
    satisfied; asserted in code).
  * Fold floor: a fold counts for NQ only with >= 15 taken and >= 15 skipped NQ
    test trades; rejected folds listed with the reason.
  * FINAL HOLDOUT: trades >= 2025-07-01 (the ledger's OOS), model trained once on all
    trades before it, evaluated ONCE after the walk-forward. No re-tuning.

CANDIDATE RULES (fixed now).
  FILTER CONFIRMED (MEGA) needs all of:
   (a) pooled WF NQ: bootstrap P(mean taken > mean skipped) >= 0.95
   (b) pooled WF NQ: bootstrap P(mean taken > 0) >= 0.95
   (c) taken > skipped in >= 6 accepted NQ folds
   (d) label-shuffle control (200 runs of the MEGA pipeline): fraction with NQ pooled
       lift >= real <= 0.05; AND random filter (2,000 draws, same per-fold keep
       count): fraction >= real <= 0.05
   (e) ES replication: pooled WF ES lift > 0 with P(taken > skipped) >= 0.80
   (f) holdout NQ: taken mean > skipped mean AND > unfiltered mean
   (g) one-month account metric: pass_speed_gate.gate() P(pass within 21 days) of the
       filtered NQ daily R series > the unfiltered one, on the pooled WF days
  COMPLEXITY CHECK (reported, decides what would ship): MEGA pooled WF NQ lift must
   exceed both M1's and M0's; otherwise the simpler model is the recommendation.
  LEDGER CANDIDATE (the repo's formal bar): 3 ledger rows (MEGA, M1, M0 filtered NQ
   trades; IS = pooled out-of-fold WF trades, OOS = holdout): idea_harness rule, OOS
   P(edge>0) >= 1 - 0.01/k.
  Also reported: daily Sharpe of filtered vs unfiltered, and where it sits on the
  mindset doc's one-month table (~0.3 needed for ~70% in 21 days).

NOT DONE / DISCLOSED: no hyperparameter search; governor's losing-days rule off for
labeling; ES shares no sessions' outcomes with NQ but is highly correlated (it adds
rows, not independent evidence -- replication (e) is descriptive-strength only);
the filter would be deployed through the bracket bot's existing BRACKET_POC_FILTER
slot only after the trader's OK.

POWER NOTES (from --dry-run, counts and feature ranges only; no label, P&L or model
output looked at): 2,664 raw POC trades (NQ+ES), 2,442 after the warm-up drop (NQ
1,234 / ES 1,208; 2020-04-17 .. 2026-09-25; rv_rel's 250-day median is the main
warm-up cost). Walk-forward NQ test sizes per fold 81-105 (train 489 -> 1,781 rows,
both markets); holdout NQ 250 / ES 231, train 1,961. With ~90 NQ test trades per fold,
the 15-per-side floor fails only if the filter keeps or drops > 83% of a fold. Pooled
WF NQ ~737 trades is the real power; per-trade P&L sd is ~$300-500, so a taken-vs-
skipped gap needs to be roughly $60+/trade to reach P 0.95. Hand-check: 2020-04-21 NQ
(first row) recomputed independently from raw bars -- prev POC 8739.5, open 8630.5,
S 248.97, strength 0.437795, long, 4 micros, gap_S -0.327342: all identical.
range_chg has a heavy right tail (max 21.3, Round 198's own definition); kept as is.
"""
import os, sys, json, argparse, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

import idea_harness as H
import round229_rth_vs_24x5 as R229
import round230_no_va_leg as R230
from pass_speed_gate import gate

RISK = 300.0
OOS = pd.Timestamp("2025-07-01")
WF_FOLDS = [(pd.Timestamp(a), pd.Timestamp(b)) for a, b in (
    ("2021-07-01", "2022-01-01"), ("2022-01-01", "2022-07-01"), ("2022-07-01", "2023-01-01"),
    ("2023-01-01", "2023-07-01"), ("2023-07-01", "2024-01-01"), ("2024-01-01", "2024-07-01"),
    ("2024-07-01", "2025-01-01"), ("2025-01-01", "2025-07-01"))]
MIN_PER_SIDE = 15
N_BOOT, N_SHUFFLE, N_RANDOM = 4000, 200, 2000
FEATURES = ["strength", "rr_plan", "capped", "dirn", "open_in_va", "va_width_S", "poc_loc", "prevclose_poc",
            "gap_S", "on_rng_S", "on_rng_rel", "on_move_S", "open_vs_on_mid", "on_vol_rel",
            "prev_rng_rel", "rv_rel", "trend20_S", "ret5_S", "S_bps", "vix_rel", "vix_chg5", "range_chg", "lead244",
            "trail_wr", "trail_R", "dow_sin", "dow_cos", "month_sin", "month_cos", "is_nq"]
R198_FEATURES = ["strength", "S", "dow", "month", "range_chg", "trail_wr"]
MARKETS = {"NQ": dict(pv=2.0, cost=H.cost_per_contract("MNQ")), "ES": dict(pv=5.0, cost=H.cost_per_contract("MES"))}


# ------------------------------------------------------------------ data ----
def load_market(sym):
    """Days, the live bot's POC trades (governor losing-days rule off) and per-trade signal geometry."""
    R229.DBS.RISK_PER_TRADE, R229.DBS.CAP_WIN_DOLLARS, R229.DBS.MAX_CONTRACTS = RISK, 1650.0, 50
    R229.DLL, R229.DAY_PROFIT_CAP, R229.CONSEC_DAYS_LIMIT = 1000.0, 1650.0, 10 ** 9
    old = (R229.DB_FILE, R229.PV, R229.COST_PER_CONTRACT, R229.DBS.POINT_VALUE_MNQ)
    R229.DB_FILE = os.path.join(HERE, "..", "data", "databento", f"futures_{sym}.F_1m.parquet")
    R229.PV, R229.COST_PER_CONTRACT, R229.DBS.POINT_VALUE_MNQ = MARKETS[sym]["pv"], MARKETS[sym]["cost"], MARKETS[sym]["pv"]
    try:
        days = R229.load_days()
        profiles = R229.build_profiles(days)
        tr, _ = R230.run(days, profiles, R229.VARIANTS["A_current_rth"], no_va=True)
        # the signal geometry for each traded day, replayed with the same causal profile history
        geo, hist = [], []
        for di, d in enumerate(days):
            b, m = d["bars"], d["mins"]
            rth = b[(m >= 570) & (m < 970)]
            if len(rth) and hist:
                open_px = float(rth["open"].iloc[0])
                sig = R230.signal_poc_only(open_px, hist)
                if sig is not None:
                    rng_, poc, val, vah = hist[-1]
                    S = float(np.mean([p[0] for p in hist[-R229.DBS.RANGE_WINDOW:]]))
                    natural = abs(poc - open_px) * MARKETS[sym]["pv"] * sig["contracts"]
                    geo.append(dict(tday=d["tday"], open=open_px, poc=poc, val=val, vah=vah, prev_rng=rng_, S=S,
                                    sl=sig["sl"], tp=sig["tp"], contracts=sig["contracts"], reward=sig["reward"],
                                    capped=float(natural > sig["reward"] + 1e-9)))
            if profiles["rth"][di] is not None:
                hist.append(profiles["rth"][di])
    finally:
        R229.DB_FILE, R229.PV, R229.COST_PER_CONTRACT, R229.DBS.POINT_VALUE_MNQ = old
    tr = tr[tr["leg"] == "POC"].copy()
    tr["tday"] = pd.to_datetime(tr["tday"]).dt.normalize()
    geo = pd.DataFrame(geo)
    geo["tday"] = pd.to_datetime(geo["tday"]).dt.normalize()
    return days, tr, geo


def daily_frame(days):
    rows = []
    for d in days:
        b, m = d["bars"], d["mins"]
        rth = b[(m >= 570) & (m < 960)]
        on = b[(m >= 1080) | (m < 570)]
        if rth.empty:
            continue
        rows.append(dict(tday=pd.Timestamp(d["tday"]).normalize(), close=float(rth["close"].iloc[-1]),
                         high=float(rth["high"].max()), low=float(rth["low"].min()),
                         on_open=float(on["open"].iloc[0]) if len(on) else np.nan,
                         on_high=float(on["high"].max()) if len(on) else np.nan,
                         on_low=float(on["low"].min()) if len(on) else np.nan,
                         on_vol=float(on["volume"].sum()) if len(on) else np.nan))
    c = pd.DataFrame(rows).set_index("tday").sort_index()
    c["rng"] = c["high"] - c["low"]
    c["prev_close"], c["prev_high"], c["prev_low"] = c["close"].shift(1), c["high"].shift(1), c["low"].shift(1)
    c["rng_sma20"] = c["rng"].rolling(20).mean().shift(1)
    c["range_chg"] = c["rng"].pct_change(20).shift(1)
    c["sma20"] = c["close"].rolling(20).mean().shift(1)
    c["close_6ago"] = c["close"].shift(6)
    ret = np.log(c["close"]).diff()
    c["rv20"] = ret.rolling(20).std().shift(1)
    c["rv20_med250"] = c["rv20"].rolling(250, min_periods=120).median()
    c["on_rng"] = c["on_high"] - c["on_low"]
    c["on_med20"] = c["on_rng"].rolling(20).median().shift(1)
    c["on_vol_med20"] = c["on_vol"].rolling(20).median().shift(1)
    vix = pd.read_csv(os.path.join(HERE, "..", "data", "daily", "^VIX_yahoo_daily.csv"),
                      parse_dates=["date"]).set_index("date")["close"].sort_index()
    v = vix.shift(1)
    c["vix_prev"] = v.reindex(c.index, method="ffill")
    c["vix_med250"] = v.rolling(250, min_periods=120).median().reindex(c.index, method="ffill")
    c["vix_chg5"] = np.log(v / v.shift(5)).reindex(c.index, method="ffill")
    return c


def build_rows(sym):
    days, tr, geo = load_market(sym)
    c = daily_frame(days)
    t = tr.merge(geo, on="tday", how="inner", suffixes=("", "_sig"))
    assert (t["contracts"] == t["contracts_sig"]).all(), "geometry replay disagrees with the resolver"
    t = t.merge(c, left_on="tday", right_index=True, how="left").sort_values("tday").reset_index(drop=True)
    dn, S = t["direction"].astype(float), t["S"]
    f = pd.DataFrame(index=t.index)
    f["strength"] = (t["open"] - t["poc"]).abs() / S
    f["rr_plan"] = t["reward"] / RISK
    f["capped"] = t["capped"]
    f["dirn"] = dn
    f["open_in_va"] = ((t["open"] >= t["val"]) & (t["open"] <= t["vah"])).astype(float)
    f["va_width_S"] = (t["vah"] - t["val"]) / S
    f["poc_loc"] = (t["poc"] - t["prev_low"]) / (t["prev_high"] - t["prev_low"])
    f["prevclose_poc"] = dn * (t["prev_close"] - t["poc"]) / S
    f["gap_S"] = dn * (t["open"] - t["prev_close"]) / S
    f["on_rng_S"] = t["on_rng"] / S
    f["on_rng_rel"] = t["on_rng"] / t["on_med20"]
    f["on_move_S"] = dn * (t["open"] - t["on_open"]) / S
    f["open_vs_on_mid"] = dn * (t["open"] - (t["on_high"] + t["on_low"]) / 2) / S
    f["on_vol_rel"] = t["on_vol"] / t["on_vol_med20"]
    f["prev_rng_rel"] = t["prev_rng"] / t["rng_sma20"]
    f["rv_rel"] = t["rv20"] / t["rv20_med250"]
    f["trend20_S"] = dn * (t["prev_close"] - t["sma20"]) / S
    f["ret5_S"] = dn * (t["prev_close"] - t["close_6ago"]) / S
    f["S_bps"] = S / t["prev_close"] * 1e4
    f["vix_rel"] = t["vix_prev"] / t["vix_med250"]
    f["vix_chg5"] = t["vix_chg5"]
    f["range_chg"] = t["range_chg"]
    f["lead244"] = ((t["prev_rng"] < t["rng_sma20"]) & ~(t["rv20"] < t["rv20_med250"])).astype(float)
    win =(t["pnl"] > 0).astype(float)
    Rr = t["pnl"] / RISK
    f["trail_wr"] = win.shift(1).rolling(20, min_periods=20).mean()
    f["trail_R"] = Rr.shift(1).rolling(20, min_periods=20).mean()
    wd, mo = t["tday"].dt.weekday, t["tday"].dt.month
    f["dow_sin"], f["dow_cos"] = np.sin(2 * np.pi * wd / 5), np.cos(2 * np.pi * wd / 5)
    f["month_sin"], f["month_cos"] = np.sin(2 * np.pi * (mo - 1) / 12), np.cos(2 * np.pi * (mo - 1) / 12)
    f["is_nq"] = float(sym == "NQ")
    f["S"], f["dow"], f["month"] = S, wd, mo
    out = pd.concat([t[["tday", "entry_ts", "exit_ts", "direction", "contracts", "pnl", "outcome"]], f], axis=1)
    out["market"] = sym
    out["y"] = win.astype(int)
    out["R"] = Rr
    all_days = pd.DatetimeIndex(sorted({pd.Timestamp(d["tday"]).normalize() for d in days}))
    return out, all_days


# ---------------------------------------------------------------- models ----
def _ev_take(p, train, test):
    wins, losses = train[train["y"] == 1], train[train["y"] == 0]
    w = float((wins["R"] / wins["rr_plan"]).mean())
    l = float(losses["R"].mean())
    ev = p * w * test["rr_plan"].to_numpy() + (1 - p) * l
    return ev > 0


def predict(model, train, test):
    """Returns P(win) for test rows. train/test already restricted per the model's rules."""
    if model == "M0":
        sc = StandardScaler().fit(train[R198_FEATURES])
        clf = LogisticRegression(max_iter=2000).fit(sc.transform(train[R198_FEATURES]), train["y"])
        return clf.predict_proba(sc.transform(test[R198_FEATURES]))[:, 1]
    if model in ("M1", "MEGA"):
        sc = StandardScaler().fit(train[FEATURES])
        l1 = LogisticRegression(penalty="l1", solver="liblinear", C=0.1, max_iter=2000)
        p1 = l1.fit(sc.transform(train[FEATURES]), train["y"]).predict_proba(sc.transform(test[FEATURES]))[:, 1]
        if model == "M1":
            return p1
    hgb = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=40,
                                         l2_regularization=1.0, random_state=0)
    p2 = hgb.fit(train[FEATURES], train["y"]).predict_proba(test[FEATURES])[:, 1]
    return p2 if model == "M2" else (p1 + p2) / 2


def take_mask(model, train, test):
    if model == "M0":
        train = train[train["market"] == "NQ"]
    return _ev_take(predict(model, train, test), train, test)


# ------------------------------------------------------------- statistics ----
def boot_gt(a, b, seed=0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 5 or len(b) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    return float((rng.choice(a, (N_BOOT, len(a))).mean(1) > rng.choice(b, (N_BOOT, len(b))).mean(1)).mean())


def boot_pos(a, seed=0):
    a = np.asarray(a, float)
    if len(a) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    return float((rng.choice(a, (N_BOOT, len(a))).mean(1) > 0).mean())


def walk_forward(rows, model, label_perm_rng=None):
    """Per-fold results and pooled test rows (both markets) with the take flag."""
    folds, pooled = [], []
    for a, b in WF_FOLDS:
        train = rows[rows["tday"] < a]
        assert (pd.to_datetime(train["exit_ts"]) < a).all(), "a training label straddles the split"
        test = rows[(rows["tday"] >= a) & (rows["tday"] < b)]
        if label_perm_rng is not None:
            train = train.assign(y=label_perm_rng.permutation(train["y"].to_numpy()))
        take = take_mask(model, train, test)
        t = test.assign(take=take, fold=str(a.date()))
        nq = t[t["market"] == "NQ"]
        nt, ns = int(nq["take"].sum()), int((~nq["take"]).sum())
        row = dict(fold=f"{a.date()} -> {b.date()}", n_train=len(train), n_test_nq=len(nq), taken=nt, skipped=ns,
                   mean_taken=float(nq.loc[nq["take"], "pnl"].mean()) if nt else float("nan"),
                   mean_skipped=float(nq.loc[~nq["take"], "pnl"].mean()) if ns else float("nan"),
                   mean_all=float(nq["pnl"].mean()))
        row["status"] = "accepted" if (nt >= MIN_PER_SIDE and ns >= MIN_PER_SIDE) else \
            f"rejected: floor (taken={nt}, skipped={ns}, need >= {MIN_PER_SIDE} each)"
        folds.append(row)
        pooled.append(t.assign(accepted=row["status"] == "accepted"))
    return folds, pd.concat(pooled, ignore_index=True)


def lift(df):
    t, s = df.loc[df["take"], "pnl"], df.loc[~df["take"], "pnl"]
    return float(t.mean() - s.mean()) if len(t) and len(s) else float("nan")


def daily_R(trades, all_days):
    d = trades.groupby(pd.to_datetime(trades["exit_ts"]).dt.normalize())["pnl"].sum() / RISK
    return d.reindex(all_days, fill_value=0.0)


def dry_run(rows):
    print(f"\nRows after warm-up drop: {len(rows)} "
          f"({', '.join(f'{m} {int((rows.market == m).sum())}' for m in MARKETS)}); {rows.tday.min().date()} .. {rows.tday.max().date()}")
    print("Walk-forward folds (counts only):")
    for a, b in WF_FOLDS:
        tr = rows[rows["tday"] < a]
        te = rows[(rows["tday"] >= a) & (rows["tday"] < b)]
        print(f"  {a.date()} -> {b.date()}: train {len(tr)} (NQ {int((tr.market == 'NQ').sum())}) | "
              f"test NQ {int((te.market == 'NQ').sum())} ES {int((te.market == 'ES').sum())}")
    ho = rows[rows["tday"] >= OOS]
    print(f"  HOLDOUT >= {OOS.date()}: train {int((rows.tday < OOS).sum())} | test NQ {int((ho.market == 'NQ').sum())} "
          f"ES {int((ho.market == 'ES').sum())}")
    print("\nFeature ranges (min / median / max):")
    for c in FEATURES:
        x = rows[c]
        print(f"  {c:<15} {x.min():>9.3f} {x.median():>9.3f} {x.max():>9.3f}")
    print("\nFirst 2 NQ rows for hand-checking:")
    print(rows[rows.market == "NQ"][["tday", "entry_ts", "direction", "contracts", "strength", "rr_plan", "capped",
                                       "gap_S", "prev_rng_rel", "rv_rel", "vix_rel"]].head(2).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    built = {m: build_rows(m) for m in MARKETS}
    raw = pd.concat([built[m][0] for m in MARKETS], ignore_index=True)
    nan_counts = raw[FEATURES].isna().sum()
    rows = raw.dropna(subset=FEATURES).sort_values(["tday", "market"]).reset_index(drop=True)
    print(f"built in {time.time() - t0:.0f}s; raw trades {len(raw)}; NaN per feature (warm-up): "
          f"{ {k: int(v) for k, v in nan_counts.items() if v} }")
    if args.dry_run:
        dry_run(rows)
        sys.exit(0)

    days_nq = built["NQ"][1]
    results = dict(models={})
    base_nq = rows[rows["market"] == "NQ"]
    print(f"\nBase NQ trades {len(base_nq)}: win {base_nq['y'].mean():.3f}, mean ${base_nq['pnl'].mean():+.2f}")

    wf = {}
    for model in ("M0", "M1", "M2", "MEGA"):
        folds, pool = walk_forward(rows, model)
        acc = pool[pool["accepted"]]
        nq, es = acc[acc["market"] == "NQ"], acc[acc["market"] == "ES"]
        t, s = nq.loc[nq["take"], "pnl"].to_numpy(), nq.loc[~nq["take"], "pnl"].to_numpy()
        res = dict(folds=folds, n_taken=len(t), n_skipped=len(s), mean_taken=float(t.mean()), mean_skipped=float(s.mean()),
                   mean_all=float(nq["pnl"].mean()), lift_nq=lift(nq), p_gt=boot_gt(t, s), p_pos=boot_pos(t),
                   folds_pos=sum(1 for r in folds if r["status"] == "accepted" and r["mean_taken"] > r["mean_skipped"]),
                   n_acc=sum(1 for r in folds if r["status"] == "accepted"),
                   lift_es=lift(es), p_gt_es=boot_gt(es.loc[es["take"], "pnl"], es.loc[~es["take"], "pnl"]),
                   keep_nq=float(nq["take"].mean()))
        wf[model] = (res, pool)
        results["models"][model] = res
        print(f"\n=== {model} walk-forward ===")
        for r in folds:
            print(f"  {r['fold']}: NQ test {r['n_test_nq']} taken {r['taken']} skipped {r['skipped']} | "
                  f"taken ${r['mean_taken']:+.1f} skipped ${r['mean_skipped']:+.1f} all ${r['mean_all']:+.1f} | {r['status']}")
        print(f"  pooled NQ: taken {res['n_taken']} ${res['mean_taken']:+.2f} vs skipped {res['n_skipped']} "
              f"${res['mean_skipped']:+.2f} (all ${res['mean_all']:+.2f}) lift ${res['lift_nq']:+.2f} | "
              f"P(taken>skipped) {res['p_gt']:.4f} P(taken>0) {res['p_pos']:.4f} | folds+ {res['folds_pos']}/{res['n_acc']} "
              f"| ES lift ${res['lift_es']:+.2f} P {res['p_gt_es']:.3f}")

    # controls for the primary model
    res, pool = wf["MEGA"]
    real = res["lift_nq"]
    rng = np.random.default_rng(0)
    sh = []
    for i in range(N_SHUFFLE):
        _, p = walk_forward(rows, "MEGA", label_perm_rng=rng)
        p = p[p["accepted"] & (p["market"] == "NQ")]
        sh.append(lift(p))
    sh = np.array([x for x in sh if not np.isnan(x)])
    acc_nq = pool[pool["accepted"] & (pool["market"] == "NQ")]
    rnd = []
    for _ in range(N_RANDOM):
        parts = []
        for f_, g in acc_nq.groupby("fold"):
            k = int(g["take"].sum())
            m = np.zeros(len(g), bool)
            m[rng.choice(len(g), k, replace=False)] = True
            parts.append(g.assign(take=m))
        rnd.append(lift(pd.concat(parts)))
    rnd = np.array(rnd)
    res["shuffle_frac"] = float((sh >= real).mean())
    res["random_frac"] = float((rnd >= real).mean())
    print(f"\nControls (MEGA): label-shuffle {len(sh)} runs mean lift ${sh.mean():+.2f} sd ${sh.std():.2f}, "
          f"frac >= real {res['shuffle_frac']:.3f} | random filter frac >= real {res['random_frac']:.3f}")

    # one-month account metric on the pooled WF NQ days
    wf_days = days_nq[(days_nq >= WF_FOLDS[0][0]) & (days_nq < WF_FOLDS[-1][1])]
    g_all = gate(daily_R(acc_nq, wf_days).to_numpy())
    g_f = gate(daily_R(acc_nq[acc_nq["take"]], wf_days).to_numpy())
    sh_all = daily_R(acc_nq, wf_days); sh_f = daily_R(acc_nq[acc_nq["take"]], wf_days)
    res["gate_unfiltered"], res["gate_filtered"] = g_all, g_f
    res["sharpe_unfiltered"], res["sharpe_filtered"] = float(sh_all.mean() / sh_all.std()), float(sh_f.mean() / sh_f.std())
    print(f"One-month metric (WF days): unfiltered P(pass<=21d) {g_all['pass_21d']:.3f} daily Sharpe "
          f"{res['sharpe_unfiltered']:.4f} | MEGA-filtered {g_f['pass_21d']:.3f} Sharpe {res['sharpe_filtered']:.4f}")

    # final holdout, touched once, all models
    print("\n=== FINAL HOLDOUT (>= 2025-07-01, touched once) ===")
    train, test = rows[rows["tday"] < OOS], rows[rows["tday"] >= OOS]
    ho = {}
    for model in ("M0", "M1", "M2", "MEGA"):
        take = take_mask(model, train, test)
        tt = test.assign(take=take)
        nq = tt[tt["market"] == "NQ"]
        a, b = nq.loc[nq["take"], "pnl"], nq.loc[~nq["take"], "pnl"]
        ho[model] = dict(n_taken=len(a), n_skipped=len(b), mean_taken=float(a.mean()) if len(a) else float("nan"),
                         mean_skipped=float(b.mean()) if len(b) else float("nan"), mean_all=float(nq["pnl"].mean()),
                         p_pos=boot_pos(a), es_lift=lift(tt[tt["market"] == "ES"]))
        ho[model]["frame"] = nq
        print(f"  {model}: NQ taken {len(a)} ${ho[model]['mean_taken']:+.2f} skipped {len(b)} ${ho[model]['mean_skipped']:+.2f} "
              f"all ${ho[model]['mean_all']:+.2f} | P(taken>0) {ho[model]['p_pos']:.4f} | ES lift ${ho[model]['es_lift']:+.2f}")
    ho_days = days_nq[days_nq >= OOS]
    hq = ho["MEGA"]["frame"]
    gh_all, gh_f = gate(daily_R(hq, ho_days).to_numpy()), gate(daily_R(hq[hq["take"]], ho_days).to_numpy())
    print(f"  holdout one-month metric: unfiltered P(pass<=21d) {gh_all['pass_21d']:.3f} | MEGA {gh_f['pass_21d']:.3f}")

    checks = {
        "a_P(taken>skipped)>=0.95": res["p_gt"] >= 0.95,
        "b_P(taken>0)>=0.95": res["p_pos"] >= 0.95,
        "c_folds_pos>=6": res["folds_pos"] >= 6,
        "d_controls<=0.05": res["shuffle_frac"] <= 0.05 and res["random_frac"] <= 0.05,
        "e_ES_replication": res["lift_es"] > 0 and res["p_gt_es"] >= 0.80,
        "f_holdout": ho["MEGA"]["mean_taken"] > ho["MEGA"]["mean_skipped"] and ho["MEGA"]["mean_taken"] > ho["MEGA"]["mean_all"],
        "g_one_month_metric": g_f["pass_21d"] > g_all["pass_21d"],
    }
    complexity = dict(mega_lift=res["lift_nq"], m1_lift=results["models"]["M1"]["lift_nq"],
                      m0_lift=results["models"]["M0"]["lift_nq"],
                      mega_beats_simpler=res["lift_nq"] > max(results["models"]["M1"]["lift_nq"], results["models"]["M0"]["lift_nq"]))
    print("\n=== Filter-confirmed rule (MEGA, pre-registered) ===")
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"  VERDICT: {'FILTER CONFIRMED' if all(checks.values()) else 'NOT confirmed'} | complexity check: "
          f"MEGA ${complexity['mega_lift']:+.2f} vs L1 ${complexity['m1_lift']:+.2f} vs R198 ${complexity['m0_lift']:+.2f}")

    # ledger rows: filtered NQ trades, IS = pooled out-of-fold WF, OOS = holdout
    k0 = H.ledger_count()
    lrows = []
    names = {"MEGA": "POC leg mega-ML filter (L1 logit + HGB, 30 feats, NQ+ES pooled), EV rule, MNQ $300",
             "M1": "POC leg L1-logit filter (30 feats, NQ+ES pooled), EV rule, MNQ $300",
             "M0": "POC leg Round-198 logit filter (6 feats, NQ), EV rule, MNQ $300"}
    for i, model in enumerate(("MEGA", "M1", "M0"), start=1):
        _, pool_m = wf[model]
        is_tr = pool_m[pool_m["accepted"] & (pool_m["market"] == "NQ") & pool_m["take"]]
        oos_tr = ho[model]["frame"]
        tr_all = pd.concat([is_tr, oos_tr[oos_tr["take"]]], ignore_index=True)
        lrows.append(H.test_idea(names[model], tr_all[["entry_ts", "exit_ts", "contracts", "pnl"]],
                                 list(days_nq[days_nq >= WF_FOLDS[0][0]]), "MNQ", k0 + i))
    for h_ in ho.values():
        h_.pop("frame")
    results.update(controls=dict(shuffle_lifts_mean=float(sh.mean()), shuffle_lifts_sd=float(sh.std())),
                   holdout=ho, holdout_gate=dict(unfiltered=gh_all, mega=gh_f), checks=checks, complexity=complexity,
                   ledger_rows=lrows)
    print("\nLedger rows (append after review):")
    for line in H.ledger_rows(lrows, "Round 245 (pre-registered, POC mega-ML)", "COMMIT", date="2026-09-30"):
        print(line)
    with open(os.path.join(HERE, "round245_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"\nSaved round245_results.json ({time.time() - t0:.0f}s)")
