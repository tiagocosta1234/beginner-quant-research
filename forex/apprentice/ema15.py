"""PREREG_EMA15: 15m EMA12 cross with the trend, London morning, 1:1 to the nearest unmitigated FVG / clear high-low, GC futures.
python ema15.py --dry-run   counts, truncation causality test, 3 hand-check signals (no P&L)
python ema15.py --run       DEV / VAL tables -> EMA15_OUTPUT.txt, EMA15_TRADES.csv (HOLD only with --hold, after a VAL pass)"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D

HERE = os.path.dirname(os.path.abspath(__file__))
TICK, COMM = 0.1, 0.15
PER = {"DEV": ("2019-07-01", "2022-12-31"), "VAL": ("2023-01-01", "2024-12-31"), "HOLD": ("2025-01-01", "2025-12-31")}
H = lambda h, m=0: pd.Timedelta(hours=h, minutes=m)


def load(upto="2025-12-31"):
    d = D.raw(); d = d[d["lis"] < pd.Timestamp(upto) + pd.Timedelta(days=1)].reset_index(drop=True)
    b = d.set_index("lis").resample("15min", label="left", closed="left").agg({"mo": "first", "mh": "max", "ml": "min", "mc": "last"}).dropna()
    b["e12"] = b["mc"].ewm(span=12, adjust=False).mean(); b["e50"] = b["mc"].ewm(span=50, adjust=False).mean(); b["e80"] = b["mc"].ewm(span=80, adjust=False).mean()
    tr = np.maximum(b["mh"] - b["ml"], np.maximum((b["mh"] - b["mc"].shift()).abs(), (b["ml"] - b["mc"].shift()).abs())); b["atr"] = tr.rolling(14).mean()
    G = {k: g.reset_index(drop=True) for k, g in d.groupby(d["lis"].dt.normalize())}
    return G, b


def prev_wd(day):
    p = day - pd.Timedelta(days=1)
    while p.weekday() >= 5: p -= pd.Timedelta(days=1)
    return p


def levels(b, k, day, side):
    """Candidate target levels known at the close of 15m bar position k (all from bars <= k)."""
    p = prev_wd(day); w = b.iloc[:k + 1]; w = w[w.index >= p + H(8)]
    hi, lo = w["mh"].values, w["ml"].values; L = side == "L"; out = []
    for j in range(len(w) - 2):  # FVG from bars j, j+1, j+2; unmitigated = no later bar (j+3 .. k) trades into the gap
        if L and lo[j] > hi[j + 2]:
            top, bot = lo[j], hi[j + 2]
            if not (hi[j + 3:] >= bot).any(): out.append(bot)
        if not L and hi[j] < lo[j + 2]:
            bot, top = hi[j], lo[j + 2]
            if not (lo[j + 3:] <= top).any(): out.append(top)
    for j in range(2, len(w) - 2):  # 2-left / 2-right swings, unbroken through k
        if L and hi[j] >= hi[j - 2:j + 3].max() and not (hi[j + 1:] > hi[j]).any(): out.append(hi[j])
        if not L and lo[j] <= lo[j - 2:j + 3].min() and not (lo[j + 1:] < lo[j]).any(): out.append(lo[j])
    pv = w[(w.index >= p + H(8)) & (w.index < p + H(22))]; asia = w[(w.index >= day) & (w.index < day + H(8))]
    if len(pv): out.append(pv["mh"].max() if L else pv["ml"].min())
    if len(asia): out.append(asia["mh"].max() if L else asia["ml"].min())
    return out


def trend(b, k, name, d1m, day):
    c = b["mc"].iloc[k]
    if name in ("T50", "T80"):
        e = b["e50" if name == "T50" else "e80"]; up = c > e.iloc[k] and e.iloc[k] > e.iloc[k - 4]; dn = c < e.iloc[k] and e.iloc[k] < e.iloc[k - 4]
        return "L" if up else "S" if dn else None
    if name == "NONE": return "ANY"
    p = prev_wd(day); g = d1m.get(p)
    if g is None: return None
    pv = g[(g["lis"] >= p + H(8)) & (g["lis"] < p + H(22))]
    if len(pv) < 600: return None
    return "L" if pv["mc"].iloc[-1] > pv["mo"].iloc[0] else "S" if pv["mc"].iloc[-1] < pv["mo"].iloc[0] else None


def day_trade(d1m, b, day, tname, invert=False):
    g = d1m.get(day)
    if g is None: return None
    x = g[(g["lis"] >= day + H(7)) & (g["lis"] < day + H(17))]
    if len(x) < 560 or x["mc"].diff().abs().max() > 8.0: return None
    idx = b.index
    for k in np.flatnonzero((idx >= day + H(8)) & (idx <= day + H(11, 45))):
        c, e, c0, e0 = b["mc"].iloc[k], b["e12"].iloc[k], b["mc"].iloc[k - 1], b["e12"].iloc[k - 1]
        side = "L" if (c > e and c0 <= e0) else "S" if (c < e and c0 >= e0) else None
        if side is None: continue
        t = trend(b, k, tname, d1m, day)
        if t is None or (t != "ANY" and t != side): continue
        trade_side = ("S" if side == "L" else "L") if invert else side
        if k + 1 >= len(b) or idx[k + 1] != idx[k] + H(0, 15): return None
        L = side == "L"; entry_sig = b["mo"].iloc[k + 1]; atr = b["atr"].iloc[k]
        lv = [v for v in levels(b, k, day, side) if ((v > entry_sig) if L else (v < entry_sig)) and abs(v - entry_sig) >= 0.5 * atr]
        if not lv: return None  # first signal had no target in range: no trade today
        tgt = min(lv) if L else max(lv); Dd = abs(tgt - entry_sig)
        if invert: tgt, stp = (entry_sig - Dd, entry_sig + Dd) if L else (entry_sig + Dd, entry_sig - Dd)
        else: stp = entry_sig - Dd if L else entry_sig + Dd
        return simulate(d1m, idx[k + 1], trade_side, entry_sig, stp, tgt, Dd, day) | {"date": day.strftime("%Y-%m-%d"), "side": trade_side, "sig": idx[k].strftime("%H:%M")}
    return None


def simulate(d1m, t0, side, eo, stp, tgt, Dd, day):
    L = side == "L"; e = eo + (TICK if L else -TICK)
    g = d1m[day]; w = g[(g["lis"] >= t0) & (g["lis"] <= day + H(16, 30))]
    for q in w.itertuples():
        if q.lis >= day + H(16, 30): pts = (q.mo - e) if L else (e - q.mo); return {"res": "time", "R": (pts - COMM) / Dd, "R0": pts / Dd}
        if (L and q.ml <= stp) or (not L and q.mh >= stp): pts = ((stp - TICK) - e) if L else (e - (stp + TICK)); return {"res": "stop", "R": (pts - COMM) / Dd, "R0": pts / Dd}
        if (L and q.mh >= tgt + TICK) or (not L and q.ml <= tgt - TICK): pts = (tgt - e) if L else (e - tgt); return {"res": "target", "R": (pts - COMM) / Dd, "R0": pts / Dd}
    return None


def days_in(d1m, a, z):
    return [x for x in sorted(d1m) if pd.Timestamp(a) <= x <= pd.Timestamp(z) and x.weekday() < 5]


def stats(t):
    if len(t) == 0: return "n 0"
    r = t["R"].values; tt = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) if len(r) > 1 else float("nan")
    from math import erf, sqrt
    p = 0.5 * (1 - erf(tt / sqrt(2)))
    return "n %4d  win %4.1f%%  meanR %+.3f  t %+5.2f  P1 %.4f  noCostR %+.3f" % (len(r), 100 * (t["res"] == "target").mean(), r.mean(), tt, p, t["R0"].mean())


def run(periods, out):
    d1m, b = load("2025-12-31" if "HOLD" in periods else "2024-12-31"); lines = []; allt = []
    for per in periods:
        a, z = PER[per]; days = days_in(d1m, a, z); lines.append("== %s %s..%s (%d weekdays)" % (per, a, z, len(days)))
        for name, inv in (("T50", False), ("T80", False), ("TPD", False), ("NONE", False), ("T50", True)):
            rows = [r for r in (day_trade(d1m, b, dd, name, inv) for dd in days) if r]
            t = pd.DataFrame(rows); lab = name + (" INVERTED" if inv else "")
            lines.append("  %-13s %s" % (lab, stats(t)))
            if len(t):
                for s in ("L", "S"): lines.append("     %s-only   %s" % (s, stats(t[t["side"] == s])))
                t["trial"] = lab; t["period"] = per; allt.append(t)
        print("\n".join(lines[-16:]), flush=True)
    open(os.path.join(HERE, out), "w").write("\n".join(lines) + "\n")
    pd.concat(allt).to_csv(os.path.join(HERE, out.replace("OUTPUT.txt", "TRADES.csv")), index=False)


def dry():
    d1m, b = load("2022-12-31"); days = days_in(d1m, *PER["DEV"])
    n = {k: sum(1 for dd in days if day_trade(d1m, b, dd, k)) for k in ("T50", "T80", "TPD", "NONE")}
    print("DEV weekdays %d; trades per trial (counts only): %s" % (len(days), n))
    # truncation causality: rebuild bars with data cut at the signal bar's close and compare the target / stop
    checked = 0
    for dd in days[::40]:
        r = day_trade(d1m, b, dd, "T50")
        if not r: continue
        cut = pd.Timestamp(r["date"]) + H(int(r["sig"][:2]), int(r["sig"][3:])) + H(0, 15)
        d2 = pd.concat([g for k_, g in d1m.items() if k_ <= pd.Timestamp(r["date"])]); d2 = d2[d2["lis"] < cut + H(0, 15)]  # keep the entry bar only for its open
        b2 = d2.set_index("lis").resample("15min", label="left", closed="left").agg({"mo": "first", "mh": "max", "ml": "min", "mc": "last"}).dropna()
        for k_, s_ in (("e12", 12), ("e50", 50), ("e80", 80)): b2[k_] = b2["mc"].ewm(span=s_, adjust=False).mean()
        tr = np.maximum(b2["mh"] - b2["ml"], np.maximum((b2["mh"] - b2["mc"].shift()).abs(), (b2["ml"] - b2["mc"].shift()).abs())); b2["atr"] = tr.rolling(14).mean()
        k = b.index.get_loc(cut - H(0, 15)); k2 = b2.index.get_loc(cut - H(0, 15))
        assert abs(b["e12"].iloc[k] - b2["e12"].iloc[k2]) < 1e-9 and abs(b["atr"].iloc[k] - b2["atr"].iloc[k2]) < 1e-9
        assert sorted(levels(b, k, pd.Timestamp(r["date"]), r["side"])) == sorted(levels(b2, k2, pd.Timestamp(r["date"]), r["side"]))
        checked += 1
        if checked <= 3: print("hand check %s signal %s side %s (levels %d)" % (r["date"], r["sig"], r["side"], len(levels(b, k, pd.Timestamp(r["date"]), r["side"]))))
    print("truncation causality test passed on %d signal days" % checked)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--dry-run"]: dry()
    elif a[:1] == ["--run"]: run(["DEV", "VAL"] + (["HOLD"] if "--hold" in a else []), "EMA15_OUTPUT.txt" if "--hold" not in a else "EMA15_HOLD_OUTPUT.txt")
    else: sys.exit(__doc__)
