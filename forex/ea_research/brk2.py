"""BRK2: Asian / London / NY box breakouts (1:1, stop other side) with a relative box tick-volume filter.
Pre-registration: forex/ea_research/PREREG_BRK2.md.  --dry-run: counts only.  --run: results."""
import argparse, glob, os, numpy as np, pandas as pd
from multiprocessing import Pool
from zoneinfo import ZoneInfo
from forex.ea_research.orbx import walk, ct, CRYPTO

SRV, LIS, NY = ZoneInfo("Europe/Athens"), ZoneInfo("Europe/London"), ZoneInfo("America/New_York")
DATA = "D:/finance/beginner-quant-research/forex/data_mt5/"
VOL = "D:/finance/ticks_vol/"
CACHE = "D:/finance/scratch/brk2_trades.parquet"
DEV, VAL, HOLD = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-08-16")


def smin(day, h, m, tz):
    t = pd.Timestamp(day.year, day.month, day.day, h, m, tz=tz).tz_convert(SRV)
    return t.hour * 60 + t.minute


def boxes(day):
    """name -> (box start, box end, entry end, exit) in server minutes"""
    return {"ASIA": (smin(day, 1, 0, LIS), smin(day, 7, 0, LIS), smin(day, 11, 0, LIS), smin(day, 17, 0, LIS)),
            "LDN": (smin(day, 8, 0, LIS), smin(day, 8, 30, LIS), smin(day, 10, 0, LIS), smin(day, 17, 0, LIS)),
            "NY": (smin(day, 9, 30, NY), smin(day, 10, 0, NY), smin(day, 12, 30, NY), smin(day, 15, 55, NY))}


def trades(sym):
    d = pd.read_parquet(DATA + f"{sym}_M1_rates.parquet")
    vf = VOL + f"{sym}.parquet"
    if os.path.exists(vf):
        v = pd.read_parquet(vf, columns=["time", "tick_volume"]).rename(columns={"time": "t"})
        d = d.merge(v, on="t", how="left")
    else:
        d["tick_volume"] = np.nan
    dt = pd.to_datetime(d.t, unit="s")
    d["day"] = dt.dt.normalize(); d["hm"] = dt.dt.hour * 60 + dt.dt.minute
    d = d[d.day >= "2021-11-15"]
    out = []
    for day, g in d.groupby("day", sort=True):
        if day.weekday() >= 5:
            continue
        hm = g.hm.to_numpy()
        bh, bl, bo, bc = g.bh.to_numpy(), g.bl.to_numpy(), g.bo.to_numpy(), g.bc.to_numpy()
        ah, al, ao, ac = g.ah.to_numpy(), g.al.to_numpy(), g.ao.to_numpy(), g.ac.to_numpy()
        tv = g.tick_volume.to_numpy()
        for name, (b0, b1, e_end, x_end) in boxes(day).items():
            bm = (hm >= b0) & (hm < b1)
            need = 0.8 * (b1 - b0)
            if bm.sum() < need:
                continue
            vol = np.nansum(tv[bm]) if np.isfinite(tv[bm]).sum() >= need else np.nan
            idx = np.flatnonzero((hm >= b1) & (hm < x_end))
            row = {"day": day, "sym": sym, "box": name, "vol": vol}
            for px in ("spr", "mid"):
                if px == "mid":
                    mh, ml, mo, mc = (bh + ah) / 2, (bl + al) / 2, (bo + ao) / 2, (bc + ac) / 2
                    BH, BL, BO, BC, AH, AL, AO, AC = mh, ml, mo, mc, mh, ml, mo, mc
                else:
                    BH, BL, BO, BC, AH, AL, AO, AC = bh, bl, bo, bc, ah, al, ao, ac
                hi, lo = BH[bm].max(), BL[bm].min(); S = hi - lo
                if S <= 0 or len(idx) < 30:
                    break
                fill = None
                for i, j in enumerate(idx):
                    if hm[j] >= e_end:
                        break
                    if AH[j] >= hi:
                        fill = (i, 1, max(hi, AO[j]), hi + S, lo); break
                    if BL[j] <= lo:
                        fill = (i, -1, min(lo, BO[j]), lo - S, hi); break
                if fill is None:
                    break
                i, side, e, tp, sl = fill
                seg = (BO[idx], BH[idx], BL[idx], BC[idx]) if side == 1 else (AO[idx], AH[idx], AL[idx], AC[idx])
                ex = walk(*seg, i, side, tp, sl)
                row["side" if px == "spr" else "side_mid"] = side
                row["R" if px == "spr" else "R_mid"] = (ex - e) * side / abs(e - sl)
            row["has_vol"] = np.isfinite(vol)
            out.append(row)
    T = pd.DataFrame(out)
    # relative volume: today's box volume / median of the previous 20 trading days (same market, same box)
    T = T.sort_values(["box", "day"])
    T["rv"] = T.groupby("box").vol.transform(lambda s: s / s.shift(1).rolling(20, min_periods=15).median())
    T = T[T.day >= "2022-01-01"]
    return T[T.R.notna()] if "R" in T else T.iloc[0:0]


