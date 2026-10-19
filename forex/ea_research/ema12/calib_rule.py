"""Calibrate the trader's described rule on his 30 dated gold trades (MT5 M1 mid candles): signal candle (opens one side of the EMA12, closes on the other, body > larger wick) and the FVG that sets the target."""
import numpy as np, pandas as pd
from ema12_test import load
O = pd.read_csv("replay_mt5.csv"); g = load("XAUUSD", last_day="2025-12-31")
g["mo"] = (g.bo + g.ao) / 2
idx = {(d, h): i for i, (d, h) in enumerate(zip(g.day, g.hm))}
def candle(i):
    o, h, l, c = g.mo[i], g.mh[i], g.ml[i], g.mid[i]; body = abs(c - o); up = h - max(o, c); lo = min(o, c) - l
    return o, h, l, c, body, up, lo
def fvgs(i_end, n=90):
    """unfilled 3-candle gaps formed in the n bars before bar i_end (mid candles). returns (kind, bottom, top, formed_bar)."""
    out = []
    for c3 in range(i_end - n, i_end):
        a, c = c3 - 2, c3
        if g.mh[a] < g.ml[c]: out.append(["bull", g.mh[a], g.ml[c], c])        # gap between high of a and low of c
        if g.ml[a] > g.mh[c]: out.append(["bear", g.mh[c], g.ml[a], c])
    keep = []
    for k, b, t, c in out:
        later = slice(c + 1, i_end)                                              # bars after the gap, up to the signal
        if k == "bull" and (g.ml[later].min() if later.stop > later.start else 1e9) <= b: continue   # fully traded through
        if k == "bear" and (g.mh[later].max() if later.stop > later.start else -1e9) >= t: continue
        keep.append((k, b, t, c))
    return keep
rows = []
for _, r in O.iterrows():
    d = pd.Timestamp(r.day).date(); ent = idx[(d, int(r.hm))]; side = 1 if r.side == "L" else -1
    # signal candle = latest bar before the entry bar that crosses the EMA in the trade direction
    best = None
    for back in range(1, 6):
        t = ent - back; o, h, l, c, body, up, lo = candle(t); e = g.ema[t]
        if side > 0 and o < e < c or side < 0 and o > e > c: best = (back, t); break
    if best is None: rows.append(dict(k=r.k, ses=r.ses, side=side, found=False)); continue
    back, t = best; o, h, l, c, body, up, lo = candle(t); e = g.ema[t]
    entry = g.ao[ent] if side > 0 else g.bo[ent]; reward = r.rew
    tgt = entry + side * reward
    gaps = [(k, b, tp, cc) for (k, b, tp, cc) in fvgs(t + 1) if (k == ("bear" if side > 0 else "bull"))]   # gap on the target side
    best_edge = None
    for k, b, tp, cc in gaps:
        near, far = (b, tp) if side > 0 else (tp, b)             # long: gap above -> near edge = bottom ; short: gap below -> near = top
        if (near - entry) * side <= 0: continue
        for nm, lvl in (("near", near), ("mid", (near + far) / 2), ("far", far)):
            dist = abs(abs(lvl - entry) - reward)
            if best_edge is None or dist < best_edge[0]: best_edge = (dist, nm, abs(far - near), abs(near - entry), abs(far - entry))
    rows.append(dict(k=r.k, ses=r.ses, side=side, found=True, back=back, body=body, wick_big=max(up, lo), body_gt_wick=body > max(up, lo), body_atr=body / g.atr[t], ema_pos=(c - e) * side / max(body, 1e-9),
                     reward=reward, fvg_match_d=None if best_edge is None else best_edge[0], fvg_edge=None if best_edge is None else best_edge[1], fvg_size=None if best_edge is None else best_edge[2], n_gaps=len(gaps)))
F = pd.DataFrame(rows); pd.set_option("display.width", 220); print(F.round(2).to_string(index=False))
f = F[F.found == True]
print("\nsignal candle (crosses the EMA in his direction within 5 bars before entry) found: %d of 30; on the immediately preceding bar: %d" % (len(f), int((f.back == 1).sum())))
print("body > bigger wick: %d of %d | body/ATR14: min %.2f, 25%% %.2f, median %.2f | closes beyond EMA: share of body past the EMA median %.2f (min %.2f)" % (f.body_gt_wick.sum(), len(f), f.body_atr.min(), f.body_atr.quantile(.25), f.body_atr.median(), f.ema_pos.median(), f.ema_pos.min()))
m = f.dropna(subset=["fvg_match_d"]); print("target matches an unfilled FVG edge on the target side within 0.30 USD: %d of %d (within 0.50: %d); edge used: %s" % ((m.fvg_match_d <= 0.3).sum(), len(f), (m.fvg_match_d <= 0.5).sum(), m[m.fvg_match_d <= 0.3].fvg_edge.value_counts().to_dict()))
print("FVG size when matched (USD): median %.2f, max %.2f" % (m[m.fvg_match_d <= 0.3].fvg_size.median(), m[m.fvg_match_d <= 0.3].fvg_size.max()))
