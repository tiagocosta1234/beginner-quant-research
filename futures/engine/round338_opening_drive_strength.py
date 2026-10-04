"""
Round 338 (2026-10-04, PRE-REGISTERED; ONE ledger row, k + 1): is the 10:30 follow-the-opening-drive effect concentrated in STRONG drives?

Background (Rounds 324, 332, 333, journal 2026-10-03): following the move since 09:30, entered at 10:30 in the deployed table, earns about +0.06 to +0.08 R a trade over a coin flip on MT5 US100 / US500 / US2000 (+0.05 pooled over four indices), nothing on US30, strong in 2023-25 and negative in 2026.
Refinement with a mechanism: trend days carry the continuation; a weak drift after a flat first hour is noise. So the excess should be larger when the drive is large relative to the recent range.
DISCLOSURE (the honest limit): this is a refinement on the SAME four indices and the same sessions the lead was found on; there is no untouched sample (ETH / BTC are not equity). A pass is therefore a lead, not a result; the guards are ONE condition fixed here with no free parameter, a mechanism, and a consistency requirement across instruments.
DATA: MT5 M1 bid / ask, real fills (ROUND_DATA=mt5broker, ROUND_FILLS=ask, set here): US100.cash, US500.cash, US30.cash, US2000.cash; Round 324's day_table_T at T = 10:30 unchanged; sessions as in Round 333 (2021-10-29 / 2022-02-08 to 2026-10-02).
STRENGTH: S = |10:30 bar open - 09:30 open| / the mean 09:30-16:00 high - low of the previous 20 sessions (the table's own range). STRONG day: S >= the median of S over the previous 120 sessions (needs at least 60; strictly past, no look-ahead); WEAK otherwise. Days with a zero move are dropped.
DAILY EXCESS (Round 333's statistic): excess = mean over the five table targets k of 0.5 x (R_follow - R_opposite) for that session. TEST STATISTIC: D = mean excess on STRONG days - mean excess on WEAK days, pooled over the four indices (one row per instrument-day), date-clustered bootstrap, 5,000 draws, seed 338.
CANDIDATE (fixed now): D > +0.03 R AND bootstrap P(D > 0) >= 0.975 AND mean excess on STRONG days > +0.05 R AND positive in both halves (before / from 2024-01-01) AND D > 0 on at least 3 of the 4 indices. Not widened after the run: no other strength definition, window, threshold, time, or instrument.
POWER (honest): the s.e. of one subgroup mean over the pooled sample (about 2,300 days each) is about 0.025 R, and of D about 0.035 R, so P >= 0.975 needs D of about +0.07 R: a pass means the effect is mostly in strong drives; a miss is inconclusive for a small difference.
DRY-RUN COUNTS (days only, no excess R printed): US100.cash 1,149 days from 2022-01-31 (strong 570, weak 579; 470 before 2024); US500.cash 1,147 (573 / 574; 471); US30.cash 1,147 (566 / 581; 469); US2000.cash 1,081 from 2022-05-05 (538 / 543; 404). The sample starts three to four months later than Round 333 because the strength median needs 60 prior sessions.
POWER: about 4,500 pooled days, strong / weak about 2,250 each; s.e. of each subgroup mean about 0.025 R and of D about 0.035 R (per-index D has an s.e. of about 0.07 R, so the 3-of-4 consistency limit is a weak filter on its own).
"""
import os, sys, json
os.environ["ROUND_DATA"] = "mt5broker"; os.environ["ROUND_FILLS"] = "ask"
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
import round321_long_bias_bold_play as R
import round324_post_open_drive_entry as Q

T = Q.TS["1030"]; KS = R.KS; SPLIT = pd.Timestamp("2024-01-01")
NAME = {"NQ": "US100.cash", "ES": "US500.cash", "YM": "US30.cash", "RTY": "US2000.cash"}


def frame(sym):
    df = Q.day_table_T(sym, T); df = df[df.move != 0].copy()
    b = R.load(sym)
    g = b.groupby(b.index.normalize())
    rng = (g.h.max() - g.l.min())
    r20 = rng.rolling(20).mean().shift(1).reindex(df.index)
    df["S"] = df.move.abs() / r20
    df["med"] = df.S.rolling(120, min_periods=60).median().shift(1)
    s = np.sign(df.move.values); ex = []
    for k in KS:
        Rl, Rs = df[f"R_1_{k}"].values, df[f"R_-1_{k}"].values
        ex.append(0.5 * (np.where(s > 0, Rl, Rs) - np.where(s > 0, Rs, Rl)))
    df["excess"] = np.mean(ex, axis=0)
    df = df.dropna(subset=["S", "med"]); df["strong"] = df.S >= df.med
    df["sym"] = sym
    return df[["excess", "strong", "sym"]].reset_index().rename(columns={"index": "date"})


def diff_boot(x, rng):
    g = x.assign(sw=x.excess * x.strong, sc=x.strong.astype(float), ww=x.excess * (~x.strong), wc=(~x.strong).astype(float)).groupby("date")[["sw", "sc", "ww", "wc"]].sum()
    v = g.values; idx = rng.integers(0, len(v), (5000, len(v)))
    t = v[idx].sum(1)                                       # columns: strong sum, strong n, weak sum, weak n
    d = t[:, 0] / t[:, 1] - t[:, 2] / t[:, 3]
    mS = x[x.strong].excess.mean(); mW = x[~x.strong].excess.mean()
    return float(mS), float(mW), float(mS - mW), float((d > 0).mean())


def main(dry):
    rng = np.random.default_rng(338); fr = {s: frame(s) for s in NAME}
    if dry:
        for s, d in fr.items():
            print(f"{NAME[s]}: {len(d)} days from {d.date.min().date()} to {d.date.max().date()}, strong {int(d.strong.sum())}, weak {int((~d.strong).sum())}, before 2024 {(d.date < SPLIT).sum()}")
        return
    x = pd.concat(fr.values()); out = {}
    mS, mW, D, P = diff_boot(x, rng)
    a, b = x[x.date < SPLIT], x[x.date >= SPLIT]
    ha, hb = diff_boot(a, rng), diff_boot(b, rng)
    per = {NAME[s]: diff_boot(d, rng) for s, d in fr.items()}
    out["pooled"] = dict(n=len(x), strong_excess=mS, weak_excess=mW, D=D, P=P, first=dict(S=ha[0], W=ha[1], D=ha[2]), second=dict(S=hb[0], W=hb[1], D=hb[2]))
    out["per_index"] = {k: dict(strong=v[0], weak=v[1], D=v[2], P=v[3]) for k, v in per.items()}
    pos = sum(1 for v in per.values() if v[2] > 0)
    out["candidate"] = bool(D > 0.03 and P >= 0.975 and mS > 0.05 and ha[2] > 0 and hb[2] > 0 and pos >= 3)
    print("pooled:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out["pooled"].items() if not isinstance(v, dict)}, "first half", {k: round(v, 3) for k, v in out["pooled"]["first"].items()}, "second half", {k: round(v, 3) for k, v in out["pooled"]["second"].items()})
    for k, v in out["per_index"].items():
        print(" ", k, {a_: round(b_, 3) for a_, b_ in v.items()})
    print("CANDIDATE:", out["candidate"], "| indices with D > 0:", pos, "of 4")
    json.dump(out, open(os.path.join(HERE, "round338_results_mt5broker_ask.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
