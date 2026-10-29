"""CRTF exactly as in PREREG_CRTF.md: Candle Range Theory with the lower-timeframe entry (F1), + weekly key level (F2), 4H 1-5-9 NY model (F3).
   python -m forex.ea_research.crtf --dry     counts, truncation test, hand check (no P&L)
   python -m forex.ea_research.crtf           real run + placebo worlds 61-63"""
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.crt import days_of
from forex.ea_research.ict2 import SYMS, fix_minute, nw_t, prep, sim

END = pd.Timestamp("2026-01-01").timestamp()           # 2026 sealed
H = 3600
SEEDS = (61, 62, 63)
DEV = ("2022-01-01", "2024-12-31")
VAL = ("2025-01-01", "2025-12-31")
YEARS = (2022, 2023, 2024, 2025)
COLS = ["mkt", "cell", "world", "day", "side", "R", "gR", "t_entry", "fs", "ft"]


def ltf_entry(D, dl, i3, side, void, target_of):
    """lower-timeframe trigger on server day dl[i3]; void = candle-2 extreme; target_of(entry) -> target price. Returns (k, e, stop, tgt, kend) or None."""
    d3 = dl[i3]
    a, b = d3["a"], d3["b"]
    sod = D["t"][a:b] % 86400
    s01 = a + np.searchsorted(sod, H)
    kmid = a + np.searchsorted(sod, 12 * H)
    if kmid >= b or s01 >= b:
        return None
    nd = D["ny"][kmid] // 86400
    t5, h5, l5, c5 = D["t5"], D["h5"], D["l5"], D["c5"]
    for ks, ke in ((2 * H, 5 * H), (7 * H, 10 * H)):
        za, zb = np.searchsorted(t5, nd * 86400 + ks), np.searchsorted(t5, nd * 86400 + ke)
        m1a = np.searchsorted(D["ny"], nd * 86400 + ks)
        if zb - za < 12 or m1a <= s01 or za < 6:
            continue
        if side > 0:
            rng_lo = D["ml"][s01:m1a].min()
            if rng_lo <= void:
                return None
        else:
            rng_hi = D["mh"][s01:m1a].max()
            if rng_hi >= void:
                return None
        for j in range(za, zb):
            if (l5[j] <= void) if side > 0 else (h5[j] >= void):
                return None
            if (l5[j] < rng_lo) if side > 0 else (h5[j] > rng_hi):
                lvl = h5[j - 6:j].max() if side > 0 else l5[j - 6:j].min()
                ext = l5[j] if side > 0 else h5[j]
                for m in range(j + 1, min(j + 25, len(c5))):
                    if (l5[m] <= void) if side > 0 else (h5[m] >= void):
                        return None
                    ext = min(ext, l5[m]) if side > 0 else max(ext, h5[m])
                    if (c5[m] > lvl) if side > 0 else (c5[m] < lvl):
                        k = fix_minute(D, D["last1"][m] + 1)
                        if k >= d3["k_out"]:
                            return None
                        e = D["ao"][k] if side > 0 else D["bo"][k]
                        tgt = target_of(e)
                        risk = abs(e - ext)
                        if risk < 2 * (D["ao"][k] - D["bo"][k]) or side * (tgt - e) < risk:
                            return None
                        return k, e, ext, tgt, d3["k_out"]
                break                     # no shift after this killzone's manipulation: try the next killzone
    return None


