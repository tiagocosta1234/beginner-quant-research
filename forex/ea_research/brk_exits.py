"""BRK-EXITS exactly as in PREREG_BRK_EXITS.md: nine exits on the session opening-range breakout of 46 MT5, plus a random-entry control.
   python -m forex.ea_research.brk_exits --dry     counts, truncation test, hand check
   python -m forex.ea_research.brk_exits           real run"""
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
EXITS = ("X1_t1R", "X2_t2R", "X3_t3R", "X4_noTP", "X5_BE", "X6_trail1R", "X7_trail2R", "X8_partial", "X9_time60")
DEV = ("2022-01-01", "2024-12-31")
VAL = ("2025-01-01", "2025-12-31")
Y26 = ("2026-01-01", "2026-10-02")


def first(mask):
    i = np.flatnonzero(mask)
    return i[0] if len(i) else 10**9


def exits(D, k, kend, side, e, R):
    """net R of the nine exits for one position filled at minute k (entry price e), horizon kend (exit at its open)."""
    n = kend - k
    if n <= 0:
        return None
    if side > 0:
        lo, hi, op = D["bl"][k:kend], D["bh"][k:kend], D["bo"][k:kend]
        fav, adv = hi - e, e - lo
        x_end, closes = D["bo"][kend], D["bc"][k:kend]
    else:
        lo, hi, op = D["al"][k:kend], D["ah"][k:kend], D["ao"][k:kend]
        fav, adv = e - lo, hi - e
        x_end, closes = D["ao"][kend], D["ac"][k:kend]
    sgn = side
    cfav = np.maximum.accumulate(fav)
    i_sl = first(adv >= R)
    px_sl = lambda i: (min(e - R, op[i]) if sgn > 0 else max(e + R, op[i]))
    def fixed(k_r):
        i_t = first(fav >= k_r * R)
        if i_sl == 10**9 and i_t == 10**9:
            return sgn * (x_end - e) / R
        if i_sl <= i_t:
            return sgn * (px_sl(i_sl) - e) / R
        return k_r
    out = [fixed(1), fixed(2), fixed(3)]
    out.append(sgn * ((px_sl(i_sl) if i_sl < 10**9 else x_end) - e) / R)          # X4
    # X5 breakeven after +1R (move effective from the next minute)
    i1 = first(fav >= R)
    def be_from(i_start_stop):
        if i_sl < i1 and i_sl < 10**9:
            return sgn * (px_sl(i_sl) - e) / R
        if i1 == 10**9:
            return sgn * (x_end - e) / R
        j = first(adv[i1 + 1:] >= 0)
        if j == 10**9:
            return sgn * (x_end - e) / R
        jj = i1 + 1 + j
        px = min(e, op[jj]) if sgn > 0 else max(e, op[jj])
        return sgn * (px - e) / R
    x5 = be_from(i1)
    out.append(x5)
    for d_r in (1.0, 2.0):                                                        # X6, X7 trailing
        best_prev = np.concatenate([[0.0], cfav[:-1]])
        lvl = np.maximum(-R, best_prev - d_r * R)                                 # stop level, in price distance from e
        hit = first(-adv <= lvl)                                                  # adverse excursion reaches the level
        if hit == 10**9:
            out.append(sgn * (x_end - e) / R)
        else:
            stop_px = e + sgn * lvl[hit]
            px = min(stop_px, op[hit]) if sgn > 0 else max(stop_px, op[hit])
            out.append(sgn * (px - e) / R)
    out.append(0.5 * out[0] + 0.5 * x5)                                           # X8
    if n > 60 and i_sl > 60 and sgn * (closes[59] - e) < 0.5 * R:                 # X9 time stop at minute 60
        out.append(sgn * (closes[59] - e) / R)
    else:
        out.append(out[3])
    return out


def market(args):
    sym, end = args
    D = load(sym, end)
    tz, op_s, cl_s = session(sym)
    lc = local_clock(D["t"], tz)
    t = D["t"]
    rng = np.random.default_rng(zlib.crc32(sym.encode()))
    rows = []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + op_s), np.searchsorted(lc, base + op_s + 30 * M)
        w1 = np.searchsorted(lc, base + op_s + 3 * H)
        xe = np.searchsorted(lc, base + cl_s)
        if xe >= len(t) or lc[min(xe, len(t) - 1)] // 86400 != d:
            xe -= 1
        if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1 + 30 or xe <= i1:
            continue
        cap = np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M)
        kend = min(xe, cap, len(t) - 1)
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        box = Hb - Lb
        if not box > 0:
            continue
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb)
        dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        day = pd.Timestamp(d * 86400, unit="s")
        if not (ku is None and kd is None) and not (ku is not None and ku == kd):
            side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
            k = ku if side > 0 else kd
            e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
            R = abs(e - (Lb if side > 0 else Hb))
            if k < kend and R >= 2 * (D["ao"][k] - D["bo"][k]):
                x = exits(D, k, kend, side, e, R)
                if x is not None:
                    rows.append((sym, day, "BRK", side, int(t[k]), *x))
        # control: random minute in the order window, random side, the same distance R = box
        kc = int(rng.integers(i1, w1))
        sc = 1 if rng.random() < 0.5 else -1
        ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
        if kc < kend and box >= 2 * (D["ao"][kc] - D["bo"][kc]):
            x = exits(D, kc, kend, sc, ec, box)
            if x is not None:
                rows.append((sym, day, "CTRL", sc, int(t[kc]), *x))
    return rows