def build():
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    syms = sorted(os.path.basename(f)[:-17] for f in glob.glob(DATA + "*_M1_rates.parquet"))
    syms = [s for s in syms if s not in CRYPTO]
    with Pool(12) as p:
        T = pd.concat(p.map(trades, syms), ignore_index=True)
    T.to_parquet(CACHE)
    return T


def placebo(univ, keep, n=500, seed=11):
    rng = np.random.default_rng(seed)
    k = univ[keep].groupby("sym").size()
    groups = {s: g.R.to_numpy() for s, g in univ.groupby("sym")}
    out = np.empty(n)
    for b in range(n):
        out[b] = sum(rng.choice(groups[s], size=c, replace=False).sum() for s, c in k.items()) / k.sum()
    return out


TRIALS = {"A": ("ASIA", False), "A_RV": ("ASIA", True), "L_RV": ("LDN", True), "N_RV": ("NY", True),
          "L_base": ("LDN", None), "N_base": ("NY", None)}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    T = build()
    per = lambda p: (T.day >= p[0]) & (T.day < p[1])
    print(f"markets {T.sym.nunique()}, rows {len(T)}, {T.day.min().date()}..{T.day.max().date()}")

    def mask(tr):
        box, rv = TRIALS[tr]
        m = (T.box == box).to_numpy()
        if rv:
            m = m & (T.rv >= 1.5).to_numpy()
        return m

    if a.dry_run:
        for tr in TRIALS:
            m = mask(tr)
            print(f"{tr:7s} DEV {int((m & per(DEV)).sum()):6d} VAL {int((m & per(VAL)).sum()):5d} HOLD {int((m & per(HOLD)).sum()):5d}")
        print("rv coverage (share of rows with rv):", T.groupby("box").rv.apply(lambda s: round(s.notna().mean(), 3)).to_dict())
        print("rv>=1.5 share:", T.groupby("box").rv.apply(lambda s: round((s >= 1.5).mean(), 3)).to_dict())
        print("markets without tick volume:", sorted(T.groupby("sym").has_vol.mean()[lambda s: s == 0].index))
    if a.run:
        for tr in TRIALS:
            m = mask(tr); row = [f"{tr:7s}"]
            for nm, p in (("DEV", DEV), ("VAL", VAL), ("HOLD", HOLD)):
                x = T[m & per(p)]
                if nm == "HOLD":
                    row.append("HOLD sealed"); continue
                mu, t = ct(x); row.append(f"{nm} n {len(x):5d} net {mu:+.3f} t {t:+.2f} gross {x.R_mid.mean():+.3f}")
            if not tr.endswith("base"):
                dm = per(DEV).to_numpy()
                box = TRIALS[tr][0]
                univ = T[dm & (T.box == box).to_numpy()]
                if TRIALS[tr][1]:
                    univ = univ[univ.rv.notna()]
                    pl = np.quantile(placebo(univ, (univ.rv >= 1.5).to_numpy()), .95)
                else:
                    pl = 0.0
                x = T[m & dm]; mu, t = ct(x)
                ok = mu > 0 and t >= 2.5 and mu > pl and len(x) >= 300
                row.append(f"placebo95 {pl:+.3f} -> DEV {'PASS' if ok else 'FAIL'}")
            print(" | ".join(row))