def week_extremes(D, dl):
    """previous server week's low/high for each day index (weeks Mon-Sun by server date)."""
    wk = np.array([(x["day"] + 3) // 7 for x in dl])
    lo = pd.Series([x["lo"] for x in dl]).groupby(wk).min()
    hi = pd.Series([x["hi"] for x in dl]).groupby(wk).max()
    return [(lo.get(w - 1, np.nan), hi.get(w - 1, np.nan)) for w in wk]


def f3_day(D, nd):
    """4H CRT 1-5-9 NY on NY day nd; returns (side, stop, target, k, kend) or None."""
    ny = D["ny"]
    i1, i5, i9, i13 = (np.searchsorted(ny, nd * 86400 + h * H) for h in (1, 5, 9, 13))
    if i5 - i1 < 120 or i9 - i5 < 120 or i9 >= len(ny) or ny[i9] // 86400 != nd or i13 >= len(ny):
        return None
    L1, H1 = D["ml"][i1:i5].min(), D["mh"][i1:i5].max()
    L2, H2, C2 = D["ml"][i5:i9].min(), D["mh"][i5:i9].max(), D["mc"][i9 - 1]
    if L2 < L1 and L1 < C2 < H1 and H2 <= H1:
        return 1, L2, H1, i9, i13
    if H2 > H1 and L1 < C2 < H1 and L2 >= L1:
        return -1, H2, L1, i9, i13
    return None


def market(args):
    sym, end, with_placebo = args
    D = prep(sym, end)
    dl = days_of(D)
    wx = week_extremes(D, dl)
    real = []
    prev = None
    for i, d in enumerate(dl):
        if d["n"] < 300:
            continue
        if prev is not None and i + 1 < len(dl):
            L1, H1 = dl[prev]["lo"], dl[prev]["hi"]
            bull = d["lo"] < L1 and L1 < d["cl"] < H1 and d["hi"] <= H1
            bear = d["hi"] > H1 and L1 < d["cl"] < H1 and d["lo"] >= L1
            if bull or bear:
                side = 1 if bull else -1
                void, tgt = (d["lo"], H1) if bull else (d["hi"], L1)
                x = ltf_entry(D, dl, i + 1, side, void, lambda e, t=tgt: t)
                if x is not None:
                    k, e, stop, tg, kend = x
                    r = sim(D, k, side, e, stop, tg, kend)
                    if r is not None:
                        key = (bull and d["lo"] < wx[i][0]) or (bear and d["hi"] > wx[i][1])
                        row = (pd.Timestamp(dl[i + 1]["day"] * 86400, unit="s"), side, r[0], r[1], int(D["t"][k]), abs(e - stop) / e, abs(tg - e) / e)
                        real.append((sym, "F1", "real") + row)
                        if key:
                            real.append((sym, "F2", "real") + row)
        prev = i
    nydays = np.unique(D["ny"] // 86400)
    for nd in nydays:
        f = f3_day(D, nd)
        if f is None:
            continue
        side, stop, tgt, k, kend = f
        k = fix_minute(D, k)
        e = D["ao"][k] if side > 0 else D["bo"][k]
        if abs(e - stop) < 2 * (D["ao"][k] - D["bo"][k]):
            continue
        r = sim(D, k, side, e, stop, tgt, kend)
        if r is not None:
            real.append((sym, "F3", "real", pd.Timestamp(nd * 86400, unit="s"), side, r[0], r[1], int(D["t"][k]), abs(e - stop) / e, abs(tgt - e) / e))
    out = list(real)
    if with_placebo:
        dd = np.array([x["day"] for x in dl])
        for sd in SEEDS:
            rng = np.random.default_rng([sd, zlib.crc32(sym.encode())])
            for (s, cell, _, day, side, _, _, _, fs, ft) in real:
                lo, hi = (DEV if day <= pd.Timestamp(DEV[1]) else VAL)
                lo_t, hi_t = pd.Timestamp(lo).timestamp(), pd.Timestamp(hi).timestamp()
                if cell == "F3":
                    cand = nydays[(nydays * 86400 >= lo_t) & (nydays * 86400 <= hi_t)]
                    nd = int(rng.choice(cand))
                    ny = D["ny"]
                    k, kend = np.searchsorted(ny, nd * 86400 + 9 * H), np.searchsorted(ny, nd * 86400 + 13 * H)
                    if k >= len(ny) or kend >= len(ny) or ny[k] // 86400 != nd:
                        continue
                    k = fix_minute(D, k)
                    e = D["ao"][k] if side > 0 else D["bo"][k]
                    r = sim(D, k, side, e, e - side * fs * e, e + side * ft * e, kend)
                    if r is not None:
                        out.append((sym, cell, str(sd), pd.Timestamp(nd * 86400, unit="s"), side, r[0], r[1], int(D["t"][k]), fs, ft))
                    continue
                cand = np.flatnonzero((dd * 86400 >= lo_t) & (dd * 86400 <= hi_t))
                cand = cand[(cand >= 1) & (cand + 1 < len(dl))]
                for _ in range(5):
                    i3 = int(rng.choice(cand))
                    void = dl[i3 - 1]["lo"] if side > 0 else dl[i3 - 1]["hi"]
                    x = ltf_entry(D, dl, i3, side, void, lambda e, f=ft, sd_=side: e + sd_ * f * e)
                    if x is None:
                        continue
                    k, e, stop, tg, kend = x
                    r = sim(D, k, side, e, stop, tg, kend)
                    if r is not None:
                        out.append((sym, cell, str(sd), pd.Timestamp(dl[i3]["day"] * 86400, unit="s"), side, r[0], r[1], int(D["t"][k]), abs(e - stop) / e, ft))
                    break
    return out


def collect(end, with_placebo):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(market, [(s, end, with_placebo) for s in SYMS]))
    df = pd.DataFrame([r for rr in res for r in rr], columns=COLS)
    return df[df.day >= pd.Timestamp(DEV[0])]


def dry():
    t0 = time.time()
    df = collect(END, False)
    df["per"] = np.where(df.day <= DEV[1], "DEV", "VAL")
    print(f"{time.time() - t0:.0f}s")
    print(df.groupby(["cell", "per"]).size().unstack())
    print("stop as % of price (median) by cell:", (df.groupby("cell").fs.median() * 100).round(3).to_dict(), "| target/stop (median):", (df.ft / df.fs).groupby(df.cell).median().round(2).to_dict())
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    bad = 0
    for s in ("EURUSD", "XAUUSD", "SP", "BTCUSD"):
        f = pd.DataFrame(market((s, END, False)), columns=COLS)
        p = pd.DataFrame(market((s, cut, False)), columns=COLS)
        f = f[f.t_entry < cut - 2 * 86400].sort_values(["t_entry", "cell"]).reset_index(drop=True)
        p = p[p.t_entry < cut - 2 * 86400].sort_values(["t_entry", "cell"]).reset_index(drop=True)
        bad += int(not (len(f) == len(p) and np.allclose(f.R, p.R) and (f.side.values == p.side.values).all()))
    print("truncation test:", "PASS" if bad == 0 else f"FAIL {bad}")
    g = df[(df.mkt == "XAUUSD") & (df.cell == "F1")].iloc[20]
    print("hand check XAUUSD F1:", g.day.date(), "side", g.side, "entry (server)", pd.Timestamp(g.t_entry, unit="s"), "stop % ", round(g.fs * 100, 3), "target % ", round(g.ft * 100, 3))


def run():
    t0 = time.time()
    df = collect(END, True)
    print(f"run {time.time() - t0:.0f}s, {len(df)} trades", flush=True)
    df.to_parquet("data/si_ledgers/CRTF_trades.parquet")
    rows = []
    for (cell, world), g in df.groupby(["cell", "world"]):
        r = dict(cell=cell, world=world)
        for per, (a, b) in (("D", DEV), ("V", VAL)):
            x = g[(g.day >= a) & (g.day <= b)]
            r[f"n{per}"], r[f"m{per}"], r[f"g{per}"] = len(x), x.R.mean(), x.gR.mean()
            r[f"t{per}"] = nw_t(x.groupby("day").R.mean().to_numpy())
        for y in YEARS:
            r[f"y{y % 100}"] = g[g.day.dt.year == y].R.mean()
        rows.append(r)
    R = pd.DataFrame(rows)
    R.to_csv("data/si_ledgers/CRTF_cells.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.round(3).to_string(index=False))
    plc = R[R.world != "real"]
    ceil = np.percentile(plc.tD, 95)
    print(f"\nplacebo (9 cells): max DEV t {plc.tD.max():.2f}, 95th pct {ceil:.2f}")
    for _, r in R[R.world == "real"].iterrows():
        allr = df[(df.cell == r.cell) & (df.world == "real")]
        dv = allr[allr.day <= DEV[1]]
        bym = dv.groupby("mkt").R.sum()
        conc = bym.max() / bym.sum() if bym.sum() > 0 else np.inf
        g = [r.mD >= 0.05 and r.tD >= 2.40, r.mV > 0 and r.tV >= 1.65, sum(r[f"y{y % 100}"] > 0 for y in YEARS) >= 3, r.tD > ceil, conc <= 0.40]
        print(f"{r.cell}: DEV n {r.nD} net {r.mD:+.3f}R (gross {r.gD:+.3f}) t {r.tD:+.2f} | VAL n {r.nV} net {r.mV:+.3f}R (gross {r.gV:+.3f}) t {r.tV:+.2f} | "
              f"years {r.y22:+.3f}/{r.y23:+.3f}/{r.y24:+.3f}/{r.y25:+.3f} | top market {conc:.2f} | win {(dv.R > 0).mean():.1%} median R {dv.R.median():+.2f} | gates {''.join('Y' if x else 'n' for x in g)} PASS {all(g)}")
        cls = allr.assign(c=allr.mkt.map(mclass), per=np.where(allr.day <= DEV[1], "DEV", "VAL")).groupby(["c", "per"]).agg(n=("R", "size"), R=("R", "mean"), gR=("gR", "mean"))
        print("  ", "; ".join(f"{c}/{p} n{int(x.n)} {x.R:+.3f} (g {x.gR:+.3f})" for (c, p), x in cls.iterrows()))
        gold = allr[allr.mkt == "XAUUSD"]
        print(f"   XAUUSD: DEV n {len(gold[gold.day <= DEV[1]])} net {gold[gold.day <= DEV[1]].R.mean():+.3f} | VAL n {len(gold[gold.day > DEV[1]])} net {gold[gold.day > DEV[1]].R.mean():+.3f}")


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
