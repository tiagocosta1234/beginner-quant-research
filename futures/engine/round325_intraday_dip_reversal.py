"""
Round 325 (2026-10-03, PRE-REGISTERED; the 12 cells are logged as ONE ledger row, k + 1): multi-hour INTRADAY dip reversal on ES and NQ -- the intraday cousin of the confirmed daily dip-reversal lead.

Standing goal: find something better than the current best (coin-flip bold play ~40% 1-Step pass; the dip-reversal lead +35 bp a trade but only ~20 signals a year). Mechanism: a 1-3 hour fall of >= 2 sigma on an index
is followed by a rebound (liquidity-provision premium, same story as the daily 3-day dip); it fires several times a week instead of a few times a year, which is what the pass-speed gate lacks. Ledger checked first (k = 2027):
1-minute mean reversion (Rounds 309-310: zero gross), hourly momentum (125-126), 30-minute slot scans (Rounds 298 / 421 / 319) exist; a >= 2 sigma multi-hour fall followed by a 1-2 hour long hold does not.

DATA: Databento 1-minute ES, NQ (2020-01-02..2026-09-25), RTH 09:30-15:59 ET. SIGMA: standard deviation of non-overlapping 30-minute returns over the previous 20 sessions (strictly past). z_L = (close at t / close at t-L - 1) / (sigma30 x sqrt(L/30)).
DECISION TIMES: every 30 minutes from 10:30 to 14:30 ET (the close of the bar before t is the signal price, the ENTRY is the open of the bar stamped t); L in {60, 120, 180} minutes (a decision time needs t - L >= 09:30).
RULES: DIP_LONG: first decision time of the day with z_L <= -2 -> long; SPIKE_SHORT: first with z_L >= +2 -> short. One trade a day per cell. HOLD M in {60, 120} minutes (exit at the close of the last minute, capped at 15:59).
CELLS: L (3) x M (2) x rule (2) = 12, pooled over ES + NQ. Net bp = direction x return x 1e4 - 1.0 (ES / NQ round trip, fixed now). Placebo: the same entries with the opposite direction, reported.
SPLIT: IS 2020-2023, OOS 2024-2026-09. Statistic: mean net bp per trade, date-clustered bootstrap (5,000 draws, seed 325).
CANDIDATE (fixed now): IS mean > 0 with P >= 0.95 AND OOS mean > 0 with P >= 1 - 0.05/12 = 0.9958 AND the placebo OOS mean <= 0. Not widened after the run: no new thresholds, horizons, instruments or filters to rescue a failure.
DRY-RUN COUNTS (trade counts only; one example trade hand-checked against the bars: ES 2020-02-25, L = 60, decision 11:00, 60-minute fall -102.9 bp, entry = the 11:00 bar open 3,199.0): pooled ES + NQ trades IS / OOS per
cell: L60 DIP_LONG 497 / 349 (523 days), L60 SPIKE_SHORT 404 / 305, L120 DIP_LONG 336 / 227, L120 SPIKE_SHORT 266 / 172, L180 DIP_LONG 236 / 157, L180 SPIKE_SHORT 182 / 113 (M = 60 and 120 share entries). About one trade every 2-3 sessions
per instrument for L = 60, the frequency the daily dip lead lacks.
POWER: per-trade sd about 30-40 bp over 1-2 hours, so the s.e. of an IS mean is about 1.6-2.5 bp and of an OOS mean 1.9-3 bp: an edge above about +5 bp net is detectable; the OOS bar P >= 0.9958 needs about +8 bp at the smallest cells.
"""
import os, sys, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import round321_long_bias_bold_play as R

IS_END = pd.Timestamp("2023-12-31")
COST = 1.0
LS, MS = (60, 120, 180), (60, 120)
DEC = list(range(10 * 60 + 30, 14 * 60 + 31, 30))      # minutes after midnight


