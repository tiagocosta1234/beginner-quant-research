"""BRK-USDIDX exactly as in PREREG_BRK_USDIDX.md: USD-index breakout at the London open traded through EURUSD / USDJPY.  python -m forex.ea_research.brk_usdidx"""
import zlib
import numpy as np
import pandas as pd
from forex.ea_research.breakouts import local_clock
from forex.ea_research.brk_exits import exits
from forex.ea_research.crt import load
from forex.ea_research.ict2 import nw_t

END = pd.Timestamp("2026-10-03").timestamp()
H, M = 3600, 60
DEV, VAL, Y26 = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-10-02")
LEGS = {"USDJPY": 1, "USDCHF": 1, "USDCAD": 1, "EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1}


def main():
    Ds = {s: load(s, END) for s in LEGS}
    mids = {s: pd.Series(np.log((D["bc"] + D["ac"]) / 2), index=D["t"]) for s, D in Ds.items()}
    idx = pd.concat([mids[s] * sgn for s, sgn in LEGS.items()], axis=1, join="inner").mean(axis=1)
    it = idx.index.to_numpy(); iv = idx.to_numpy()
    ilc = local_clock(it, "Europe/London")
    rows = []
    for pair, usd_sign in (("EURUSD", -1), ("USDJPY", 1)):
        D = Ds[pair]; t = D["t"]; lc = local_clock(t, "Europe/London")
        rng = np.random.default_rng(zlib.crc32(pair.encode()) + 23)
        for d in np.unique(ilc // 86400):
            base = d * 86400
            a, b = np.searchsorted(ilc, base + 8 * H), np.searchsorted(ilc, base + 8 * H + 30 * M)
            w = np.searchsorted(ilc, base + 11 * H)
            if b - a < 20 or w <= b + 10:
                continue
            hi, lo = iv[a:b].max(), iv[a:b].min()
            sig = np.flatnonzero((iv[b:w] > hi) | (iv[b:w] < lo))
            if not len(sig):
                continue
            m = b + sig[0]
            usd_up = iv[m] > hi
            side = (1 if usd_up else -1) * usd_sign
            p0, p1 = np.searchsorted(lc, base + 8 * H), np.searchsorted(lc, base + 8 * H + 30 * M)
            if p1 - p0 < 20:
                continue
            Hb, Lb = D["bh"][p0:p1].max(), D["bl"][p0:p1].min()
            k = np.searchsorted(t, it[m] + 60)                           # the next minute of the pair
            xe = np.searchsorted(lc, base + 17 * H)
            cap = np.searchsorted(t, (t[min(k, len(t) - 1)] // 86400) * 86400 + 22 * H + 55 * M)
            kend = min(xe, cap, len(t) - 1)
            if k >= kend:
                continue
            e = D["ao"][k] if side > 0 else D["bo"][k]
            stop = Lb if side > 0 else Hb
            R = abs(e - stop)
            if side * (e - stop) <= 0 or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
                continue
            x = exits(D, k, kend, side, e, R)
            kc = int(rng.integers(p1, max(np.searchsorted(lc, base + 11 * H), p1 + 1))); sc = 1 if rng.random() < 0.5 else -1
            ec = D["ao"][kc] if sc > 0 else D["bo"][kc]
            xc = exits(D, kc, kend, sc, ec, R) if kc < kend and R >= 2 * (D["ao"][kc] - D["bo"][kc]) else None
            if x:
                rows.append(dict(pair=pair, day=pd.Timestamp(d * 86400, unit="s"), side=side, R=x[3], C=xc[3] if xc else np.nan))
    df = pd.DataFrame(rows); df = df[df.day >= DEV[0]]
    df.to_parquet("data/si_ledgers/BRK_USDIDX.parquet")
    ex = pd.read_parquet("data/si_ledgers/BRK_EXITS.parquet")
    for pair, g in df.groupby("pair"):
        r = {}
        for lab, (a, b) in (("DEV", DEV), ("VAL", VAL), ("2026", Y26)):
            s = g[(g.day >= a) & (g.day <= b)]
            r[lab] = (len(s), s.R.mean(), nw_t(s.groupby("day").R.mean().to_numpy()), s.C.mean())
        gt = [r["DEV"][1] >= 0.05 and r["DEV"][2] >= 2.24, r["VAL"][1] > 0 and r["VAL"][2] >= 1.65, r["DEV"][1] - r["DEV"][3] >= 0.05 and r["VAL"][1] - r["VAL"][3] >= 0.05]
        own = ex[(ex.kind == "BRK") & (ex.mkt == pair)]
        ref = "/".join(f"{own[(own.day >= a) & (own.day <= b)].X4_noTP.mean():+.3f}" for a, b in (DEV, VAL, Y26))
        print(f"{pair} via USD index: " + " | ".join(f"{k} n{v[0]} {v[1]:+.3f} (t {v[2]:+.2f}) ctl {v[3]:+.3f}" for k, v in r.items()) + f" | own breakout {ref} | gates {''.join('Y' if z else 'n' for z in gt)} PASS {all(gt)}")


if __name__ == "__main__":
    main()
