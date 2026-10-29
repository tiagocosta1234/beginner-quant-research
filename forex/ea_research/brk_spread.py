"""BRK-SPREAD exactly as in PREREG_BRK_SPREAD.md: opening-range breakouts of two-leg relative spreads (NSDQ/SP, NSDQ/DOW, XAU/XAG, BRENT/WTI, ETH/BTC).
   python -m forex.ea_research.brk_spread --dry | (no flag) run"""
import sys
import zlib

import numpy as np
import pandas as pd

from forex.ea_research.breakouts import local_clock
from forex.ea_research.crt import load
from forex.ea_research.ict2 import nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
PAIRS = {("NSDQ", "SP"): ("America/New_York", 9 * H + 30 * M, 16 * H), ("NSDQ", "DOW"): ("America/New_York", 9 * H + 30 * M, 16 * H),
         ("XAUUSD", "XAGUSD"): ("Europe/London", 8 * H, 17 * H), ("BRENT", "WTI"): ("America/New_York", 9 * H, 14 * H + 30 * M),
         ("ETHUSD", "BTCUSD"): ("America/New_York", 9 * H + 30 * M, 16 * H)}


def joined(a, b, end=END):
    A, B = load(a, end), load(b, end)
    da = pd.DataFrame({k: A[k] for k in ("t", "bo", "ao", "bc", "ac")}).set_index("t")
    db = pd.DataFrame({k: B[k] for k in ("t", "bo", "ao", "bc", "ac")}).set_index("t")
    j = da.join(db, lsuffix="_a", rsuffix="_b", how="inner")
    return j.reset_index()


def leg_value(j, i, side, at):
    """executable log spread value at minute i ('open' or 'close'), for a position of `side` being OPENED (enter) or CLOSED (exit)."""
    sfx = "o" if at == "open" else "c"
    return j[f"a{sfx}_a"].iat[i], j[f"b{sfx}_a"].iat[i], j[f"a{sfx}_b"].iat[i], j[f"b{sfx}_b"].iat[i]


def trade_value(j, i, side, opening, at="open"):
    aa, ba, ab, bb = leg_value(j, i, side, at)
    if (side > 0) == opening:          # buy A / sell B
        return np.log(aa) - np.log(bb)
    return np.log(ba) - np.log(ab)     # sell A / buy B


def run_pair(pair, end=END):
    a, b = pair
    tz, op_s, cl_s = PAIRS[pair]
    j = joined(a, b, end)
    t = j.t.to_numpy()
    lc = local_clock(t, tz)
    mid = np.log((j.bc_a + j.ac_a) / 2).to_numpy() - np.log((j.bc_b + j.ac_b) / 2).to_numpy()
    rng = np.random.default_rng(zlib.crc32((a + b).encode()))
    rows = []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + op_s), np.searchsorted(lc, base + op_s + 30 * M)
        w1 = np.searchsorted(lc, base + op_s + 3 * H)
        xe = np.searchsorted(lc, base + cl_s)
        if xe >= len(t) or lc[min(xe, len(t) - 1)] // 86400 != d:
            xe -= 1
        if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1 + 30 or xe <= i1 + 2:
            continue
        cap = np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M)
        kend = min(xe, cap, len(t) - 1)
        hi, lo = mid[i0:i1].max(), mid[i0:i1].min()
        if not hi > lo:
            continue
        def simulate(k, side, stop_lvl):
            e = trade_value(j, k, side, True)
            R = abs(e - stop_lvl)
            if R <= 0:
                return None
            for m in range(k, kend):
                if (mid[m] <= stop_lvl) if side > 0 else (mid[m] >= stop_lvl):
                    x = trade_value(j, min(m + 1, kend), side, False)
                    return side * (x - e) / R, R
            x = trade_value(j, kend, side, False)
            return side * (x - e) / R, R
        sig = np.flatnonzero((mid[i1:w1] > hi) | (mid[i1:w1] < lo))
        day = pd.Timestamp(d * 86400, unit="s")
        if len(sig) and i1 + sig[0] + 1 < kend:
            m = i1 + sig[0]
            side = 1 if mid[m] > hi else -1
            r = simulate(m + 1, side, lo if side > 0 else hi)
            if r is not None:
                kc = int(rng.integers(i1 + 1, w1)); sc = 1 if rng.random() < 0.5 else -1
                ec = trade_value(j, kc, sc, True)
                c = None
                if kc < kend:
                    stop_c = ec - sc * r[1]
                    cc = None
                    for mm in range(kc, kend):
                        if (mid[mm] <= stop_c) if sc > 0 else (mid[mm] >= stop_c):
                            cc = sc * (trade_value(j, min(mm + 1, kend), sc, False) - ec) / r[1]; break
                    c = cc if cc is not None else sc * (trade_value(j, kend, sc, False) - ec) / r[1]
                rows.append(dict(pair=f"{a}/{b}", day=day, side=side, t_entry=int(t[m + 1]), R=r[0], C=c if c is not None else np.nan, box_bp=(hi - lo) * 1e4))
    return pd.DataFrame(rows)


def dry():
    for p in PAIRS:
        df = run_pair(p)
        df = df[df.day >= DEV[0]]
        print(p, {k: int(((df.day >= a) & (df.day <= b)).sum()) for k, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26))}, "| median box", round(df.box_bp.median(), 1), "bp")
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    f, p_ = run_pair(("NSDQ", "SP")), run_pair(("NSDQ", "SP"), cut)
    f, p_ = f[f.t_entry < cut - 86400].reset_index(drop=True), p_[p_.t_entry < cut - 86400].reset_index(drop=True)
    print("truncation:", "PASS" if len(f) == len(p_) and np.allclose(f.R, p_.R) else "FAIL")
    x = f[f.day == "2024-06-12"]
    print("hand check NSDQ/SP 2024-06-12:", x[["side", "R", "box_bp"]].round(3).to_dict("records"))


def run():
    out = []
    for p in PAIRS:
        df = run_pair(p)
        df = df[df.day >= DEV[0]]
        out.append(df)
        r = {}
        for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = df[(df.day >= a) & (df.day <= b)]
            r[lab] = (len(s), s.R.mean(), nw_t(s.groupby("day").R.mean().to_numpy()), s.C.mean())
        g = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.58, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        print(f"{p[0]}/{p[1]}: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) ctl {v[3]:+.3f}" for k, v in r.items()) + f" | gates {''.join('Y' if z else 'n' for z in g)} PASS {all(g)}")
    pd.concat(out).to_parquet("data/si_ledgers/BRK_SPREAD.parquet")


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