def build(sym):
    b = R.load(sym)
    out = []
    sig30 = []
    days = []
    for d, x in b.groupby(b.index.normalize()):
        if len(x) < 380 or x.index[0].hour != 9 or x.index[0].minute != 30:
            continue
        m = (x.index.hour * 60 + x.index.minute).values
        c, o = x.c.values, x.o.values
        # 30-minute non-overlapping returns from the closes at 10:00, 10:30, ... vs 09:30 open
        marks = [570 + 30 * i for i in range(14)]          # 09:30 .. 16:00
        px = []
        for mk in marks[:-1]:
            j = np.flatnonzero(m == mk); px.append(o[j[0]] if len(j) else np.nan)
        px.append(c[-1])
        px = np.array(px); r30 = np.diff(np.log(px))
        days.append((d, m, o, c, r30))
    sig = pd.Series({d: np.nanstd(r) for d, _, _, _, r in days})
    sg = sig.rolling(20).mean().shift(1)           # mean of the previous 20 sessions' 30-minute std
    rows = []
    for d, m, o, c, _ in days:
        s = sg.get(d, np.nan)
        if not np.isfinite(s) or d < pd.Timestamp("2020-01-02"):
            continue
        idx = {mm: i for i, mm in enumerate(m)}
        for L in LS:
            for rule in ("DIP_LONG", "SPIKE_SHORT"):
                for M_ in MS:
                    hit = None
                    for t in DEC:
                        if t - L < 570 or t not in idx or (t - 1) not in idx or (t - 1 - L) not in idx and (t - L) not in idx:
                            continue
                        i_sig = idx[t - 1]; i_back = idx.get(t - L - 1, idx.get(t - L))
                        if i_back is None: continue
                        rl = c[i_sig] / c[i_back] - 1
                        z = rl / (s * np.sqrt(L / 30))
                        if (rule == "DIP_LONG" and z <= -2) or (rule == "SPIKE_SHORT" and z >= 2):
                            hit = t; break
                    if hit is None:
                        continue
                    i0 = idx[hit]
                    t_end = min(hit + M_ - 1, 959)
                    i1 = idx.get(t_end)
                    if i1 is None:
                        k = np.flatnonzero(m <= t_end); i1 = k[-1]
                    ret = c[i1] / o[i0] - 1
                    dirn = 1 if rule == "DIP_LONG" else -1
                    rows.append(dict(date=d, L=L, M=M_, rule=rule, net=dirn * ret * 1e4 - COST, plc=-dirn * ret * 1e4 - COST))
    return pd.DataFrame(rows)


def boot(x, rng, col="net"):
    g = x.groupby("date")[col].agg(["sum", "count"])
    s_, c_ = g["sum"].values, g["count"].values
    idx = rng.integers(0, len(g), (5000, len(g)))
    m = s_[idx].sum(1) / c_[idx].sum(1)
    return float(x[col].mean()), float((m > 0).mean())


def main(dry):
    df = pd.concat([build(s).assign(sym=s) for s in ("ES", "NQ")])
    rng = np.random.default_rng(325)
    out = {}
    for L in LS:
        for M_ in MS:
            for rule in ("DIP_LONG", "SPIKE_SHORT"):
                x = df[(df.L == L) & (df.M == M_) & (df.rule == rule)]
                a, b = x[x.date <= IS_END], x[x.date > IS_END]
                key = f"L{L}|M{M_}|{rule}"
                if dry:
                    print(key, "trades IS", len(a), "OOS", len(b), "days", x.date.nunique()); continue
                mi, pi = boot(a, rng); mo, po = boot(b, rng); pl = b.plc.mean()
                out[key] = dict(n_is=len(a), n_oos=len(b), is_bp=mi, is_P=pi, oos_bp=mo, oos_P=po, placebo_oos=float(pl),
                                candidate=bool(mi > 0 and pi >= .95 and mo > 0 and po >= 1 - .05 / 12 and pl <= 0))
                print(key, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[key].items()}, flush=True)
    if not dry:
        print("candidates:", [k for k, v in out.items() if v["candidate"]])
        json.dump(out, open(R.result_path(HERE, "round325_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
