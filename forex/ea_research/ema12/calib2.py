import numpy as np, pandas as pd
from ema12_test import load
O = pd.read_csv("replay_mt5.csv"); g = load("XAUUSD", last_day="2025-12-31"); g["mo"] = (g.bo + g.ao) / 2
idx = {(d, h): i for i, (d, h) in enumerate(zip(g.day, g.hm))}
def test(name, cond, back_max):
    ok = near = 0
    for _, r in O.iterrows():
        ent = idx[(pd.Timestamp(r.day).date(), int(r.hm))]; side = 1 if r.side == "L" else -1
        hit = [b for b in range(1, back_max + 1) if cond(ent - b, side)]
        ok += bool(hit); near += (1 in hit)
    print("%-62s found within %2d bars: %2d/30 | on the bar just before entry: %2d/30" % (name, back_max, ok, near))
def body_wick(t):
    o, c, h, l = g.mo[t], g.mid[t], g.mh[t], g.ml[t]; b = abs(c - o); return b > max(h - max(o, c), min(o, c) - l), b
for kb in (5, 10):
    test("open/close vs EMA at bar t (as drawn)", lambda t, s: (g.mo[t] - g.ema[t]) * s < 0 < (g.mid[t] - g.ema[t]) * s, kb)
    test("open/close vs EMA of previous bar", lambda t, s: (g.mo[t] - g.ema[t-1]) * s < 0 < (g.mid[t] - g.ema[t-1]) * s, kb)
    test("close crosses the EMA vs previous close (first-cross style)", lambda t, s: (g.mid[t-1] - g.ema[t-1]) * s < 0 < (g.mid[t] - g.ema[t]) * s, kb)
    test("candle spans the EMA (low<EMA<high) and closes on trade side", lambda t, s: g.ml[t] < g.ema[t] < g.mh[t] and (g.mid[t] - g.ema[t]) * s > 0 and (g.mo[t] - g.ema[t]) * s < 0.5 * abs(g.mid[t]-g.mo[t]), kb)
    test("opens on the wrong side + body > bigger wick", lambda t, s: (g.mo[t] - g.ema[t]) * s < 0 < (g.mid[t] - g.ema[t]) * s and body_wick(t)[0], kb)
    test("... + body >= 0.5 ATR14", lambda t, s: (g.mo[t] - g.ema[t]) * s < 0 < (g.mid[t] - g.ema[t]) * s and body_wick(t)[0] and body_wick(t)[1] >= 0.5 * g.atr[t-1], kb)
# base rate: how often does a random window bar satisfy the 'open/close vs EMA' condition (any direction)?
cnt = tot = 0
for t in range(100000, 100000 + 200000):
    cnt += ((g.mo[t] - g.ema[t]) * (g.mid[t] - g.ema[t]) < 0); tot += 1
print("base rate: share of all 1-min bars whose open and close are on opposite sides of the EMA12: %.1f%%" % (100 * cnt / tot))
