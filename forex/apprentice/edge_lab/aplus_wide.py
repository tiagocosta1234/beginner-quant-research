"""PREREG_APLUS_WIDE.md: the A+ London 12 EMA signals with wider stops; gold descriptive, NQ + ES + SI pooled = the test.
Usage (from edge_lab): python aplus_wide.py"""
import numpy as np, pandas as pd
import ml_direction as M

SPEC = {"GC": (0.1, 0.32), "NQ": (0.25, 1.1), "ES": (0.25, 0.74), "SI": (0.005, 0.0112)}
VARS = ("ORIG", "W2", "W15", "WATR")


def run(src):
    tick, cost = SPEC[src]
    d = M.load_min(src)
    d["ema1"] = d.close.ewm(span=12, adjust=False).mean()
    m15 = d.close.resample("15min", label="left", closed="left").last().dropna(); e15 = m15.ewm(span=12, adjust=False).mean()
    h1 = d.close.resample("60min", label="left", closed="left").last().dropna(); e1h = h1.ewm(span=12, adjust=False).mean()
    day = d.groupby(d.index.normalize()).agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
    pc = day.c.shift(1)
    atr = pd.concat([day.h - day.l, (day.h - pc).abs(), (day.l - pc).abs()], axis=1).max(axis=1).ewm(alpha=1 / 14, adjust=False).mean().shift(1)
    O, H, L, C, E = (d[k].to_numpy() for k in ("open", "high", "low", "close", "ema1")); TS = d.index.to_numpy()
    out = []
    for dt in day.index:
        if dt.weekday() >= 5 or dt < pd.Timestamp("2019-11-01") or not (atr.get(dt, np.nan) > 0): continue
        k15 = dt + pd.Timedelta(hours=7, minutes=45)
        if k15 not in m15.index: continue
        i = m15.index.get_loc(k15)
        if i < 4: continue
        c, e, e4 = m15.iloc[i], e15.iloc[i], e15.iloc[i - 4]
        bias = 1 if (c > e and e > e4) else -1 if (c < e and e < e4) else 0
        if bias == 0: continue
        a = np.searchsorted(TS, np.datetime64(dt + pd.Timedelta(hours=7, minutes=59)))
        b = np.searchsorted(TS, np.datetime64(dt + pd.Timedelta(hours=8, minutes=15)))
        end = np.searchsorted(TS, np.datetime64(dt + pd.Timedelta(hours=16)))
        sig = None
        for j in range(max(a, 1), b):
            body = abs(C[j] - O[j]); wick = max(H[j] - max(O[j], C[j]), min(O[j], C[j]) - L[j])
            if bias * (C[j] - E[j]) > 0 and bias * (C[j - 1] - E[j - 1]) < 0 and body > wick:
                sig = j; break
        if sig is None or sig < 16: continue
        c1 = False
        for k in range(max(sig - 60, 2), sig):
            if bias > 0 and H[k - 2] < L[k] and L[sig] <= L[k] and H[sig] >= H[k - 2]: c1 = True; break
            if bias < 0 and L[k - 2] > H[k] and H[sig] >= H[k] and L[sig] <= L[k - 2]: c1 = True; break
        s0 = np.searchsorted(TS, np.datetime64(dt)); s7 = np.searchsorted(TS, np.datetime64(dt + pd.Timedelta(hours=7)))
        c2 = bool(s7 > s0 + 30 and ((L[s7:sig + 1].min() < L[s0:s7].min()) if bias > 0 else (H[s7:sig + 1].max() > H[s0:s7].max())))
        k1h = dt + pd.Timedelta(hours=7)
        c3 = bool(k1h in h1.index and bias * (h1.loc[k1h] - e1h.loc[k1h]) > 0)
        if int(c1) + int(c2) + int(c3) < 2: continue
        entry = C[sig]
        s5 = (entry - (L[sig - 5:sig + 1].min() - tick)) if bias > 0 else ((H[sig - 5:sig + 1].max() + tick) - entry)
        s15 = (entry - (L[sig - 15:sig + 1].min() - tick)) if bias > 0 else ((H[sig - 15:sig + 1].max() + tick) - entry)
        A = atr[dt]
        dist = {"ORIG": (s5, 0.0006, 0.0024), "W2": (2 * s5, 0.0012, 0.0048), "W15": (s15, 0.0012, 0.0048), "WATR": (max(s5, 0.5 * A), 0.0, A / entry)}
        rec = dict(date=dt, yr=dt.year, mkt=src)
        for v, (risk, lo, hi) in dist.items():
            if not (lo * entry <= risk <= hi * entry):
                rec[v] = np.nan; rec[v + "_m"] = np.nan; continue
            for sd, lab in ((bias, ""), (-bias, "_m")):
                sl, tp = entry - sd * risk, entry + sd * risk; px = None
                for j in range(sig + 1, min(end + 1, len(C))):
                    if j >= end: px = O[j]; break
                    if (L[j] <= sl) if sd > 0 else (H[j] >= sl): px = sl; break
                    if (H[j] >= tp) if sd > 0 else (L[j] <= tp): px = tp; break
                if px is None: px = C[min(end, len(C) - 1)]
                rec[v + lab] = sd * (px - entry) / risk - cost / risk
            rec[v + "_cost"] = cost / risk
        out.append(rec)
    return pd.DataFrame(out)


def show(label, R, primary):
    rng = np.random.default_rng(20261026)
    for v in VARS:
        s = R[R[v].notna()]
        if len(s) < 5: print("  %-26s %-4s too few" % (label, v)); continue
        a, m = s[v].to_numpy(), s[v + "_m"].to_numpy()
        p = float((np.where(rng.random((20000, len(a))) < 0.5, a, m).mean(axis=1) >= a.mean()).mean())
        yrs = s.groupby("yr")[v].mean(); pos = int((yrs.loc[[y for y in yrs.index if 2020 <= y <= 2026]] > 0).sum())
        ok = primary and v == "W2" and a.mean() > 0 and p <= 0.025 and len(a) >= 100 and pos >= 4
        print("  %-26s %-4s n %4d (%4.1f/yr)  win %3.0f%%  cost %.3fR  mean net R %+.3f  P %.4f  years>0 %d/7  2026 %+.3f  %s" % (
            label, v, len(a), len(a) / 6.9, 100 * (a > 0).mean(), s[v + "_cost"].mean(), a.mean(), p, pos, yrs.get(2026, np.nan),
            ("-> PASS" if ok else "-> NOT SHOWN") if (primary and v == "W2") else ""))
        if v == "W2": print("      by year: " + " ".join("%d %+.3f (%d)" % (y, val, (s.yr == y).sum()) for y, val in yrs.items()))


if __name__ == "__main__":
    parts = {m: run(m) for m in SPEC}
    print("A+ signal days per market: " + ", ".join("%s %d" % (m, len(p)) for m, p in parts.items()))
    print("\nGOLD (descriptive, signals already seen):"); show("GC", parts["GC"], False)
    print("\nREPLICATION (never tested for A+):")
    for m in ("NQ", "ES", "SI"): show(m, parts[m], False)
    show("NQ+ES+SI pooled (TEST)", pd.concat([parts[m] for m in ("NQ", "ES", "SI")], ignore_index=True), True)
