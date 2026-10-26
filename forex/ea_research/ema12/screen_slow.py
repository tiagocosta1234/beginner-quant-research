"""PREREG_SLOW_READ Amendment 1: one-night screen on the first 40 scheduled days (own side only, futures app convention as score_slow.py).
GO iff >= 20 trades AND mean R >= +0.20 AND the 40th day was logged before 01:00 local clock. Usage (from ema12): python screen_slow.py"""
import json
import numpy as np, pandas as pd
import blind_png as B

sched = list(pd.read_csv("BLIND_SLOW_2024_25.csv").date[:40])
L = pd.read_csv("BLIND_LOG_SLOW.csv", dtype={"hhmm": str})
assert list(L.date[:len(sched)]) == sched[:len(L)], "log does not follow the schedule"
if len(L) < 40: raise SystemExit("screen not finished: %d of 40 days logged -> NO-GO for tomorrow" % len(L))
L = L.iloc[:40]; T = L[L.side.isin(["L", "S"])]
R = []
for r in T.itertuples():
    sd = 1 if r.side == "L" else -1; sdist, tdist = abs(r.entry - r.stop), abs(r.target - r.entry)
    g = B.load_fut(r.date, pd.Timestamp(f"{r.date} 17:00")); g = g[g.index > pd.Timestamp(f"{r.date} {r.hhmm}")]
    fill = g.open.iloc[0] + sd * 0.1; sl, tp = fill - sd * sdist, fill + sd * tdist; out = None
    for _, b in g.iterrows():
        if (b.low <= sl) if sd > 0 else (b.high >= sl): out = -1 - 0.1 / sdist; break
        if (b.high >= tp) if sd > 0 else (b.low <= tp): out = tdist / sdist; break
    R.append(out if out is not None else sd * (g.close.iloc[-1] - fill) / sdist)
R = np.array(R)
ev = [e for e in map(json.loads, open("replay_events.jsonl", encoding="utf-8")) if e.get("mode") == "registered" and e.get("day") == sched[-1] and e.get("event") in ("trade", "no_trade")]
t40 = ev[0]["pc_time"] if ev else "?"; on_time = bool(ev) and t40 < "2026-10-27 01:00:00"
secs = [e.get("secs") for e in map(json.loads, open("replay_events.jsonl", encoding="utf-8")) if e.get("mode") == "registered" and e.get("day") in set(sched) and e.get("event") in ("trade", "no_trade") and e.get("secs")]
print("40 days, %d trades, %d wins (%.0f%%), mean R %+.3f, sum %+.2f R | 40th day logged %s | median decision %s s"
      % (len(R), (R > 0).sum(), 100 * (R > 0).mean() if len(R) else 0, R.mean() if len(R) else float("nan"), R.sum(), t40, int(np.median(secs)) if secs else "n/a"))
go = len(R) >= 20 and R.mean() >= 0.20 and on_time
print("SCREEN:", "GO" if go else "NO-GO", "(bar: >= 20 trades, mean R >= +0.20, before 01:00)")
