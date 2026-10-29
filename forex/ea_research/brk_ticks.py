"""BRK-TICKS exactly as in PREREG_BRK_TICKS.md: tick-level confirmation at the session breakout, MT5 broker real ticks 2025-10..2026-09.
   python -m forex.ea_research.brk_ticks --dry | (no flag) run"""
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.breakouts import local_clock, session
from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t, sim

H, M = 3600, 60
A, Z = pd.Timestamp("2025-10-01").timestamp(), pd.Timestamp("2026-10-01").timestamp()
DEVp, VALp = ("2025-10-01", "2026-03-31"), ("2026-04-01", "2026-09-30")


def ticks(sym):
    parts = []
    for p in sorted(Path(f"data/ticks/{sym}").glob("*.parquet")):
        if "2025-10" <= p.stem <= "2026-09":
            d = pd.read_parquet(p, columns=["time_msc", "bid", "ask"])
            parts.append(d[(d.bid > 0) & (d.ask >= d.bid)])
    if not parts:
        return None
    d = pd.concat(parts).sort_values("time_msc", kind="stable")
    return d.time_msc.to_numpy(), d.bid.to_numpy(), d.ask.to_numpy()


def market(sym):
    T = ticks(sym)
    if T is None:
        return []
    tm, bid, ask = T
    D = load(sym, Z + 2 * 86400)
    t = D["t"]
    tz, op_s, cl_s = session(sym)
    lc = local_clock(t, tz)
    rows = []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + op_s), np.searchsorted(lc, base + op_s + 30 * M)
        w1 = np.searchsorted(lc, base + op_s + 3 * H)
        xe = np.searchsorted(lc, base + cl_s)
        if xe >= len(t) or lc[min(xe, len(t) - 1)] // 86400 != d:
            xe -= 1
        if i1 >= len(t) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1 + 30 or xe <= i1 or not (A <= t[i0] < Z):
            continue
        cap = np.searchsorted(t, (t[i1] // 86400) * 86400 + 22 * H + 55 * M)
        kend = min(xe, cap, len(t) - 1)
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        if not Hb > Lb:
            continue
        # ticks of the box and of the order window (server-clock ms)
        b0, b1 = np.searchsorted(tm, t[i0] * 1000), np.searchsorted(tm, t[i1] * 1000)
        w_end = np.searchsorted(tm, t[min(w1, len(t) - 1)] * 1000)
        if b1 - b0 < 50 or w_end <= b1:
            continue
        up = np.flatnonzero(ask[b1:w_end] >= Hb); dn = np.flatnonzero(bid[b1:w_end] <= Lb)
        ju, jd = (b1 + up[0] if len(up) else None), (b1 + dn[0] if len(dn) else None)
        if (ju is None and jd is None) or (ju is not None and ju == jd):
            continue
        side = 1 if (jd is None or (ju is not None and ju < jd)) else -1
        j = ju if side > 0 else jd
        t_touch = tm[j]
        je = np.searchsorted(tm, t_touch + 30_000)
        if je >= len(tm):
            continue
        e = ask[je] if side > 0 else bid[je]
        stop = Lb if side > 0 else Hb
        R = abs(e - stop)
        sp_e = ask[je] - bid[je]
        if side * (e - stop) <= 0 or not (R > 0 and R >= 2 * sp_e):
            continue
        k = np.searchsorted(t, (tm[je] // 1000) // 60 * 60)               # M1 bar containing the entry
        if k >= kend:
            continue
        r = sim(D, k, side, e, stop, e + side * 1e9, kend)
        if r is None:
            continue
        mid = (bid + ask) / 2
        box_ticks = b1 - b0
        per30 = box_ticks / max((t[i1] - t[i0]) / 30, 1)
        pre = np.searchsorted(tm, t_touch - 60_000)
        dm = np.diff(mid[pre:j + 1])
        flow = side * (np.sum(dm > 0) - np.sum(dm < 0)) / max(np.sum(dm != 0), 1)
        rows.append(dict(mkt=sym, day=pd.Timestamp(d * 86400, unit="s"), side=side, R_net=r[0],
                         f_speed=side * (mid[je] - mid[j]) / R, f_activity=(je - j) / per30 if per30 > 0 else np.nan,
                         f_spread=(ask[j] - bid[j]) / np.median(ask[b0:b1] - bid[b0:b1]), f_flow=flow, t_touch=int(t_touch)))
    df = pd.DataFrame(rows)
    if len(df):
        for f in ("f_speed", "f_activity"):
            df[f + "_hi"] = df[f] > df[f].rolling(250, min_periods=40).quantile(0.67).shift(1)
    return df


def collect():
    with ProcessPoolExecutor(4) as ex:
        parts = list(ex.map(market, SYMS))
    return pd.concat([p for p in parts if len(p)], ignore_index=True)


def cells(df):
    return {"T1_fast": df[df.f_speed_hi], "T2_active": df[df.f_activity_hi], "T3_flow": df[df.f_flow >= 0.2], "T4_tight_spread": df[df.f_spread <= 1.0]}


def stats(x, a, b):
    s = x[(x.day >= a) & (x.day <= b)]
    return len(s), s.R_net.mean(), nw_t(s.groupby("day").R_net.mean().to_numpy())


def dry():
    t0 = time.time()
    df = collect()
    print(f"{time.time() - t0:.0f}s | events {len(df)} | DEV {stats(df, *DEVp)[0]} VAL {stats(df, *VALp)[0]}")
    print(df[["f_speed", "f_activity", "f_spread", "f_flow"]].describe().round(3).to_string())
    for k, v in cells(df).items():
        print(f"  {k}: DEV {stats(v, *DEVp)[0]} VAL {stats(v, *VALp)[0]}")
    x = df[df.mkt == "NSDQ"].iloc[5]
    print("hand check NSDQ:", x.day.date(), "side", x.side, "touch", pd.Timestamp(x.t_touch, unit="ms"), "speed", round(x.f_speed, 3), "activity", round(x.f_activity, 2), "spread", round(x.f_spread, 2), "flow", round(x.f_flow, 2))


def run():
    df = collect()
    df.to_parquet("data/si_ledgers/BRK_TICKS.parquet")
    b = [stats(df, *p) for p in (DEVp, VALp)]
    print(f"base: DEV n{b[0][0]} {b[0][1]:+.3f} (t {b[0][2]:+.2f}) | VAL n{b[1][0]} {b[1][1]:+.3f} (t {b[1][2]:+.2f})")
    for k, v in cells(df).items():
        r = [stats(v, *p) for p in (DEVp, VALp)]
        g = [r[0][1] >= 0.05 and r[0][2] >= 2.5, r[1][1] > 0 and r[1][2] >= 1.65, r[0][1] - b[0][1] >= 0.05 and r[1][1] - b[1][1] >= 0.05]
        print(f"{k}: DEV n{r[0][0]} {r[0][1]:+.3f} (t {r[0][2]:+.2f}) | VAL n{r[1][0]} {r[1][1]:+.3f} (t {r[1][2]:+.2f}) | gates {''.join('Y' if z else 'n' for z in g)} PASS {all(g)}")
    print("\nterciles (all events) of each feature -> mean R:")
    for f in ("f_speed", "f_activity", "f_spread", "f_flow"):
        q = pd.qcut(df[f].rank(method="first"), 3, labels=["low", "mid", "high"])
        print(f"  {f}: " + " ".join(f"{k} {v:+.3f}" for k, v in df.groupby(q, observed=True).R_net.mean().items()))
    print("by class:", {c: round(g.R_net.mean(), 3) for c, g in df.groupby(df.mkt.map(mclass))})


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
