"""ORBX: London opening-range breakout (08:00-08:30 local box, 1:1, first break 08:30-10:00) with news-day / trend
filters. Pre-registration: forex/ea_research/PREREG_ORBX.md.  --dry-run: counts only.  --run: results."""
import argparse, glob, os, numpy as np, pandas as pd
from multiprocessing import Pool
from zoneinfo import ZoneInfo

SRV, LIS = ZoneInfo("Europe/Athens"), ZoneInfo("Europe/London")
DATA = "forex/data_mt5/"
CACHE = "data/scratch/orbx_trades.parquet"
CAL = "data/data_macro/mt5_calendar.csv"
CRYPTO = {"ADAUSD", "BCHUSD", "BNBUSD", "BTCUSD", "ETHUSD", "LTCUSD", "SOLUSD", "XRPUSD"}
USD_LIKE = {"XAUUSD": ["USD"], "XAGUSD": ["USD"], "WTI": ["USD"], "BRENT": ["USD"], "SP": ["USD"], "NSDQ": ["USD"],
            "DOW": ["USD"], "DAX": ["EUR"], "NIKKEI": ["JPY"], "ASX": ["AUD"]}
DEV, VAL, INFO = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-10-03")


def ccys(sym):
    return USD_LIKE.get(sym, [sym[:3], sym[3:6]])


def smin(day, h, m):
    t = pd.Timestamp(day.year, day.month, day.day, h, m, tz=LIS).tz_convert(SRV)
    return t.hour * 60 + t.minute


def walk(o, h, l, c, i0, side, tp, sl):
    for k in range(i0, len(o)):
        if (l[k] <= sl) if side == 1 else (h[k] >= sl):
            return sl if k == i0 else (min(sl, o[k]) if side == 1 else max(sl, o[k]))
        if k > i0 and ((h[k] >= tp) if side == 1 else (l[k] <= tp)):
            return max(tp, o[k]) if side == 1 else min(tp, o[k])
    return c[-1]


def trades(sym):
    d = pd.read_parquet(DATA + f"{sym}_M1_rates.parquet")
    dt = pd.to_datetime(d.t, unit="s")
    d["day"] = dt.dt.normalize(); d["hm"] = dt.dt.hour * 60 + dt.dt.minute
    d = d[d.day >= "2021-12-20"]
    close = ((d.bc + d.ac) / 2).groupby(d.day).last()
    chg = close.diff().shift(1)                        # previous day's close-to-close change, known at the open
    out = []
    for day, g in d.groupby("day", sort=True):
        if day.weekday() >= 5 or day < pd.Timestamp("2022-01-01"):
            continue
        b0, b1, e_end, x_end = smin(day, 8, 0), smin(day, 8, 30), smin(day, 10, 0), smin(day, 17, 0)
        hm = g.hm.to_numpy(); bm = (hm >= b0) & (hm < b1)
        if bm.sum() < 25:
            continue
        bh, bl, bo, bc = g.bh.to_numpy(), g.bl.to_numpy(), g.bo.to_numpy(), g.bc.to_numpy()
        ah, al, ao, ac = g.ah.to_numpy(), g.al.to_numpy(), g.ao.to_numpy(), g.ac.to_numpy()
        idx = np.flatnonzero((hm >= b1) & (hm < x_end))
        res = {}
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
            res[px] = (side, (ex - e) * side / abs(e - sl))
        if "spr" not in res:
            continue
        side = res["spr"][0]
        c = chg.get(day, np.nan)
        out.append((day, sym, side, res["spr"][1], res["mid"][1] if "mid" in res else np.nan,
                    0 if not np.isfinite(c) or c == 0 else int(np.sign(c))))
    return pd.DataFrame(out, columns=["day", "sym", "side", "R", "R_mid", "prev_sign"])


def news_days():
    c = pd.read_csv(CAL, encoding="latin-1", usecols=["time", "currency", "importance"])
    c = c[c.importance == 3].copy()
    t = pd.to_datetime(c.time, format="%Y.%m.%d %H:%M:%S").dt.tz_localize("UTC").dt.tz_convert(LIS)
    c = c[(t.dt.hour >= 6) & (t.dt.hour < 10)].assign(day=t[(t.dt.hour >= 6) & (t.dt.hour < 10)].dt.tz_localize(None).dt.normalize())
    return set(zip(c.day, c.currency)), t.max()


def build():
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    syms = sorted(os.path.basename(f)[:-17] for f in glob.glob(DATA + "*_M1_rates.parquet"))
    syms = [s for s in syms if s not in CRYPTO]
    with Pool(12) as p:
        T = pd.concat(p.map(trades, syms), ignore_index=True)
    nd, last = news_days()
    T["news"] = [any((d, c) in nd for c in ccys(s)) for d, s in zip(T.day, T.sym)]
    T["trend"] = T.side == T.prev_sign
    T.attrs["cal_last"] = str(last)
    T.to_parquet(CACHE)
    return T


def ct(x):
    """mean R per trade and day-clustered t"""
    r = x.R.to_numpy(); m = r.mean()
    s = pd.Series(r - m).groupby(x.day.to_numpy()).sum().to_numpy()
    se = np.sqrt((s ** 2).sum()) / len(r)
    return m, m / se if se > 0 else np.nan


def placebo(dev, keep, n=500, seed=7):
    rng = np.random.default_rng(seed)
    k = dev[keep].groupby("sym").size()
    groups = {s: g.R.to_numpy() for s, g in dev.groupby("sym")}
    tot = k.sum(); out = np.empty(n)
    for b in range(n):
        out[b] = sum(rng.choice(groups[s], size=c, replace=False).sum() for s, c in k.items()) / tot
    return out


FILT = {"BASE": lambda T: np.ones(len(T), bool), "N": lambda T: T.news.to_numpy(), "T": lambda T: T.trend.to_numpy(),
        "NT": lambda T: (T.news & T.trend).to_numpy()}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    T = build()
    per = lambda p: (T.day >= p[0]) & (T.day < p[1])
    print(f"markets {T.sym.nunique()}, trades {len(T)}, {T.day.min().date()}..{T.day.max().date()}")
    if a.dry_run:
        for f in FILT:
            m = FILT[f](T)
            print(f"{f:5s} DEV {int((m & per(DEV)).sum()):6d}  VAL {int((m & per(VAL)).sum()):5d}  INFO {int((m & per(INFO)).sum()):5d}"
                  f"  markets with DEV trades {T[m & per(DEV)].sym.nunique()}")
        print("news-day share by market (DEV):", T[per(DEV)].groupby("sym").news.mean().round(2).sort_values().to_dict())
        print("trend: prev_sign==0 share", round((T.prev_sign == 0).mean(), 4))
    if a.run:
        dev = T[per(DEV)]
        for f in FILT:
            row = [f]
            for name, p in (("DEV", DEV), ("VAL", VAL), ("2026i", INFO)):
                x = T[FILT[f](T) & per(p)]
                m, t = ct(x); row.append(f"{name} n {len(x):5d} net {m:+.3f} t {t:+.2f} gross {x.R_mid.mean():+.3f}")
            if f != "BASE":
                pl = placebo(dev, FILT[f](dev))
                m_dev, t_dev = ct(dev[FILT[f](dev)])
                row.append(f"placebo95 {np.quantile(pl, .95):+.3f} -> DEV {'PASS' if (m_dev > 0 and t_dev >= 2.4 and m_dev > np.quantile(pl, .95) and FILT[f](dev).sum() >= 300) else 'FAIL'}")
            print(" | ".join(row))
