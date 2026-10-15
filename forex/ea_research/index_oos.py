"""INDEX-OOS exactly as in PREREG_INDEX_OOS.md: today's three index-breakout hypotheses on UK100 / FRA40 / US2000 (MT5 M1 bid/ask, never used today).
   python -m forex.ea_research.index_oos --dry | (no flag) run"""
import sys
import zlib

import numpy as np
import pandas as pd

from forex.ea_research.breakouts import local_clock
from forex.ea_research.brk_exits import exits
from forex.ea_research.orb_refine import daily_table

H, M = 3600, 60
END = pd.Timestamp("2026-10-03").timestamp()
MKTS = {"UK100.cash": ("Europe/London", 8 * H, 16 * H + 30 * M), "FRA40.cash": ("Europe/Paris", 9 * H, 17 * H + 30 * M),
        "US2000.cash": ("America/New_York", 9 * H + 30 * M, 16 * H)}


def load_mt5broker(sym, end=END):
    d = pd.read_parquet(f"forex/data/{sym}_M1_ticks_full.parquet")
    t = d["time"]
    if t.dtype.kind == "M":
        t = t.astype("int64") // 10**9
    d = d.assign(t=t.astype("int64"))
    d = d[(d.t < end) & (d.open > 0) & (d.ask_open >= d.open)].drop_duplicates("t").sort_values("t")
    D = dict(t=d.t.to_numpy(), bo=d.open.to_numpy(), bh=d.high.to_numpy(), bl=d.low.to_numpy(), bc=d.close.to_numpy(),
             ao=d.ask_open.to_numpy(), ah=d.ask_high.to_numpy(), al=d.ask_low.to_numpy(), ac=d.ask_close.to_numpy())
    D["mh"], D["ml"], D["mc"] = (D["bh"] + D["ah"]) / 2, (D["bl"] + D["al"]) / 2, (D["bc"] + D["ac"]) / 2
    return D


def run_market(sym, end=END):
    tz, op_s, cl_s = MKTS[sym]
    D = load_mt5broker(sym, end)
    t = D["t"]
    lc = local_clock(t, tz)
    dt = daily_table(D)
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
        if not Hb > Lb:
            continue
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb)
        dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        R = abs(e - (Lb if side > 0 else Hb))
        if k >= kend or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
            continue
        x = exits(D, k, kend, side, e, R)
        sday = t[i0] // 86400
        trend = np.sign(dt.at[sday, "c_prev"] - dt.at[sday, "sma_prev"]) if sday in dt.index else np.nan
        kc = int(rng.integers(i1, w1)); sc = 1 if rng.random() < 0.5 else -1
        ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
        xc = exits(D, kc, kend, sc, ec, R) if kc < kend and R >= 2 * (D["ao"][kc] - D["bo"][kc]) else None
        if x is not None:
            rows.append(dict(mkt=sym, kind="H1", day=pd.Timestamp(d * 86400, unit="s"), side=side, t_entry=int(t[k]), R=x[3], C=xc[3] if xc else np.nan, trend=trend))
    # H3 month opening range (server days, Mon-Fri)
    day, sod = t // 86400, t % 86400
    st = np.flatnonzero(np.r_[True, day[1:] != day[:-1]]); en = np.r_[st[1:], len(t)]
    info = {}
    for a, b in zip(st, en):
        w = np.arange(a, b)[(sod[a:b] >= H) & (sod[a:b] < 23 * H)]
        dd = int(day[a])
        if len(w) >= 300 and (dd + 3) % 7 < 5:
            info[dd] = dict(hi=D["bh"][w].max(), lo=D["bl"][w].min(), k_open=a + np.searchsorted(sod[a:b], H + 5 * M),
                            k_close=a + np.searchsorted(sod[a:b], 21 * H + 55 * M), k_last=a + np.searchsorted(sod[a:b], 22 * H + 55 * M))
    months = {}
    for dd in sorted(info):
        months.setdefault(pd.Timestamp(dd * 86400, unit="s").to_period("M"), []).append(dd)
    for mth, ds in sorted(months.items()):
        if len(ds) < 10:
            continue
        hb, lb = max(info[x]["hi"] for x in ds[:3]), min(info[x]["lo"] for x in ds[:3])
        f15 = [x for x in ds[3:] if pd.Timestamp(x * 86400, unit="s").day <= 15]
        if not f15:
            continue
        wa, wb, kend = info[ds[3]]["k_open"], info[f15[-1]]["k_last"], min(info[ds[-1]]["k_close"], len(t) - 1)
        up = np.flatnonzero(D["ah"][wa:wb] >= hb); dn = np.flatnonzero(D["bl"][wa:wb] <= lb)
        ku, kd = (wa + up[0] if len(up) else None), (wa + dn[0] if len(dn) else None)
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        e = max(hb, D["ao"][k]) if side > 0 else min(lb, D["bo"][k])
        R = abs(e - (lb if side > 0 else hb))
        if k >= kend or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
            continue
        x = exits(D, k, kend, side, e, R)
        kc = int(rng.integers(wa, wb)); sc = 1 if rng.random() < 0.5 else -1
        ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
        xc = exits(D, kc, kend, sc, ec, R) if kc < kend and R >= 2 * (D["ao"][kc] - D["bo"][kc]) else None
        if x is not None:
            rows.append(dict(mkt=sym, kind="H3", day=pd.Timestamp(ds[3] * 86400, unit="s"), side=side, t_entry=int(t[k]), R=x[3], C=xc[3] if xc else np.nan, trend=np.nan))
    return pd.DataFrame(rows)


