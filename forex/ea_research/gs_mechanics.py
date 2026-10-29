"""Is GoldenShot's 95% win rate an EDGE or the geometry of its exits? (the trader 2026-10-09 23:5x: "(original wording omitted)".)
   python -m forex.ea_research.gs_mechanics
Diagnostic, not a registered trial: RANDOM entries (random time inside the EA's entry windows, Mon-Thu, random direction) on 180 days of MT5 broker real ticks (2025-10 .. 2026-09) with the EA's published exit geometry: stop 20 USD / target 4 USD (strategy 1) and 25 / 5 (strategy 2), a trailing stop that starts at a favourable move of `start` USD and then follows the best price at a distance `dist`, quantised to 0.3 USD steps. If random entries already win about 94% of the time with a positive expectancy, the EA's published numbers come from the exits and the execution model, not from its entry rule.
Random-walk arithmetic: P(+4 before -20) = 20 / 24 = 83% and P(+1.2 before -20) = 20 / 21.2 = 94%: a 95% win rate is what a stop 17x wider than the first target produces by itself.
Execution models: the tester modifies the trailing stop instantly (latency 0); a real broker needs 100-800 ms for each modification and for the entry. Stop and target fills use the first tick that crosses the level (as the MT5 tester and a real server do), so gaps cost money. Spread is paid through bid / ask: long = ask at entry, bid afterwards; short = bid at entry, ask afterwards."""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

TICKS = sorted(glob.glob(r"data\scratch\ticks_gold\*.parquet"))
RNG = np.random.default_rng(20261009)
K_MS = 30 * 60 * 1000


def day_ticks(f):
    d = pd.read_parquet(f); return d.ms.to_numpy("int64"), d.bid.to_numpy("float64"), d.ask.to_numpy("float64")


def one_trade(ms, bid, ask, i0, side, SL, TP, start, dist, step, lat_entry, lat_mod):
    t0 = ms[i0] + lat_entry; i = int(np.searchsorted(ms, t0)); j_end = int(np.searchsorted(ms, ms[i] + K_MS)) if i < len(ms) else len(ms)
    if i >= len(ms) - 5 or j_end - i < 50: return None
    if side > 0:
        entry = ask[i]; prof = bid[i + 1:j_end] - entry
    else:
        entry = bid[i]; prof = entry - ask[i + 1:j_end]
    t = ms[i + 1:j_end]; mfe = np.maximum.accumulate(prof)
    lvl = np.where(mfe >= start, np.floor((mfe - dist) / step) * step, -np.inf)                           # trailing level in profit terms, quantised
    lvl = np.maximum.accumulate(np.maximum(lvl, -SL)); lvl = np.where(lvl > -SL, lvl, -SL)
    k = np.searchsorted(t, t - lat_mod, side="left"); k = np.clip(k, 0, len(t) - 1)                       # the modification only becomes active lat_mod ms after it was decided
    eff = np.where(t - lat_mod >= t[0], lvl[k], -SL); eff = np.maximum(eff, -SL)
    hit_tp = np.nonzero(prof >= TP)[0]; hit_sl = np.nonzero(prof <= eff)[0]
    a = hit_tp[0] if len(hit_tp) else 10 ** 9; b = hit_sl[0] if len(hit_sl) else 10 ** 9
    if a == 10 ** 9 and b == 10 ** 9: return float(prof[-1]), "time"
    return (float(TP), "tp") if a <= b else (float(prof[b]), "stop")


def main():
    # entry sample: random ticks inside the allowed windows (server hours 06:00-21:00 for S1; 01:15-20:00 for S2), Monday-Thursday
    days = []
    for f in TICKS:
        ms, bid, ask = day_ticks(f); dow = pd.Timestamp(int(ms[0]) // 1000, unit="s").dayofweek
        if dow <= 3: days.append((ms, bid, ask))
    print(len(days), "Monday-Thursday days with ticks")
    n_per_day = 25; rows = []
    SCEN = [("S1 pullback  SL 20 TP 4 start 1.2", 20.0, 4.0, 1.2, (6, 21)), ("S2 momentum  SL 25 TP 5 start 2.1", 25.0, 5.0, 2.1, (1.25, 20))]
    for name, SL, TP, start, (h0, h1) in SCEN:
        for dist in (0.3, 0.6, 1.2):
            for lat in (0, 300, 800):
                pn = []; why = {"tp": 0, "stop": 0, "time": 0}
                rng = np.random.default_rng(1)
                for ms, bid, ask in days:
                    sec = (ms // 1000) % 86400; ok = np.nonzero((sec >= h0 * 3600) & (sec <= h1 * 3600 - 1800))[0]
                    if len(ok) < 100: continue
                    for i0 in rng.choice(ok, n_per_day, replace=False):
                        side = 1 if rng.random() < 0.5 else -1; r = one_trade(ms, bid, ask, int(i0), side, SL, TP, start, dist, 0.3, lat, lat)
                        if r is None: continue
                        pn.append(r[0]); why[r[1]] += 1
                x = np.array(pn); w, l = x[x > 0].sum(), -x[x <= 0].sum()
                print(f"{name} | trail dist {dist:.1f} | latency {lat:4d} ms | n {len(x):5d} | win {100*(x>0).mean():5.1f}% | avg win {x[x>0].mean():+.2f} avg loss {x[x<=0].mean():+.2f} | mean {x.mean():+.3f} USD/oz | PF {w/l if l > 0 else float('inf'):.2f} | exits {why}", flush=True)


if __name__ == "__main__":
    main()
