"""PREREG_EMA15B: ema15.py with a 2.5-point minimum target and $1,000-target sizing (max 40 MGC). ema15.py is unchanged.
python ema15b.py --dry-run | --run [--hold]"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ema15 as E

MIN_PTS, MAX_MGC, TGT_USD = 2.5, 40, 1000.0


def day_trade(G, b, day, tname):
    g = G.get(day)
    if g is None: return None
    x = g[(g["lis"] >= day + E.H(7)) & (g["lis"] < day + E.H(17))]
    if len(x) < 560 or x["mc"].diff().abs().max() > 8.0: return None
    idx = b.index
    for k in np.flatnonzero((idx >= day + E.H(8)) & (idx <= day + E.H(11, 45))):
        c, e, c0, e0 = b["mc"].iloc[k], b["e12"].iloc[k], b["mc"].iloc[k - 1], b["e12"].iloc[k - 1]
        side = "L" if (c > e and c0 <= e0) else "S" if (c < e and c0 >= e0) else None
        if side is None: continue
        t = E.trend(b, k, tname, G, day)
        if t is None or (t != "ANY" and t != side): continue
        if k + 1 >= len(b) or idx[k + 1] != idx[k] + E.H(0, 15): return None
        L = side == "L"; eo = b["mo"].iloc[k + 1]
        lv = [v for v in E.levels(b, k, day, side) if ((v > eo) if L else (v < eo)) and abs(v - eo) >= MIN_PTS]
        if not lv: return None
        tgt = min(lv) if L else max(lv); Dd = abs(tgt - eo); stp = eo - Dd if L else eo + Dd
        r = E.simulate(G, idx[k + 1], side, eo, stp, tgt, Dd, day)
        if r is None: return None
        n = int(max(1, min(MAX_MGC, TGT_USD // (10 * Dd))))
        return r | {"date": day.strftime("%Y-%m-%d"), "side": side, "sig": idx[k].strftime("%H:%M"), "D": round(Dd, 2), "mgc": n, "usd": round(r["R"] * Dd * 10 * n, 2)}
    return None


def stats(t, years):
    if len(t) == 0: return "n 0"
    r = t["R"].values; tt = r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))
    from math import erf, sqrt
    p = 0.5 * (1 - erf(tt / sqrt(2))); u = t["usd"].values; cum = np.cumsum(u); dd = (np.maximum.accumulate(np.r_[0, cum]) - np.r_[0, cum]).max()
    return "n %4d  win %4.1f%%  meanR %+.3f  t %+5.2f  P1 %.4f  noCostR %+.3f | $/trade %+6.0f  $/yr %+7.0f  maxDD $%6.0f  medD %.2f medMGC %d" % (
        len(r), 100 * (t["res"] == "target").mean(), r.mean(), tt, p, t["R0"].mean(), u.mean(), u.sum() / years, dd, t["D"].median(), t["mgc"].median())


def run(periods):
    G, b = E.load("2025-12-31" if "HOLD" in periods else "2024-12-31"); lines = []; allt = []
    for per in periods:
        a, z = E.PER[per]; days = E.days_in(G, a, z); yrs = (pd.Timestamp(z) - pd.Timestamp(a)).days / 365.25
        lines.append("== %s %s..%s (%d weekdays)" % (per, a, z, len(days)))
        for name in ("T50", "T80", "TPD", "NONE"):
            t = pd.DataFrame([r for r in (day_trade(G, b, dd, name) for dd in days) if r]); lines.append("  %-5s %s" % (name, stats(t, yrs)))
            if len(t): t["trial"] = name; t["period"] = per; allt.append(t)
    print("\n".join(lines)); tag = "_HOLD" if "HOLD" in periods else ""
    open(os.path.join(E.HERE, "EMA15B%s_OUTPUT.txt" % tag), "w").write("\n".join(lines) + "\n")
    pd.concat(allt).to_csv(os.path.join(E.HERE, "EMA15B%s_TRADES.csv" % tag), index=False)


def dry():
    G, b = E.load("2022-12-31"); days = E.days_in(G, *E.PER["DEV"])
    rs = {k: [r for r in (day_trade(G, b, dd, k) for dd in days) if r] for k in ("T50", "T80", "TPD", "NONE")}
    print("DEV trades per trial (counts only):", {k: len(v) for k, v in rs.items()})
    v = pd.DataFrame(rs["T50"]); print("T50 target distance D: median %.2f, min %.2f, p90 %.2f; MGC median %d, min %d, max %d" % (v.D.median(), v.D.min(), v.D.quantile(.9), v.mgc.median(), v.mgc.min(), v.mgc.max()))
    assert (v.D >= MIN_PTS).all() and (v.mgc <= MAX_MGC).all()


if __name__ == "__main__":
    a = sys.argv[1:]
    dry() if a[:1] == ["--dry-run"] else run(["DEV", "VAL"] + (["HOLD"] if "--hold" in a else [])) if a[:1] == ["--run"] else sys.exit(__doc__)
