"""
Round 336 (2026-10-03, PRE-REGISTERED; ONE ledger row, k + 1): walk-forward gradient boosting on 24 causal 1-minute BTCUSD features, trading only when the predicted move beats the cost. Research only.

Round 335 tested single signals (0 of 128). A model reading all the 1-minute features at once can find combinations a single threshold cannot; it is the last family worth a fair, pre-registered try on this data. Ledger checked first (k = 2037): walk-forward ML exists for futures and CFD bracket labels (Rounds 137, 149, 228, 271); on BTC minute data it does not.
DATA / EXECUTION: exactly Round 335's (forex/early_mt5/data/BTCUSD_M1_ticks247.parquet; entry at the next minute's open, long at the ask / short at the bid; exit at the close of minute i+H, long at the bid / short at the ask; 6.5 bp commission; valid only if all minutes i..i+H are present and minutes i+1 and i+H share a server day; one position at a time). Round 335's trades_for is reused.
FEATURES at the close of minute i (24, all past or current; the docstring first said about 30, a miscount fixed in the dry run): log returns over 1, 2, 3, 5, 10, 15, 30, 60, 120, 240 minutes (bp); std of 1-minute returns over 15, 60, 240 minutes (bp) and vol15 / vol240; tick_volume now / mean of 60 and mean of 5 / mean of 60; spread (ask close - bid close, bp of mid) and its ratio to its 60-minute mean; position of the close in the 60- and 240-minute high-low range; the last minute's high-low range / vol60; server hour (sin, cos) and day of week. Rows need 240 continuous minutes behind them.
TARGET: forward mid return in bp from the next minute's mid open to the mid close of minute i+H, H in (15, 30, 60), winsorized at +/-300 bp for training only. MODEL: sklearn HistGradientBoostingRegressor(max_depth=4, learning_rate=0.05, max_iter=200, l2_regularization=1.0, min_samples_leaf=200, random_state=336), fixed, not tuned; trained on every 2nd minute of the training window.
WALK-FORWARD: refit every 1 January and 1 July from 2024-01-01 on, expanding window from 2021-10-01, training labels purged (rows whose window ends after the refit date are dropped); each model predicts the next six months; the first refit date, 2024-01-01, leaves the 2021-10..2023-12 data as the first training window, so OUT-OF-SAMPLE = 2024-01-01..2026-10-03 and nothing earlier is scored.
RULE: trade when |prediction| >= tau bp, long if positive, short if negative, tau in (4, 6, 8, 10); H in (15, 30, 60): 12 hypotheses, each pooled over the whole test period.
CANDIDATE (fixed now): at least 300 trades, mean net >= +1.0 bp, day-clustered bootstrap P(mean > 0) >= 1 - 0.05/12 = 0.9958 (5,000 draws, seed 336), AND positive mean net in each of 2024, 2025 and 2026. Not widened after the run: no new features, H, tau, model sizes, targets or instruments to rescue a failure. ETHUSD is not pulled: it is the confirmation set for a candidate.
DRY-RUN COUNTS (rows only, no model trained): usable rows (all 24 features present, label valid): H15 1,717,819, H30 1,686,435, H60 1,624,725 of 2,505,029 minutes; training rows (every 2nd minute, purged) by refit date, H30: 2024-01-01 348,666; 2024-07-01 418,647; 2025-01-01 513,856; 2025-07-01 610,898; 2026-01-01 703,951; 2026-07-01 797,621.
Features: r1, r2, r3, r5, r10, r15, r30, r60, r120, r240, vol15, vol60, vol240, volratio, tv_now, tv_5, spr, spr_ratio, pos60, pos240, rng1, hsin, hcos, dow.
POWER: the test period has about 1.1M usable minutes; a model with a real edge would need predictions that clear 4-10 bp when the typical 15-60 minute move is 18-62 bp (sd); with the 6.5 bp commission + 3 bp spread the gross edge per trade must exceed about 9.5 bp. The number of trades per cell is reported; fewer than 300 cannot be a candidate. Walk-forward with fixed hyperparameters means no selection on the test period.
"""
import os, sys, json
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import round335_btc_1min_signal_battery as B

HS, TAUS = (15, 30, 60), (4.0, 6.0, 8.0, 10.0)
REFITS = [pd.Timestamp(f"{y}-{m:02d}-01") for y in (2024, 2025, 2026) for m in (1, 7)]
END = pd.Timestamp("2026-10-04")


