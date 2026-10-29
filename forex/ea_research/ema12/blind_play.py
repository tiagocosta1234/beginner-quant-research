"""Play a logged blind-replay trade forward on MT5 XAUUSD bid/ask (batch scoring convention: fill at the next minute's open on the ask (long) /
bid (short), the logged stop and target DISTANCES applied to the fill, exits on the bid (long) / ask (short), stop first if both in one minute,
still open at 17:00 local = closed there). Also the S1 1:1 variant (own stop, 1.0 R target).
Usage (from ema12): python blind_play.py 2026-08-12 08:00 L 4405.84 4403 4416.1"""
import sys
import pandas as pd

day, hhmm, side, E, S, T = sys.argv[1], sys.argv[2], sys.argv[3], *map(float, sys.argv[4:7])
r = pd.read_parquet("forex/data_mt5/XAUUSD_M1_rates.parquet")
t = pd.to_datetime(r.t, unit="s"); m = (t >= day) & (t < pd.Timestamp(day) + pd.Timedelta(days=1, hours=6)); r, t = r[m], t[m]
r = r.set_axis(t.dt.tz_localize("Europe/Athens").dt.tz_convert("Europe/London").dt.tz_localize(None).to_numpy()).sort_index()
start = pd.Timestamp("%s %s" % (day, hhmm)) + pd.Timedelta(minutes=1)
d = r[(r.index >= start) & (r.index <= pd.Timestamp(day + " 17:00"))]
sd = 1 if side == "L" else -1
fill = d.ao.iloc[0] if sd > 0 else d.bo.iloc[0]; risk = abs(E - S)
for name, sdist, tdist in (("as logged", abs(E - S), abs(T - E)), ("S1 1:1", abs(E - S), abs(E - S))):
    sl, tp = fill - sd * sdist, fill + sd * tdist; out = None
    for ts, b in d.iterrows():
        lo, hi = (b.bl, b.bh) if sd > 0 else (b.al, b.ah)
        if (lo <= sl) if sd > 0 else (hi >= sl): out = (ts, sl, "STOP"); break
        if (hi >= tp) if sd > 0 else (lo <= tp): out = (ts, tp, "TARGET"); break
    if out is None: out = (d.index[-1], d.bc.iloc[-1] if sd > 0 else d.ac.iloc[-1], "17:00 close")
    print("%-10s fill %.2f (%s %s open)  stop %.2f  target %.2f  -> %s at %s, exit %.2f, R %+.2f" % (
        name, fill, "ask" if sd > 0 else "bid", start.strftime("%H:%M"), sl, tp, out[2], out[0].strftime("%H:%M"), out[1], sd * (out[1] - fill) / sdist))
print("after entry to 17:00: bid low %.2f at %s, high %.2f at %s" % (d.bl.min(), d.bl.idxmin().strftime("%H:%M"), d.bh.max(), d.bh.idxmax().strftime("%H:%M")))
