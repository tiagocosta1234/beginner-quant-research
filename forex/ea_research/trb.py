"""TRB exactly as in PREREG_TRB.md: time-range breakout with reel 13's selection process, run walk-forward.
   python -m forex.ea_research.trb --dry     counts, truncation test, hand check (no P&L of the process)
   python -m forex.ea_research.trb           real run + random-selection placebo 81-83"""
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_research.crt import load
from forex.ea_research.ict2 import SYMS, nw_t

END = pd.Timestamp("2026-01-01").timestamp()           # 2026 sealed
H, M = 3600, 60
SLOTS = [H + 30 * M * i for i in range(39)]             # 01:00 .. 20:00 server
LENS = (5, 15, 30)
SLS = (0.5, 1.0)
TPS = (0.5, 1.0, 2.0, 3.0)
MODES = ("BOTH", "LONG", "SHORT")
INDICES = ("SP", "NSDQ", "DOW", "DAX")
DEV = ("2022-07-01", "2024-12-31")
VAL = ("2025-01-01", "2025-12-31")
CACHE = Path("D:/finance/tmp/trb_cache")


def outcomes(D, k, side, e, rng, kend):
    """net and gross R for the 8 (SL, TP) sets of one filled stop order."""
    n = kend - k
    out = np.full((2, len(SLS), len(TPS)), np.nan)
    if n <= 0:
        return out
    sp = D["ao"][k] - D["bo"][k]
    if side > 0:
        adv = np.maximum.accumulate(e - D["bl"][k:kend])
        fav = np.maximum.accumulate(D["bh"][k:kend] - e)
    else:
        adv = np.maximum.accumulate(D["ah"][k:kend] - e)
        fav = np.maximum.accumulate(e - D["al"][k:kend])
    for a, s in enumerate(SLS):
        dist = s * rng
        if dist < 2 * sp:
            continue
        i_s = np.searchsorted(adv, dist)
        for b, tp in enumerate(TPS):
            i_t = np.searchsorted(fav, tp * rng)
            if i_s >= n and i_t >= n:
                x = D["bo"][kend] if side > 0 else D["ao"][kend]
            elif i_s <= i_t:
                j = k + i_s
                x = min(e - dist, D["bo"][j]) if side > 0 else max(e + dist, D["ao"][j])
            else:
                x = e + side * tp * rng
            r = side * (x - e) / dist
            out[0, a, b], out[1, a, b] = r, r + sp / dist
    return out


def market(args):
    """R[day, slot, len, mode, sl, tp] (net), G (gross), vol[day, slot], day stamps."""
    sym, end = args
    D = load(sym, end)
    t = D["t"]
    mid_o = (D["bo"] + D["ao"]) / 2
    day, sod = t // 86400, t % 86400
    st = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    en = np.r_[st[1:], len(t)]
    nd = len(st)
    R = np.full((nd, len(SLOTS), len(LENS), len(MODES), len(SLS), len(TPS)), np.nan, np.float32)
    G = np.full_like(R, np.nan)
    V = np.full((nd, len(SLOTS)), np.nan)
    for di, (a, b) in enumerate(zip(st, en)):
        s = sod[a:b]
        if b - a < 300:
            continue
        cap = a + np.searchsorted(s, 22 * H + 55 * M)
        if cap >= b:
            cap = b - 1
        for si, T in enumerate(SLOTS):
            i0 = a + np.searchsorted(s, T)
            i15 = a + np.searchsorted(s, T + 15 * M)
            if i0 < b and i15 < b and sod[i0] < T + 5 * M:
                V[di, si] = abs(mid_o[i15] / mid_o[i0] - 1)
            for li, L in enumerate(LENS):
                r1 = a + np.searchsorted(s, T + L * M)
                w1 = a + np.searchsorted(s, T + L * M + 120 * M)
                ke = min(a + np.searchsorted(s, T + L * M + 240 * M), cap)
                if r1 - i0 < max(3, L // 2) or w1 - r1 < 30 or ke <= r1:
                    continue
                hi = ((D["bh"][i0:r1] + D["ah"][i0:r1]) / 2).max()
                lo = ((D["bl"][i0:r1] + D["al"][i0:r1]) / 2).min()
                rng = hi - lo
                if not rng > 0:
                    continue
                okm = (sod[r1:w1] % H) >= M                              # minute :00 never triggers
                up = np.flatnonzero((D["ah"][r1:w1] >= hi) & okm)
                dn = np.flatnonzero((D["bl"][r1:w1] <= lo) & okm)
                ku = r1 + up[0] if len(up) else None
                kd = r1 + dn[0] if len(dn) else None
                fills = {}
                if ku is not None:
                    fills[1] = (ku, max(hi, D["ao"][ku]))
                if kd is not None:
                    fills[-1] = (kd, min(lo, D["bo"][kd]))
                for mi, mode in enumerate(MODES):
                    if mode == "LONG":
                        f = fills.get(1)
                        side = 1
                    elif mode == "SHORT":
                        f = fills.get(-1)
                        side = -1
                    else:
                        if ku is None and kd is None:
                            continue
                        if ku is not None and kd is not None and ku == kd:
                            continue
                        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
                        f = fills[side]
                    if f is None or f[0] >= ke:
                        continue
                    o = outcomes(D, f[0], side, f[1], rng, ke)
                    R[di, si, li, mi], G[di, si, li, mi] = o[0], o[1]
    days = pd.to_datetime(day[st] * 86400, unit="s")
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE / f"{sym}.npz", R=R, G=G, V=V, days=days.values.astype("datetime64[s]").astype(np.int64))
    return sym