COLS = ["mkt", "day", "kind", "side", "t_entry", *EXITS]


def collect(end):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=COLS)
    return df[df.day >= DEV[0]]


def dry():
    t0 = time.time()
    df = collect(END)
    print(f"{time.time() - t0:.0f}s | events: {df.groupby(['kind']).size().to_dict()} | per period BRK: DEV {((df.kind == 'BRK') & (df.day <= DEV[1])).sum()} VAL {((df.kind == 'BRK') & (df.day >= VAL[0]) & (df.day <= VAL[1])).sum()} 2026 {((df.kind == 'BRK') & (df.day >= Y26[0])).sum()}")
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    bad = 0
    for s in ("EURUSD", "XAUUSD", "NSDQ", "BTCUSD"):
        f = pd.DataFrame(market((s, END)), columns=COLS); p = pd.DataFrame(market((s, cut)), columns=COLS)
        f, p = f[f.t_entry < cut - 86400].reset_index(drop=True), p[p.t_entry < cut - 86400].reset_index(drop=True)
        bad += int(not (len(f) == len(p) and np.allclose(f[list(EXITS)].to_numpy(), p[list(EXITS)].to_numpy())))
    print("truncation test:", "PASS" if bad == 0 else f"FAIL {bad}")
    x = df[(df.mkt == "NSDQ") & (df.kind == "BRK") & (df.day == "2024-06-12")]
    print("hand check NSDQ 2024-06-12 (stop-order long at 19,474.42 expected from ORB-REFINE):", x[["side", "t_entry", *EXITS]].round(2).to_dict("records"))


def run():
    t0 = time.time()
    df = collect(END)
    df.to_parquet("data/si_ledgers/BRK_EXITS.parquet")
    print(f"run {time.time() - t0:.0f}s, {len(df)} rows")
    rows = []
    for kind in ("BRK", "CTRL"):
        g = df[df.kind == kind]
        for x in EXITS:
            r = dict(kind=kind, exit=x)
            for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
                s = g[(g.day >= a) & (g.day <= b)]
                r[f"n {lab}"], r[f"R {lab}"], r[f"t {lab}"] = len(s), s[x].mean(), nw_t(s.groupby("day")[x].mean().to_numpy())
            dv = g[(g.day >= DEV[0]) & (g.day <= DEV[1])][x]
            r["win DEV"], r["avg win"], r["avg loss"] = (dv > 0).mean(), dv[dv > 0].mean(), dv[dv <= 0].mean()
            rows.append(r)
    R = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(R.round(3).to_string(index=False))
    R.to_csv("data/si_ledgers/BRK_EXITS_cells.csv", index=False)
    b, c = R[R.kind == "BRK"].set_index("exit"), R[R.kind == "CTRL"].set_index("exit")
    for x in EXITS:
        g = [b.at[x, "R DEV"] >= 0.05 and b.at[x, "t DEV"] >= 2.6, b.at[x, "R VAL"] > 0 and b.at[x, "t VAL"] >= 1.65,
             b.at[x, "R DEV"] - c.at[x, "R DEV"] >= 0.05 and b.at[x, "R VAL"] - c.at[x, "R VAL"] >= 0.05]
        print(f"{x}: BRK DEV {b.at[x, 'R DEV']:+.3f} (t {b.at[x, 't DEV']:+.2f}) VAL {b.at[x, 'R VAL']:+.3f} 2026 {b.at[x, 'R 2026']:+.3f} | control DEV {c.at[x, 'R DEV']:+.3f} VAL {c.at[x, 'R VAL']:+.3f} | gates {''.join('Y' if v else 'n' for v in g)} PASS {all(g)}")
    brk = df[df.kind == "BRK"].assign(cls=lambda z: z.mkt.map(mclass))
    print("\nBRK by class (DEV / VAL), best exits:")
    for cls, g in brk.groupby("cls"):
        dv, vl = g[g.day <= DEV[1]], g[(g.day >= VAL[0]) & (g.day <= VAL[1])]
        print(f"  {cls:7s} n {len(dv)}/{len(vl)} | " + " ".join(f"{x[:3]} {dv[x].mean():+.3f}/{vl[x].mean():+.3f}" for x in EXITS))


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
