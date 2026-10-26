"""PREREG_SLOW_READ scoring (written and hashed before any trade of the test exists). Single look after all 100 days are logged.
Each logged trade is replayed on GC futures with the app convention (fill at the next minute's open one tick worse; stop exit one tick worse;
target at its price; stop and target in the same minute = stop; still open at 17:00 = closed at that minute's close). The mirror trade is the
same fill minute, distances and rules on the other side. Random-side P = share of 20,000 random own / mirror assignments whose mean R is at
least the observed mean. Usage (from ema12): python score_slow.py"""
import json
import numpy as np, pandas as pd
import blind_png as B

L = pd.read_csv("BLIND_LOG_SLOW.csv", dtype={"hhmm": str})
sched = pd.read_csv("BLIND_SLOW_2024_25.csv")
assert list(L.date) == list(sched.date), "log is not the full registered schedule in calendar order"
T = L[L.side.isin(["L", "S"])].reset_index(drop=True)


def outcome(g, sd, sdist, tdist):
    fill = g.open.iloc[0] + sd * 0.1; sl, tp = fill - sd * sdist, fill + sd * tdist
    for _, b in g.iterrows():
        if (b.low <= sl) if sd > 0 else (b.high >= sl): return -1 - 0.1 / sdist
        if (b.high >= tp) if sd > 0 else (b.low <= tp): return tdist / sdist
    return sd * (g.close.iloc[-1] - fill) / sdist


own, mir = [], []
for r in T.itertuples():
    sd = 1 if r.side == "L" else -1; sdist, tdist = abs(r.entry - r.stop), abs(r.target - r.entry)
    g = B.load_fut(r.date, pd.Timestamp(f"{r.date} 17:00")); g = g[g.index > pd.Timestamp(f"{r.date} {r.hhmm}")]
    own.append(outcome(g, sd, sdist, tdist)); mir.append(outcome(g, -sd, sdist, tdist))
own, mir = np.array(own), np.array(mir)
rng = np.random.default_rng(20261027)
flips = np.where(rng.random((20000, len(own))) < 0.5, own, mir).mean(axis=1)
p = float((flips >= own.mean()).mean())
secs = [e.get("secs") for e in map(json.loads, open("replay_events.jsonl", encoding="utf-8"))
        if e.get("event") in ("trade", "no_trade") and e.get("mode") == "registered" and e.get("day") in set(sched.date) and e.get("secs") is not None]
pd.DataFrame({"date": T.date, "side": T.side, "R": own.round(3), "mirror_R": mir.round(3)}).to_csv("SLOW_RESULTS.csv", index=False)
print("days %d, trades %d, no-trade days %d; median decision time %s s" % (len(L), len(T), len(L) - len(T), int(np.median(secs)) if secs else "n/a"))
print("wins %d (%.0f%%), mean R %+.3f, sum %+.2f R | mirror mean %+.3f | random-side P %.4f" % ((own > 0).sum(), 100 * (own > 0).mean(), own.mean(), own.sum(), mir.mean(), p))
h = len(own) // 2
print("first half mean R %+.3f (n %d), second half %+.3f (n %d)" % (own[:h].mean(), h, own[h:].mean(), len(own) - h))
if len(own) < 40: print("VERDICT: INCONCLUSIVE (fewer than 40 trades)")
else: print("VERDICT:", "SUPPORTED" if (own.mean() > 0 and p <= 0.05) else "NOT SUPPORTED")
