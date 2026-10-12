"""IN (NR7 volatility-compression breakout on gold and the indices) and PH (pre-holiday, option-expiry Friday) on MT5 broker data (PREREG_OUTSIDE_BOX.md).   python -m mt5broker.ea_research.calendar_nr7"""
import numpy as np, pandas as pd
from mt5broker.ea_research import more_eas as ME

DEV, VAL, HOLD = ME.DEV, ME.VAL, ME.HOLD
HOLI = ["2022-01-17", "2022-02-21", "2022-04-15", "2022-05-30", "2022-06-20", "2022-07-04", "2022-09-05", "2022-11-24", "2022-12-26", "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29", "2023-06-19", "2023-07-04", "2023-09-04", "2023-11-23", "2023-12-25",
        "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27", "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25", "2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
        "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07"]


def stats(s, w):
    d = ME.win(s, w); n = len(d)
    return dict(n=n, mean=d.mean() if n else np.nan, t=d.mean() / (d.std(ddof=1) / np.sqrt(n)) if n > 2 else np.nan)


def fmt(s): return f"n {s['n']:4d} | mean {s['mean']:+7.1f} bp | t {s['t']:.2f}" if s["n"] else "no trades"


def nr7(m):
    d = ME.load(m).copy(); key = d.date + pd.to_timedelta((d.hm >= 1559).astype(int), unit="D"); wd = key.dt.dayofweek; key = key + pd.to_timedelta(np.where(wd == 5, 2, np.where(wd == 6, 1, 0)), unit="D"); d["k"] = key
    bo, bl, bc, bh, ao = d.bo.values, d.bl.values, d.bc.values, d.bh.values if "bh" in d else np.maximum(d.bo, d.bc).values, d.ao.values; ks = d.k.values
    grp = d.groupby("k"); idx = {k: (g.index[0], g.index[-1]) for k, g in grp}; days = sorted(idx); H = {k: bh[idx[k][0]:idx[k][1] + 1].max() for k in days}; L = {k: bl[idx[k][0]:idx[k][1] + 1].min() for k in days}
    rng = pd.Series({k: H[k] - L[k] for k in days}); out = {}
    for i in range(7, len(days) - 1):
        k = days[i]; w = rng.iloc[i - 6:i + 1]
        if rng.iloc[i] > w.min() or (days[i + 1] - k).days > 4: continue
        a, b = idx[days[i + 1]]; seg_h, seg_l = bh[a:b + 1], bl[a:b + 1]; up = np.nonzero(seg_h >= H[k])[0]; dn = np.nonzero(seg_l <= L[k])[0]; u, v = (up[0] if len(up) else 10**9), (dn[0] if len(dn) else 10**9)
        if u == v: continue
        if u < v:
            j = a + u; entry = max(H[k], d.bo.iat[j]) + (ao[j] - d.bo.iat[j]); exit_ = bc[b]; ret = exit_ / entry - 1
        else:
            j = a + v; entry = min(L[k], d.bo.iat[j]); exit_ = bc[b] + (ao[b] - d.bo.iat[b]); ret = entry / exit_ - 1
        out[days[i + 1]] = 1e4 * ret
    return pd.Series(out)


def closes(m):
    d = ME.load(m); b, a = ME.at(d, "hm", 1559, "bo", "date"), ME.at(d, "hm", 1559, "ao", "date"); i = b.index.intersection(a.index).sort_values(); return b[i], a[i]


lines = []
gold = nr7("XAUUSD"); idxs = pd.concat([nr7(m) for m in ("SP", "NSDQ", "DOW")], axis=1, sort=True).mean(axis=1).dropna()
for name, s in (("IN gold NR7", gold), ("IN indices NR7 (SP, NSDQ, DOW averaged)", idxs)):
    d, v, h = stats(s, DEV), stats(s, VAL), stats(s, HOLD); acc = bool(d["n"] >= 40 and d["mean"] >= 20 and d["t"] >= 1.65 and v["mean"] > 0)
    lines.append(f"{name}\n  DEV 2022-24: {fmt(d)}\n  VAL 2025   : {fmt(v)}\n  accepted: {acc}" + (f"\n  HOLD 2026  : {fmt(h)}" if acc else ""))
cl = {m: closes(m) for m in ("SP", "NSDQ", "DOW")}; hol = pd.to_datetime(HOLI); ph1, ph2 = {}, {}
for m, (b, a) in cl.items():
    days = b.index
    for h in hol:
        prev = days[days < h]; nxt = days[days > h]
        if len(prev) and len(nxt) and (h - prev[-1]).days <= 4 and (nxt[0] - h).days <= 5: ph1.setdefault(prev[-1], []).append(1e4 * (b[nxt[0]] / a[prev[-1]] - 1))
    for y in range(2022, 2027):
        for mo in range(1, 13):
            fr = [d for d in pd.date_range(f"{y}-{mo:02d}-01", periods=31, freq="D") if d.month == mo and d.dayofweek == 4]
            if len(fr) < 3: continue
            f = fr[2]; th = days[days < f]
            if f in days and len(th) and (f - th[-1]).days <= 3: ph2.setdefault(th[-1], []).append(1e4 * (b[f] / a[th[-1]] - 1))
for name, dct in (("PH1 pre-holiday (hold across the holiday)", ph1), ("PH2 third-Friday option expiry (Thursday close to Friday close)", ph2)):
    s = pd.Series({k: np.mean(v) for k, v in dct.items()}).sort_index(); d, v, h = stats(s, DEV), stats(s, VAL), stats(s, HOLD); acc = bool(d["mean"] >= 10 and d["t"] >= 1.65 and v["mean"] > 0)
    lines.append(f"{name}\n  DEV 2022-24: {fmt(d)}\n  VAL 2025   : {fmt(v)}\n  accepted: {acc}" + (f"\n  HOLD 2026  : {fmt(h)}" if acc else ""))
txt = "\n".join(lines); print(txt)
open(__file__.replace("calendar_nr7.py", "CALENDAR_NR7_OUTPUT.txt"), "w").write(txt)
