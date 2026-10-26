"""26 Oct 2026, the trader: "we're missing something, think". Audit of the backtest engine's pessimism: with 1-minute bars, a bar that touches both the
stop and the target was always scored as a LOSS (stop first). How many trades end on such a tie bar, and what do the setups earn with a
neutral tie (half a win, half a loss: gross 0) or an optimistic tie (target first)? Also the cost sensitivity. DESCRIPTIVE audit, no new rule.
Usage (from edge_lab): python tie_check.py"""
import numpy as np, pandas as pd
import ml_direction as M
from published_effects import load_ny

COSTS = {"GC": 0.32, "NQ": 1.1, "ES": 0.74, "DOW": 4.4}


def run(d, h0, m0, fh, fm, mode, tick=None, src=None):
    """mode IND = first-15m candle rule; APLUS = A+ 12 EMA (fixed 1.5-6 pt band, gold only). Returns rows of (risk, gross_pess, gross_neutral, gross_opt, tie)."""
    day = d.groupby(d.index.normalize()).agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
    pc = day.c.shift(1)
    atr = pd.concat([day.h - day.l, (day.h - pc).abs(), (day.l - pc).abs()], axis=1).max(axis=1).ewm(alpha=1 / 14, adjust=False).mean().shift(1)
    O, H, L, C = (d[k].to_numpy() for k in ("open", "high", "low", "close")); TS = d.index.to_numpy()
    if mode == "APLUS":
        E = d.close.ewm(span=12, adjust=False).mean().to_numpy()
        m15 = d.close.resample("15min", label="left", closed="left").last().dropna(); e15 = m15.ewm(span=12, adjust=False).mean()
        h1 = d.close.resample("60min", label="left", closed="left").last().dropna(); e1h = h1.ewm(span=12, adjust=False).mean()
    rows = []
    for dt in day.index:
        if dt.weekday() >= 5 or dt < pd.Timestamp("2020-01-01") or not (atr.get(dt, np.nan) > 0): continue
        end = np.searchsorted(TS, np.datetime64(dt + pd.Timedelta(hours=fh, minutes=fm)))
        if end >= len(TS) or pd.Timestamp(TS[end]).normalize() != dt: continue
        if mode == "IND":
            t0 = dt + pd.Timedelta(hours=h0, minutes=m0)
            a = np.searchsorted(TS, np.datetime64(t0)); b = np.searchsorted(TS, np.datetime64(t0 + pd.Timedelta(minutes=15)))
            if b - a < 10 or end - b < 30: continue
            co, cc, ch, cl = O[a], C[b - 1], H[a:b].max(), L[a:b].min()
            if cc == co: continue
            sd = 1 if cc > co else -1; rng = ch - cl
            risk = max((cc - cl if sd > 0 else ch - cc) + 0.5 * rng, 0.03 * atr[dt]); entry, i0 = cc, b
        else:
            k15 = dt + pd.Timedelta(hours=7, minutes=45)
            if k15 not in m15.index: continue
            i = m15.index.get_loc(k15)
            if i < 4: continue
            c, e, e4 = m15.iloc[i], e15.iloc[i], e15.iloc[i - 4]
            sd = 1 if (c > e and e > e4) else -1 if (c < e and e < e4) else 0
            if sd == 0: continue
            a = np.searchsorted(TS, np.datetime64(dt + pd.Timedelta(hours=7, minutes=59))); b = np.searchsorted(TS, np.datetime64(dt + pd.Timedelta(hours=8, minutes=15)))
            sig = None
            for j in range(max(a, 1), b):
                body = abs(C[j] - O[j]); wick = max(H[j] - max(O[j], C[j]), min(O[j], C[j]) - L[j])
                if sd * (C[j] - E[j]) > 0 and sd * (C[j - 1] - E[j - 1]) < 0 and body > wick: sig = j; break
            if sig is None or sig < 6: continue
            entry = C[sig]; stop = (L[sig - 5:sig + 1].min() - tick) if sd > 0 else (H[sig - 5:sig + 1].max() + tick); risk = abs(entry - stop)
            if not (1.5 <= risk <= 6.0): continue
            c1 = False
            for k in range(max(sig - 60, 2), sig):
                if sd > 0 and H[k - 2] < L[k] and L[sig] <= L[k] and H[sig] >= H[k - 2]: c1 = True; break
                if sd < 0 and L[k - 2] > H[k] and H[sig] >= H[k] and L[sig] <= L[k - 2]: c1 = True; break
            s0 = np.searchsorted(TS, np.datetime64(dt)); s7 = np.searchsorted(TS, np.datetime64(dt + pd.Timedelta(hours=7)))
            c2 = bool(s7 > s0 + 30 and ((L[s7:sig + 1].min() < L[s0:s7].min()) if sd > 0 else (H[s7:sig + 1].max() > H[s0:s7].max())))
            k1h = dt + pd.Timedelta(hours=7); c3 = bool(k1h in h1.index and sd * (h1.loc[k1h] - e1h.loc[k1h]) > 0)
            if int(c1) + int(c2) + int(c3) < 2: continue
            i0 = sig + 1
        sl, tp = entry - sd * risk, entry + sd * risk
        hs = (L[i0:end] <= sl) if sd > 0 else (H[i0:end] >= sl); ht = (H[i0:end] >= tp) if sd > 0 else (L[i0:end] <= tp)
        i_s = np.argmax(hs) if hs.any() else 10 ** 9; i_t = np.argmax(ht) if ht.any() else 10 ** 9
        eod = sd * (O[end] - entry) / risk
        if i_s < i_t: g = (-1.0, -1.0, -1.0); tie = False
        elif i_t < i_s: g = (1.0, 1.0, 1.0); tie = False
        elif i_s < 10 ** 9: g = (-1.0, 0.0, 1.0); tie = True
        else: g = (eod, eod, eod); tie = False
        rows.append((risk, *g, tie))
    return np.array(rows, float)


if __name__ == "__main__":
    print("How often does one 1-minute bar touch BOTH stop and target? Net R a trade with the tie scored as loss / neutral / win (2020-2026)")
    print("cost scale: 1.0 = the costs used all day; 0.5 = half (e.g. cheaper commissions + limit entries)")
    sets = [("London IND MGC", lambda: run(M.load_min("GC"), 8, 0, 16, 0, "IND"), "GC"),
            ("London IND MNQ", lambda: run(M.load_min("NQ"), 8, 0, 16, 0, "IND"), "NQ"),
            ("London IND MES", lambda: run(M.load_min("ES"), 8, 0, 16, 0, "IND"), "ES"),
            ("London IND MYM", lambda: run(M.load_min("DOW"), 8, 0, 16, 0, "IND"), "DOW"),
            ("NY IND MNQ", lambda: run(load_ny("NQ"), 9, 30, 15, 55, "IND"), "NQ"),
            ("London A+ MGC (1.5-6 pt stops)", lambda: run(M.load_min("GC"), 0, 0, 16, 0, "APLUS", tick=0.1), "GC")]
    for lab, f, src in sets:
        R = f(); risk, gp, gn, go, tie = R.T
        for cs in (1.0, 0.5):
            c = cs * COSTS[src] / risk
            print("  %-31s n %4d  ties %4.1f%%  cost %.3fR x%.1f   net R: tie=loss %+.3f   tie=neutral %+.3f   tie=win %+.3f" % (
                lab, len(R), 100 * tie.mean(), (COSTS[src] / risk).mean(), cs, (gp - c).mean(), (gn - c).mean(), (go - c).mean()))