def walk(sym, seed=None):
    """the selection process month by month; returns DataFrame of traded days (net R, gross R) for the chosen configurations."""
    z = np.load(CACHE / f"{sym}.npz")
    R, G, V = z["R"], z["G"], z["V"]
    days = pd.to_datetime(z["days"], unit="s")
    nd = len(days)
    Rf = R.reshape(nd, len(SLOTS), -1)                       # [day, slot, cfg-in-slot]
    rng = np.random.default_rng(seed) if seed is not None else None
    rows, illus = [], []
    for m in pd.date_range("2022-07-01", "2025-12-01", freq="MS"):
        p3 = (days >= m - pd.DateOffset(months=3)) & (days < m)
        p6 = (days >= m - pd.DateOffset(months=6)) & (days < m)
        cur = (days >= m) & (days < m + pd.DateOffset(months=1))
        if p6.sum() < 60 or not cur.any():
            continue
        vol = np.nanmean(V[p3], axis=0)
        if np.all(np.isnan(vol)):
            continue
        top_slots = np.argsort(np.where(np.isnan(vol), -1, vol))[::-1][:4]
        sub3 = Rf[p3][:, top_slots]                          # [d, 4, cfg]
        tot3 = np.nansum(sub3, axis=0)
        cnt3 = np.sum(~np.isnan(sub3), axis=0)
        tot3 = np.where(cnt3 >= 15, tot3, -np.inf)
        flat = tot3.ravel()
        if not np.isfinite(flat).any():
            continue
        if rng is None:
            order = np.argsort(flat)[::-1][:2]
            order = [o for o in order if np.isfinite(flat[o])]
            tot6 = [np.nansum(Rf[p6][:, top_slots].reshape(p6.sum(), -1)[:, o]) for o in order]
            pick = order[int(np.argmax(tot6))]
        else:
            pick = int(rng.choice(np.flatnonzero(np.isfinite(flat))))
        si, ci = top_slots[pick // Rf.shape[2]], pick % Rf.shape[2]
        r_now = Rf[cur][:, si, ci]
        g_now = G.reshape(nd, len(SLOTS), -1)[cur][:, si, ci]
        ok = ~np.isnan(r_now)
        illus.append((m, flat[pick] / max(cnt3.ravel()[pick], 1), np.nanmean(r_now) if ok.any() else np.nan))
        cfg = np.unravel_index(ci, (len(LENS), len(MODES), len(SLS), len(TPS)))
        tag = f"T{SLOTS[si] // H:02d}:{SLOTS[si] % H // M:02d} L{LENS[cfg[0]]} {MODES[cfg[1]]} SL{SLS[cfg[2]]} TP{TPS[cfg[3]]}"
        for d, r, g in zip(days[cur][ok], r_now[ok], g_now[ok]):
            rows.append((sym, d, r, g, tag))
    return pd.DataFrame(rows, columns=["mkt", "day", "R", "gR", "cfg"]), pd.DataFrame(illus, columns=["month", "insample_R", "next_R"]).assign(mkt=sym)


def build(end=END):
    with ProcessPoolExecutor(8) as ex:
        list(ex.map(market, [(s, end) for s in SYMS]))


def stats(df, a, b):
    x = df[(df.day >= a) & (df.day <= b)]
    return len(x), x.R.mean(), x.gR.mean(), nw_t(x.groupby("day").R.mean().to_numpy())


def dry():
    t0 = time.time()
    build()
    print(f"cache built {time.time() - t0:.0f}s")
    z = np.load(CACHE / "NSDQ.npz")
    print("NSDQ: days", len(z["days"]), "| share of day x config cells with a trade:", round(float(np.mean(~np.isnan(z["R"]))), 3))
    w, il = walk("NSDQ")
    print("NSDQ walk-forward trades", len(w), "| months", len(il), "| first configs:", w.drop_duplicates("cfg").cfg.head(4).tolist())
    # truncation: day rows before a cut must not change when later data is removed
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    bad = 0
    for s in ("EURUSD", "XAUUSD"):
        market((s, END))
        full = np.load(CACHE / f"{s}.npz")
        Rf, df_ = full["R"].copy(), full["days"].copy()
        market((s, cut))
        part = np.load(CACHE / f"{s}.npz")
        k = np.flatnonzero(part["days"] < cut - 86400)
        bad += int(not np.allclose(np.nan_to_num(Rf[k], nan=9e9), np.nan_to_num(part["R"][k], nan=9e9)))
        market((s, END))
    print("truncation test:", "PASS" if bad == 0 else f"FAIL {bad}")


def run():
    t0 = time.time()
    if "--reuse" not in sys.argv:
        build()
    print(f"cache {time.time() - t0:.0f}s", flush=True)
    res = {}
    for world in ("real", 81, 82, 83):
        parts = [walk(s, None if world == "real" else world) for s in SYMS]
        res[world] = (pd.concat([p[0] for p in parts]), pd.concat([p[1] for p in parts]))
    w, il = res["real"]
    w.to_parquet("D:/finance/si_ledgers/TRB_trades.parquet")
    rows = []
    for world, (df, _) in res.items():
        for cell, x in (("W1", df), ("W2", df[df.mkt.isin(INDICES)])):
            nD, mD, gD, tD = stats(x, *DEV)
            nV, mV, gV, tV = stats(x, *VAL)
            yrs = [x[x.day.dt.year == y].R.mean() for y in (2022, 2023, 2024, 2025)]
            rows.append(dict(cell=cell, world=str(world), nD=nD, mD=mD, gD=gD, tD=tD, nV=nV, mV=mV, gV=gV, tV=tV, y22=yrs[0], y23=yrs[1], y24=yrs[2], y25=yrs[3]))
    R = pd.DataFrame(rows)
    R.to_csv("D:/finance/si_ledgers/TRB_cells.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.round(3).to_string(index=False))
    for cell in ("W1", "W2"):
        plc = R[(R.cell == cell) & (R.world != "real")]
        r = R[(R.cell == cell) & (R.world == "real")].iloc[0]
        ceil = np.percentile(R[R.world != "real"].tD, 95)
        x = w if cell == "W1" else w[w.mkt.isin(INDICES)]
        dv = x[x.day <= DEV[1]]
        bym = dv.groupby("mkt").R.sum()
        conc = bym.max() / bym.sum() if bym.sum() > 0 else np.inf
        g = [r.mD >= 0.05 and r.tD >= 2.24, r.mV > 0 and r.tV >= 1.65, sum(v > 0 for v in (r.y22, r.y23, r.y24, r.y25)) >= 3, r.tD > ceil, cell == "W2" or conc <= 0.40]
        print(f"{cell}: DEV n {r.nD} net {r.mD:+.3f}R (gross {r.gD:+.3f}) t {r.tD:+.2f} | VAL n {r.nV} net {r.mV:+.3f}R t {r.tV:+.2f} | random-pick placebo DEV {plc.mD.min():+.3f}..{plc.mD.max():+.3f} | gates {''.join('Y' if v else 'n' for v in g)} PASS {all(g)}")
    ii = il.dropna()
    print(f"\nIN-SAMPLE ILLUSION: the selected configurations averaged {ii.insample_R.mean():+.3f} R/trade over their 3-month selection window and {ii.next_R.mean():+.3f} R/trade the month after "
          f"(correlation {ii.insample_R.corr(ii.next_R):+.3f}, {len(ii)} market-months)")
    bm = w.assign(per=np.where(w.day <= DEV[1], "D", "V")).groupby(["mkt", "per"]).R.mean().unstack()
    print("markets positive in both periods:", bm[(bm.D > 0) & (bm.V > 0)].round(3).to_dict("index"))
    print("indices by market:", w[w.mkt.isin(INDICES)].assign(per=np.where(w[w.mkt.isin(INDICES)].day <= DEV[1], "D", "V")).groupby(["mkt", "per"]).R.agg(["size", "mean"]).round(3).to_string())


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
