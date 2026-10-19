import pandas as pd, numpy as np, sys
sys.path.insert(0, ".")
exec(open("st.py").read().split("print(\"n\"")[0])   # reuse rows -> D, d, ses, win, E, S, T, risk, rew
raw = pd.read_parquet("D:/finance/beginner-quant-research/forex/data_mt5/XAUUSD_M1_rates.parquet")
raw = raw[(raw.t >= 1740787200) & (raw.t < 1759276800)].copy()          # 2025-03-01 .. 2025-09-30
raw["dt"] = pd.to_datetime(raw.t, unit="s")
raw["day"] = raw.dt.dt.date; raw["hm"] = raw.dt.dt.hour*60 + raw.dt.dt.minute
raw["mo"] = (raw.ao + raw.bo)/2; raw["mh"] = (raw.ah + raw.bh)/2; raw["ml"] = (raw.al + raw.bl)/2
days = {k: g.reset_index(drop=True) for k, g in raw.groupby("day")}
WIN = {"London": (10*60, 10*60+15), "NY": (16*60+30, 16*60+45)}     # server clock = chart clock + 2h
TOL = 1.5
def sim_mid(g, i0, side, entry, risk_, rew_):
    tp = entry + rew_ if side == "L" else entry - rew_
    sl = entry - risk_ if side == "L" else entry + risk_
    for j in range(i0, min(i0+400, len(g))):
        h, l = g.mh[j], g.ml[j]
        hit_tp = (h >= tp) if side == "L" else (l <= tp)
        hit_sl = (l <= sl) if side == "L" else (h >= sl)
        if hit_tp and hit_sl: return "A"
        if hit_tp: return "W"
        if hit_sl: return "L"
    return None
cands = []
for k in range(len(D)):
    side, sname, want = d[k], ses[k], ("W" if win[k] else "L")
    lo, hi = WIN[sname]; c = []
    for day, g in days.items():
        if day.weekday() >= 5: continue
        idx = g.index[(g.hm >= lo) & (g.hm <= hi)]
        for i in idx:
            if abs(g.mo[i] - E[k]) <= TOL:
                r = sim_mid(g, i, side, g.mo[i], risk[k], rew[k])
                if r == want or r == "A":
                    c.append((day, int(g.hm[i]), i, r))
    cands.append(c)
print("candidates per row:", [len(c) for c in cands])
# chronological DP: dates non-decreasing; same day -> London before NY
import functools
rowdays = [sorted({x[0] for x in c}) for c in cands]
print("distinct candidate days per row:", [len(x) for x in rowdays])
@functools.lru_cache(None)
def count(k, prev_day, prev_ses):
    if k == len(D): return 1
    tot = 0
    for day in rowdays[k]:
        if day < prev_day: continue
        if day == prev_day and not (prev_ses == "London" and ses[k] == "NY"): continue
        tot += count(k+1, day, ses[k])
    return tot
import datetime
print("number of chronologically consistent date assignments:", count(0, datetime.date(2025,1,1), "NY"))
# greedy earliest-feasible reconstruction + show ambiguity per row (days that appear in some consistent assignment)
def feasible_from(k, prev_day, prev_ses):
    return count(k, prev_day, prev_ses) > 0
chosen = []; prev_day, prev_ses = datetime.date(2025,1,1), "NY"
for k in range(len(D)):
    opts = [day for day in rowdays[k] if (day > prev_day or (day == prev_day and prev_ses == "London" and ses[k] == "NY")) and count(k+1, day, ses[k]) > 0]
    chosen.append(opts); 
    if opts: prev_day, prev_ses = opts[0], ses[k]
for k, o in enumerate(chosen): print(k+1, ses[k], d[k], "W" if win[k] else "L", [str(x) for x in o[:6]], "..." if len(o) > 6 else "")