def feature_frame(t, a):
    c = pd.Series(a["close"]); n = len(t)
    cont240 = np.r_[np.zeros(240, dtype=bool), (t[240:] - t[:-240]) == 240 * 60]
    r1 = np.log(c / c.shift(1)) * 1e4
    X = {}
    for k in (1, 2, 3, 5, 10, 15, 30, 60, 120, 240):
        X[f"r{k}"] = np.log(c / c.shift(k)) * 1e4
    for k in (15, 60, 240):
        X[f"vol{k}"] = r1.rolling(k, min_periods=int(k * .75)).std()
    X["volratio"] = X["vol15"] / X["vol240"]
    tv = pd.Series(a["tick_volume"])
    X["tv_now"] = tv / tv.rolling(60, min_periods=45).mean()
    X["tv_5"] = tv.rolling(5, min_periods=4).mean() / tv.rolling(60, min_periods=45).mean()
    mid = (c + pd.Series(a["ask_close"])) / 2
    spr = (pd.Series(a["ask_close"]) - c) / mid * 1e4
    X["spr"] = spr
    X["spr_ratio"] = spr / spr.rolling(60, min_periods=45).mean()
    hi, lo = pd.Series(a["high"]), pd.Series(a["low"])
    for k in (60, 240):
        mx, mn = hi.rolling(k, min_periods=int(k * .75)).max(), lo.rolling(k, min_periods=int(k * .75)).min()
        X[f"pos{k}"] = (c - mn) / (mx - mn)
    X["rng1"] = (hi - lo) / c * 1e4 / X["vol60"]
    ts = pd.to_datetime(t, unit="s")
    hr = ts.hour + ts.minute / 60
    X["hsin"], X["hcos"] = pd.Series(np.sin(2 * np.pi * hr / 24)), pd.Series(np.cos(2 * np.pi * hr / 24))
    X["dow"] = pd.Series(ts.dayofweek, dtype=float)
    F = pd.DataFrame(X); F = F.where(pd.Series(cont240))
    return F


def targets(t, a, H):
    n = len(t)
    mo = (a["open"] + a["ask_open"]) / 2; mc = (a["close"] + a["ask_close"]) / 2
    y = np.full(n, np.nan)
    e = np.arange(n - H) + 1; x = np.arange(n - H) + H
    ok = ((t[x] - t[np.arange(n - H)]) == 60 * H) & ((t[e] // 86400) == (t[x] // 86400))
    y[:n - H][ok] = (mc[x[ok]] / mo[e[ok]] - 1) * 1e4
    return y


def main(dry):
    t, a = B.load(); F = feature_frame(t, a); ts = pd.to_datetime(t, unit="s")
    if dry:
        for H in HS:
            y = targets(t, a, H); ok = F.notna().all(axis=1).values & ~np.isnan(y)
            print(f"H={H}: usable rows {int(ok.sum()):,} of {len(t):,}; train rows by refit (every 2nd minute, purged):",
                  {str(r.date()): int((ok & (ts < r - pd.Timedelta(minutes=H + 1)) & (np.arange(len(t)) % 2 == 0)).sum()) for r in REFITS})
        print("features:", list(F.columns), len(F.columns)); return
    rng = np.random.default_rng(336); out = {}; rows = []
    for H in HS:
        y = targets(t, a, H); usable = F.notna().all(axis=1).values & ~np.isnan(y)
        pred = np.full(len(t), np.nan)
        for j, r in enumerate(REFITS):
            end = REFITS[j + 1] if j + 1 < len(REFITS) else END
            tr = np.flatnonzero(usable & (ts < r - pd.Timedelta(minutes=H + 1)) & (np.arange(len(t)) % 2 == 0))
            te = np.flatnonzero(F.notna().all(axis=1).values & (ts >= r) & (ts < end))
            m = HistGradientBoostingRegressor(max_depth=4, learning_rate=0.05, max_iter=200, l2_regularization=1.0, min_samples_leaf=200, random_state=336)
            m.fit(F.values[tr], np.clip(y[tr], -300, 300))
            pred[te] = m.predict(F.values[te]); print(f"H={H} refit {r.date()}: train {len(tr):,}, test {len(te):,}, pred sd {np.nanstd(pred[te]):.2f} bp", flush=True)
        for tau in TAUS:
            idx = np.flatnonzero(np.abs(pred) >= tau); s = np.sign(pred[idx])
            day, net, gross = B.trades_for(idx, s, H, t, a, "follow")
            yr = pd.Series(net).groupby(np.asarray(day.year)).mean().to_dict()
            mean, P = B.boot(day, net, rng) if len(net) > 20 else (float(np.mean(net)) if len(net) else np.nan, 0.0)
            cand = bool(len(net) >= 300 and mean >= 1.0 and P >= 1 - .05 / 12 and all(yr.get(y_, -1) > 0 for y_ in (2024, 2025, 2026)))
            rows.append(dict(H=H, tau=tau, n=int(len(net)), net=float(mean), gross=float(np.mean(gross)) if len(net) else np.nan, P=P, by_year={int(k): round(float(v), 2) for k, v in yr.items()}, candidate=cand))
            print(f"H={H} tau={tau:g}: {rows[-1]}", flush=True)
    print("candidates:", [(r["H"], r["tau"]) for r in rows if r["candidate"]])
    json.dump(rows, open(os.path.join(HERE, "round336_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
