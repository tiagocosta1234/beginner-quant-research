"""Always-exposed variant of the x1.5 episode game (+2,000 / -1,500, multi-day, MT5 broker daily loss enforced). On every business day at 08:00 server time, if the pair has no position open, a filler gold position (q=6, like one XAU5 leg)
is opened in the direction of the previous 20 business days (trend; 'anti' = the opposite as a placebo) and held 24 h. Pre-fixed, nothing tuned. python -m forex.ea_research.episode_always_on"""
import sys
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, clean_boot_lib as L, episode_mt5 as E
from forex.ea_research.combo_grid import news_flat, bars, CH

UP, DN, M, Q, HOUR = 2000.0, 1500.0, 1.5, 6.0, 8


def fillers(tr, lo, hi, sign):
    tm, bc, sp = bars; ins, outs = tr["in_s"], tr["out_s"]; rows = []
    for d in range(lo, hi + 1):
        if pd.Timestamp(d * 86400, unit="s").dayofweek >= 5: continue
        t0 = d * 86400 + HOUR * 3600; i = int(np.searchsorted(tm, t0)); j = int(np.searchsorted(tm, t0 + 86400)); k = int(np.searchsorted(tm, t0 - 28 * 86400))
        if i >= len(tm) or j >= len(tm) or tm[i] - t0 > 1800 or i - k < 100 or j - i < 100: continue
        if np.any((ins <= t0) & (outs > t0)): continue
        s = sign * (1 if bc[i] > bc[k] else -1); ent = bc[i] + sp[i] if s > 0 else bc[i]; ex = bc[j] if s > 0 else bc[j] + sp[j]
        rows.append((tm[i], tm[j], s, ent, Q, s * (ex - ent) * Q))
    return rows


def main():
    for pool in ("MT5", "FT"):
        src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b)
        base = news_flat(L.merge(L.ea_trades(src, "sdb", CH["sdb"] * M, lo), L.ea_trades(src, "xau5", CH["xau5"] * M, lo)), G.EV, bars)
        for name, sign in (("pair only", 0), ("always-on trend", 1), ("always-on anti-trend", -1)):
            tr = {k: (v.copy() if hasattr(v, "copy") else v) for k, v in base.items()}; n = 0
            if sign:
                r = fillers(tr, lo, hi, sign); n = len(r)
                for key, col in (("in_s", 0), ("out_s", 1), ("side", 2), ("entry", 3), ("q", 4), ("pl", 5)): tr[key] = np.r_[tr[key], np.array([x[col] for x in r], dtype=float)]
            e = E.replay(pool, M, UP, DN, tr); o = E.account(e, UP, DN); ps = o[o.r == "pass"]
            print(f"{pool} {name:22s} fillers {n:4d} | episodes {len(e)} hit {100 * (e.res == 1).mean():.0f}% median {(e.end - e.start).median() / 3600:.0f} h daily-breach episodes {int(e.breach.sum())} worst day {e.worst_day.min():+.0f} | starts {len(o)} pass {100 * (o.r == 'pass').mean():.0f}% breach {100 * (o.r == 'breach').mean():.0f}% median bd {0.71 * ps.d.median() if len(ps) else float('nan'):.0f} | net {e.pnl.sum():+,.0f}", flush=True)


if __name__ == "__main__":
    main()