def tstat(x):
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def dry():
    for s in MKTS:
        df = run_market(s)
        print(s, df.groupby("kind").size().to_dict(), "| first/last day", df.day.min().date(), df.day.max().date())
        cut = pd.Timestamp("2024-03-13 12:00").timestamp()
        f, p = run_market(s, END), run_market(s, cut)
        f = f[(f.kind == "H1") & (f.t_entry < cut - 86400)].reset_index(drop=True); p = p[(p.kind == "H1") & (p.t_entry < cut - 86400)].reset_index(drop=True)
        print("   truncation:", "PASS" if len(f) == len(p) and np.allclose(f.R, p.R) else "FAIL")
        x = df[df.kind == "H1"].iloc[100]
        print("   hand check:", x.day.date(), "side", x.side, "fill", pd.Timestamp(x.t_entry, unit="s"), "server, R", round(x.R, 3), "trend", x.trend)


def run():
    df = pd.concat([run_market(s) for s in MKTS], ignore_index=True)
    df.to_parquet("D:/finance/si_ledgers/INDEX_OOS.parquet")
    df = df[df.day >= "2022-01-01"]
    cells = {"H1 session ORB, hold to close": df[df.kind == "H1"], "H2 = H1 trend direction": df[(df.kind == "H1") & (df.side == df.trend)], "H3 month opening range": df[df.kind == "H3"]}
    from forex.ea_research.ict2 import nw_t
    for name, c in cells.items():
        tt = tstat(c.R) if "H3" in name else nw_t(c.groupby("day").R.mean().to_numpy())
        per_mkt = {m: round(g.R.mean(), 3) for m, g in c.groupby("mkt")}
        g = [c.R.mean() > 0 and tt >= 2.13, sum(v > 0 for v in per_mkt.values()) >= 2, c.R.mean() - c.C.mean() >= 0.03]
        print(f"{name}: n {len(c)} mean {c.R.mean():+.3f} R (t {tt:+.2f}) | control {c.C.mean():+.3f} | per market {per_mkt} | by year {({y: round(g_.R.mean(), 3) for y, g_ in c.groupby(c.day.dt.year)})} | gates {''.join('Y' if v else 'n' for v in g)} PASS {all(g)}")


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
