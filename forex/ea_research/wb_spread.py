"""WB: WTI / Brent spread reversion (PREREG_OUTSIDE_BOX.md).   python -m forex.ea_research.wb_spread"""
import numpy as np, pandas as pd
from forex.ea_research import more_eas as ME

def px(m): d = ME.load(m); b, a = ME.at(d, "hm", 1559, "bo", "date"), ME.at(d, "hm", 1559, "ao", "date"); i = b.index.intersection(a.index).sort_values(); return b[i], a[i]
bB, aB = px("BRENT"); bW, aW = px("WTI"); T = ME.pair_trades(bB, aB, bW, aW)
print("pair trades", len(T), "| ln(BRENT/WTI) mean", round(float(np.log(bB / bW).mean()), 4), "sd", round(float(np.log(bB / bW).std()), 4))
def stat(s, w):
    d = ME.win(s, w); n = len(d)
    return dict(n=n, mean=d.mean() if n else np.nan, t=d.mean() / (d.std(ddof=1) / np.sqrt(n)) if n > 2 else np.nan, win=100 * (d > 0).mean() if n else np.nan)
for lab, w in (("DEV 2022-24", ME.DEV), ("VAL 2025", ME.VAL), ("HOLD 2026 (one look)", ME.HOLD)):
    s = stat(T, w); print(f"{lab}: trades {s['n']} | mean {s['mean']:+.1f} bp | win {s['win']:.0f}% | t {s['t']:.2f}")
d, v = stat(T, ME.DEV), stat(T, ME.VAL); print("accepted (DEV >= 15 trades, >= +25 bp, t >= 1.65, VAL > 0):", bool(d["n"] >= 15 and d["mean"] >= 25 and d["t"] >= 1.65 and v["mean"] > 0))
