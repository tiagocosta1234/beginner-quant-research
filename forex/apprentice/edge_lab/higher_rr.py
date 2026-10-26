"""PREREG_HIGHER_RR.md: the indicator and the A+ London 12 EMA at 1 / 1.5 / 2 / 3 R and hold-to-16:00.
Usage (from edge_lab): python higher_rr.py"""
import numpy as np, pandas as pd
import ml_direction as M

TG = (("T1", 1.0), ("T1.5", 1.5), ("T2", 2.0), ("T3", 3.0), ("EOD", None))
TICK = {"GC": 0.1, "NQ": 0.25, "ES": 0.25, "SI": 0.005}
COST = {"GC": 0.32, "NQ": 1.1, "ES": 0.74, "SI": 0.0112, "DOW": 4.4}


def sim(H, L, O, C, i0, end, entry, side, risk, cost):
    """Exits for every target from bar i0 to the 16:00 bar `end`; returns {target: net R}."""
    out = {}
    sl = entry - side * risk
    hs = L[i0:end] <= sl if side > 0 else H[i0:end] >= sl
    i_s = np.argmax(hs) if hs.any() else 10 ** 9
    ex_eod = O[end] if end < len(O) else C[-1]
    for name, k in TG:
        if k is None:
            px = sl if i_s < 10 ** 9 else ex_eod
        else:
            tp = entry + side * k * risk
            ht = H[i0:end] >= tp if side > 0 else L[i0:end] <= tp
            i_t = np.argmax(ht) if ht.any() else 10 ** 9
            px = sl if (i_s <= i_t and i_s < 10 ** 9) else tp if i_t < 10 ** 9 else ex_eod
        out[name] = side * (px - entry) / risk - cost / risk
    return out


def prep(src):
    d = M.load_min(src)
    day = d.groupby(d.index.normalize()).agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
    pc = day.c.shift(1)
    atr = pd.concat([day.h - day.l, (day.h - pc).abs(), (day.l - pc).abs()], axis=1).max(axis=1).ewm(alpha=1 / 14, adjust=False).mean().shift(1)
    return d, day, atr


def ind(src, lab):
    d, day, atr = prep(src)
    O, H, L, C = (d[k].to_numpy() for k in ("open", "high", "low", "close")); TS = d.index.to_numpy()
    rows = []
    for dt in day.index:
        if dt.weekday() >= 5 or not (atr.get(dt, np.nan) > 0): continue
        a = np.searchsorted(TS, np.datetime64(dt + pd.Timedelta(hours=8)))
        b = np.searchsorted(TS, np.datetime64(dt + pd.Timedelta(hours=8, minutes=15)))
        end = np.searchsorted(TS, np.datetime64(dt + pd.Timedelta(hours=16)))
        if b - a < 10 or end - b < 60 or end >= len(TS) or pd.Timestamp(TS[end]).normalize() != dt: continue
        co, cc, ch, cl = O[a], C[b - 1], H[a:b].max(), L[a:b].min()
        if cc == co: continue
        side = 1 if cc > co else -1; rng = ch - cl
        risk = max((cc - cl if side > 0 else ch - cc) + 0.5 * rng, 0.03 * atr[dt])
        r = dict(date=dt, yr=dt.year, mkt=lab, risk=risk)
        for sd, suf in ((side, ""), (-side, "_m")):
            for k, v in sim(H, L, O, C, b, end, cc, sd, risk, COST[src]).items(): r[k + suf] = v
        rows.append(r)
    return pd.DataFrame(rows)


def aplus(src):
    d, day, atr = prep(src)
    d["ema1"] = d.close.ewm(span=12, adjust=False).mean()
    m15 = d.close.resample("15min", label="left", closed="left").last().dropna(); e15 = m15.ewm(span=12, adjust=False).mean()
    h1 = d.close.resample("60min", label="left", closed="left").last().dropna(); e1h = h1.ewm(span=12, adjust=False).mean()
    O, H, L, C, E = (d[k].to_numpy() for k in ("open", "high", "low", "close", "ema1")); TS = d.index.to_numpy()
    rows = []
    for dt in day.index:
        if dt.weekday() >= 5 or dt < pd.Timestamp("2019-11-01"): continue
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
        if end >= len(TS): continue
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
        risk = (entry - (L[sig - 5:sig + 1].min() - TICK[src])) if bias > 0 else ((H[sig - 5:sig + 1].max() + TICK[src]) - entry)
        if not (0.0006 * entry <= risk <= 0.0024 * entry): continue
        r = dict(date=dt, yr=dt.year, mkt=src, risk=risk)
        for sd, suf in ((bias, ""), (-bias, "_m")):
            for k, v in sim(H, L, O, C, sig + 1, end, entry, sd, risk, COST[src]).items(): r[k + suf] = v
        rows.append(r)
    return pd.DataFrame(rows)


def show(label, R, primary, alpha=0.0125, minpos=5):
    rng = np.random.default_rng(20261026)
    yrs_span = max((R.date.max() - R.date.min()).days / 365.25, 0.5)
    for t, _ in TG:
        a, m = R[t].to_numpy(), R[t + "_m"].to_numpy()
        p = float((np.where(rng.random((20000, len(a))) < 0.5, a, m).mean(axis=1) >= a.mean()).mean())
        yrs = R.groupby("yr")[t].mean(); pos = int((yrs.loc[[y for y in yrs.index if 2020 <= y <= 2026]] > 0).sum())
        w = a[a > 0]; l = a[a <= 0]
        ok = primary and t == "T2" and a.mean() > 0 and p <= alpha and pos >= minpos and len(a) >= 100
        print("  %-24s %-4s n %4d (%5.1f/yr)  win %3.0f%%  avg win %+.2f  avg loss %+.2f  mean net R %+.3f  P %.4f  years>0 %d  2026 %+.3f  %s" % (
            label, t, len(a), len(a) / yrs_span, 100 * len(w) / len(a), w.mean() if len(w) else 0, l.mean() if len(l) else 0, a.mean(), p, pos,
            yrs.get(2026, np.nan), ("-> PASS" if ok else "-> NOT SHOWN") if (primary and t == "T2") else ""))
        if primary and t == "T2": print("      by year: " + " ".join("%d %+.3f (%d)" % (y, v, (R.yr == y).sum()) for y, v in yrs.items()))


if __name__ == "__main__":
    I = {lab: ind(src, lab) for lab, src in (("MGC", "GC"), ("MNQ", "NQ"), ("MES", "ES"), ("MYM", "DOW"))}
    print("INDICATOR (candle colour), stop = far end + 0.5 x range")
    for k, v in I.items(): show(k, v, False)
    show("IND pooled (PRIMARY)", pd.concat(I.values(), ignore_index=True), True)
    A = {m: aplus(m) for m in ("NQ", "ES", "SI")}
    print("\nA+ LONDON 12 EMA, ORIG stop (gold excluded)")
    for k, v in A.items(): show(k, v, False)
    show("APLUS NQ+ES+SI (PRIMARY)", pd.concat(A.values(), ignore_index=True), True)
