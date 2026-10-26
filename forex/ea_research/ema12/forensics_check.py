"""Checks on trade_forensics.py (post-hoc, descriptive): (1) the 'target hit later after the stop' rate for the MIRROR side (same distances,
opposite side): if it is as high, the stat says the stops are small against the day's range, not that his direction was right;
(2) what-if minimum stops of k x the pre-entry noise (stop = max(his stop, k x noise)), target at 1:1 and at his own reward:risk,
for his side and the mirror side, on MT5 broker bid/ask. Usage: python forensics_check.py"""
import numpy as np, pandas as pd
import spot_vs_futures as V

L = pd.read_csv("BLIND_LOOK2_FOR_SCORE.csv", dtype={"hhmm": str}); L = L[L.side.isin(["L", "S"])]
F = pd.read_csv("TRADE_FORENSICS.csv")
noise = dict(zip(F.date, F.noise))
cache = {}
def sim(r, sd, sdist, tdist):
    s = cache.setdefault(r.date, V.spot_day(r.date))
    t = pd.Timestamp(f"{r.date} {r.hhmm}"); after = s[(s.index >= t + pd.Timedelta(minutes=1)) & (s.index <= pd.Timestamp(f"{r.date} 17:00"))]
    fill = after.ao.iloc[0] if sd > 0 else after.bo.iloc[0]
    R, kind, tx = V.play(after, sd, sdist, tdist, "bh" if sd > 0 else "ah", "bl" if sd > 0 else "al", fill, 0.0)
    later = after[after.index > tx]; tgt = fill + sd * tdist
    hit = bool(((later.bh >= tgt).any() if sd > 0 else (later.al <= tgt).any())) if kind == "SL" and len(later) else None
    return R, kind, hit
own, mir = [], []
for r in L.itertuples():
    if r.date not in noise or not noise[r.date] == noise[r.date]: continue
    sd = 1 if r.side == "L" else -1; sdist, tdist = abs(r.entry - r.stop), abs(r.target - r.entry)
    own.append(sim(r, sd, sdist, tdist)); mir.append(sim(r, -sd, sdist, tdist))
for lab, X in (("his side", own), ("MIRROR side", mir)):
    sl = [x for x in X if x[1] == "SL"]
    print("%-12s stopped %2d, target reached later %2d (%.0f%%); wins %.0f%%, mean R %+.3f" % (lab, len(sl), sum(x[2] for x in sl), 100 * np.mean([x[2] for x in sl]),
          100 * np.mean([x[0] > 0 for x in X]), np.mean([x[0] for x in X])))
print("\nWHAT-IF minimum stop = k x pre-entry 1-minute noise (stop = max(his, k x noise)); his side vs mirror; MT5 broker bid/ask")
rng = np.random.default_rng(20261026)
for k in (0, 3, 5, 7):
    for tmode in ("his R:R", "1:1"):
        a, b = [], []
        for r in L.itertuples():
            nz = noise.get(r.date)
            if nz is None or nz != nz: continue
            sd = 1 if r.side == "L" else -1; s0, t0 = abs(r.entry - r.stop), abs(r.target - r.entry)
            sdist = max(s0, k * nz); tdist = sdist * (t0 / s0 if tmode == "his R:R" else 1.0)
            a.append(sim(r, sd, sdist, tdist)[0]); b.append(sim(r, -sd, sdist, tdist)[0])
        a, b = np.array(a), np.array(b)
        p = float((np.where(rng.random((20000, len(a))) < 0.5, a, b).mean(axis=1) >= a.mean()).mean())
        print("  k %d, target %-7s  his: wins %3.0f%% mean R %+.3f | mirror: wins %3.0f%% mean R %+.3f | his - mirror %+.3f  P %.3f" % (
            k, tmode, 100 * (a > 0).mean(), a.mean(), 100 * (b > 0).mean(), b.mean(), a.mean() - b.mean(), p))
