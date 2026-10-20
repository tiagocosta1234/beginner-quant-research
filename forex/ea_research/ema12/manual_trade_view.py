"""DESCRIPTIVE ONLY: one of the trader's 50 FX Replay trades on the MT5 1-minute mid candles, for the 'why did you take it' conversation (MANUAL_WHY_ENTRIES.md).
python manual_trade_view.py "2025-05-05 08:08" Buy 3260.66 3257.291 3262.4       (signal-candle minute in local time, side, entry, stop, target as in FX Replay)
Prints: the candles around the signal with EMA12 and tags (cross / touch / 1-minute gaps), the signal-candle shape, BOS, displacement, sweep, 5-minute gaps near the target, equal-high / low zones at the target and stop, lot numbers at USD 2,000, and what happened next. Nothing is a test."""
import sys, numpy as np, pandas as pd
sigt = pd.Timestamp(sys.argv[1]); side = sys.argv[2]; s = 1 if side == "Buy" else -1; ent, stp, tgt = (float(x) for x in sys.argv[3:6])
d = pd.read_parquet("D:/finance/beginner-quant-research/forex/data_mt5/XAUUSD_M1_rates.parquet").sort_values("t").reset_index(drop=True)
M = pd.DataFrame(dict(lis=pd.to_datetime(d.t, unit="s") - pd.Timedelta(hours=2), o=(d.bo+d.ao)/2, h=(d.bh+d.ah)/2, l=(d.bl+d.al)/2, c=(d.bc+d.ac)/2)).reset_index(drop=True)
M["ema"] = M.c.ewm(span=12, adjust=False).mean(); M["atr"] = (M.h-M.l).rolling(14).mean().shift(1); i0 = int(M.index[M.lis == sigt][0]); o, h, l, c, e, atr = (M[k].to_numpy() for k in ("o", "h", "l", "c", "ema", "atr"))
off = ent - c[i0]; E, S, T = ent - off, stp - off, tgt - off; sd = abs(E - S); td = abs(T - E)
print("%s %s: FX Replay price - MT5 broker mid at the signal close %+.2f | MT5-equivalent entry %.2f stop %.2f (%.2f away) target %.2f (%.2f away = %.2f R) | USD 2,000 needs %.1f lots (cap 3.1)" % (sigt, side, off, E, S, sd, T, td, td/sd, 2000/(sd*100)))
print("local  open     high     low      close    EMA12    o-EMA  c-EMA  body  wickUp wickLo  b/ATR  note")
for k in range(i0-22, i0+9):
    body = abs(c[k]-o[k]); up = h[k]-max(o[k], c[k]); lo = min(o[k], c[k])-l[k]; cross = (o[k]-e[k])*(c[k]-e[k]) < 0; touch = l[k] <= e[k] <= h[k]
    note = ("SIGNAL " if k == i0 else "") + ("cross " if cross else ("touch " if touch else "")) + ("bullGap " if l[k] > h[k-2] else "") + ("bearGap " if h[k] < l[k-2] else "")
    print("%s  %.3f %.3f %.3f %.3f  %.3f  %+.2f  %+.2f  %.2f  %.2f  %.2f   %.2f   %s" % (M.lis[k].strftime("%H:%M"), o[k], h[k], l[k], c[k], e[k], o[k]-e[k], c[k]-e[k], body, up, lo, body/atr[k] if atr[k] else np.nan, note))
body = abs(c[i0]-o[i0]); up = h[i0]-max(o[i0], c[i0]); lo = min(o[i0], c[i0])-l[i0]; cw = up if s > 0 else lo
bos = (c[i0] > h[i0-5:i0].max()) if s > 0 else (c[i0] < l[i0-5:i0].min()); sw = (l[i0-5:i0+1].min() < l[i0-65:i0-5].min()) if s > 0 else (h[i0-5:i0+1].max() > h[i0-65:i0-5].max())
print("\nsignal candle: body %.2f, wicks %.2f (up %.2f low %.2f), close-side wick %.0f%% of the body, body %s the wicks, %.2f ATR, closes %.2f %s the EMA, BOS over the previous 5 candles: %s, sweep of the previous 60-candle extreme in the last 6 candles: %s, 30-candle move %+.2f (%s the trade)" % (body, up+lo, up, lo, 100*cw/body if body else np.nan, ">" if body > up+lo else "<=", body/atr[i0], abs(c[i0]-e[i0]), "above" if c[i0] > e[i0] else "below", bool(bos), bool(sw), c[i0]-c[i0-30], "with" if np.sign(c[i0]-c[i0-30]) == s else "against"))
X = M.set_index("lis")[["o", "h", "l", "c"]][M.set_index("lis").index < sigt].resample("5min", label="left", closed="left").agg(dict(o="first", h="max", l="min", c="last")).dropna(); X = X[X.index + pd.Timedelta(minutes=5) <= sigt]
print("\nunfilled 5-minute gaps (previous 24 h) near the target side:")
for i in range(2, len(X)):
    a, c3 = X.iloc[i-2], X.iloc[i]; t = X.index[i] + pd.Timedelta(minutes=5)
    if t < sigt - pd.Timedelta(hours=24): continue
    later = X.iloc[i+1:]
    for kind, lo_, hi_ in (("bull", a.h, c3.l) if c3.l > a.h else (None, 0, 0), ("bear", c3.h, a.l) if c3.h < a.l else (None, 0, 0)):
        if kind is None: continue
        filled = ((later.l <= lo_).any() if kind == "bull" else (later.h >= hi_).any()) if len(later) else False
        mid = (lo_+hi_)/2
        if not filled and ((s > 0 and mid > E and mid < E + 25) or (s < 0 and mid < E and mid > E - 25)): print("   %s gap %.2f-%.2f (completed %s): near edge %.2f is %.2f R from the entry, far edge %.2f is %.2f R" % (kind, lo_, hi_, t.strftime("%d %H:%M"), (lo_ if s > 0 else hi_), abs((lo_ if s > 0 else hi_) - E)/sd, (hi_ if s > 0 else lo_), abs((hi_ if s > 0 else lo_) - E)/sd))
pp = M[(M.lis >= sigt - pd.Timedelta(hours=14)) & (M.lis <= sigt)]
tz = pp[(pp.h - T).abs() <= 0.5] if s > 0 else pp[(pp.l - T).abs() <= 0.5]; sz = pp[(pp.l - S).abs() <= 0.6] if s > 0 else pp[(pp.h - S).abs() <= 0.6]
print("\ntarget zone: %d candles with a %s within 0.5 of %.2f in the previous 14 h (first %s, last %s)" % (len(tz), "high" if s > 0 else "low", T, tz.lis.iloc[0].strftime("%d %H:%M") if len(tz) else "-", tz.lis.iloc[-1].strftime("%d %H:%M") if len(tz) else "-"))
print("stop zone: %d candles with a %s within 0.6 of %.2f (first %s, last %s)" % (len(sz), "low" if s > 0 else "high", S, sz.lis.iloc[0].strftime("%d %H:%M") if len(sz) else "-", sz.lis.iloc[-1].strftime("%d %H:%M") if len(sz) else "-"))
w = M[(M.lis >= sigt.floor("D") + pd.Timedelta(hours=2)) & (M.lis < sigt.floor("D") + pd.Timedelta(hours=7))]; pdd = M[(M.lis >= sigt.floor("D") - pd.Timedelta(days=1)) & (M.lis < sigt.floor("D"))]
print("Asia 02:00-07:00 high %.2f low %.2f | previous day high %.2f low %.2f | entry %.2f" % (w.h.max(), w.l.min(), pdd.h.max(), pdd.l.min(), E))
after = M[(M.lis > sigt) & (M.lis <= sigt + pd.Timedelta(minutes=40))]
for lab, lvl in (("target", T), ("1 R", E + s*sd), ("2 R", E + s*2*sd), ("stop", S)):
    hit = after[after.h >= lvl] if (s > 0 and lab != "stop") or (s < 0 and lab == "stop") else after[after.l <= lvl]; print("  %-6s %.2f first traded at %s" % (lab, lvl, hit.lis.iloc[0].strftime("%H:%M") if len(hit) else "not within 40 minutes"))
print("  max favourable excursion in 40 min: %.2f (%.1f R) | max adverse: %.2f (%.1f R)" % ((after.h.max() - E) if s > 0 else (E - after.l.min()), ((after.h.max() - E) if s > 0 else (E - after.l.min()))/sd, (E - after.l.min()) if s > 0 else (after.h.max() - E), ((E - after.l.min()) if s > 0 else (after.h.max() - E))/sd))
