"""Descriptive: what distinguishes London-breakout winners from losers? (the trader 2026-10-16)
London 08:00-08:30 local box, first break 08:30-10:00, SL other side, TP 1 box (1:1), exit 17:00; real bid/ask.
Features known at entry; terciles fixed on DEV 2022-24, read in DEV / VAL 2025 / 2026. Not a registered trial:
any feature that looks useful must be pre-registered before it is traded."""
import glob, os, numpy as np, pandas as pd
from multiprocessing import Pool
from zoneinfo import ZoneInfo
from forex.ea_research.orbx import walk, CRYPTO
SRV, LIS = ZoneInfo("Europe/Athens"), ZoneInfo("Europe/London")
DATA = "D:/finance/beginner-quant-research/forex/data_mt5/"
OUT = "D:/finance/scratch/ldn_feat/trades.parquet"


def smin(day, h, m):
    t = pd.Timestamp(day.year, day.month, day.day, h, m, tz=LIS).tz_convert(SRV)
    return t.hour * 60 + t.minute


def run(sym):
    d = pd.read_parquet(DATA + f"{sym}_M1_rates.parquet")
    dt = pd.to_datetime(d.t, unit="s"); d["day"] = dt.dt.normalize(); d["hm"] = dt.dt.hour * 60 + dt.dt.minute
    d = d[d.day >= "2021-11-01"]
    mid_h, mid_l, mid_c = (d.bh + d.ah) / 2, (d.bl + d.al) / 2, (d.bc + d.ac) / 2
    daily = pd.DataFrame({"h": mid_h.groupby(d.day).max(), "l": mid_l.groupby(d.day).min(), "c": mid_c.groupby(d.day).last()})
    daily["atr20"] = (daily.h - daily.l).shift(1).rolling(20, min_periods=15).mean()
    daily["ph"], daily["pl"], daily["pc"] = daily.h.shift(1), daily.l.shift(1), daily.c.shift(1)
    daily["ret5"] = (daily.c.shift(1) - daily.c.shift(6))
    out = []
    for day, g in d.groupby("day", sort=True):
        if day.weekday() >= 5 or day < pd.Timestamp("2022-01-01") or day not in daily.index:
            continue
        hm = g.hm.to_numpy()
        a0, b0, b1, e_end, x_end = smin(day, 1, 0), smin(day, 8, 0), smin(day, 8, 30), smin(day, 10, 0), smin(day, 17, 0)
        bm = (hm >= b0) & (hm < b1); am = (hm >= a0) & (hm < b0)
        if bm.sum() < 25 or am.sum() < 100:
            continue
        bh, bl, bo, bc = g.bh.to_numpy(), g.bl.to_numpy(), g.bo.to_numpy(), g.bc.to_numpy()
        ah, al, ao, ac = g.ah.to_numpy(), g.al.to_numpy(), g.ao.to_numpy(), g.ac.to_numpy()
        mh, ml, mc = (bh + ah) / 2, (bl + al) / 2, (bc + ac) / 2
        hi, lo = bh[bm].max(), bl[bm].min(); S = hi - lo
        idx = np.flatnonzero((hm >= b1) & (hm < x_end))
        if S <= 0 or len(idx) < 30:
            continue
        fill = None
        for i, j in enumerate(idx):
            if hm[j] >= e_end:
                break
            if ah[j] >= hi:
                fill = (i, 1, max(hi, ao[j]), hi + S, lo); break
            if bl[j] <= lo:
                fill = (i, -1, min(lo, bo[j]), lo - S, hi); break
        if fill is None:
            continue
        i, side, e, tp, sl = fill
        seg = (bo[idx], bh[idx], bl[idx], bc[idx]) if side == 1 else (ao[idx], ah[idx], al[idx], ac[idx])
        ex = walk(*seg, i, side, tp, sl)
        D = daily.loc[day]
        asia_h, asia_l = mh[am].max(), ml[am].min()
        p_asia_start = (mh[am][0] + ml[am][0]) / 2
        p0800 = (mh[bm][0] + ml[bm][0]) / 2
        box_close = mc[bm][-1]
        spread = np.median(ac[bm] - bc[bm])
        out.append(dict(
            day=day, sym=sym, side=side, R=(ex - e) * side / abs(e - sl),
            box_atr=S / D.atr20 if D.atr20 > 0 else np.nan,
            asia_atr=(asia_h - asia_l) / D.atr20 if D.atr20 > 0 else np.nan,
            box_asia=S / (asia_h - asia_l) if asia_h > asia_l else np.nan,
            delay=hm[idx[i]] - b1,
            spread_box=spread / S,
            beyond_asia=int((hi > asia_h) if side == 1 else (lo < asia_l)),
            beyond_pd=int((hi > D.ph) if side == 1 else (lo < D.pl)),
            asia_move=side * (p0800 - p_asia_start) / D.atr20 if D.atr20 > 0 else np.nan,
            gap_pc=side * (p0800 - D.pc) / D.atr20 if D.atr20 > 0 else np.nan,
            ret5=side * D.ret5 / D.atr20 if D.atr20 > 0 else np.nan,
            close_pos=((box_close - lo) / S if side == 1 else (hi - box_close) / S),
            dow=day.weekday()))
    return pd.DataFrame(out)


if __name__ == "__main__":
    syms = sorted(os.path.basename(f)[:-17] for f in glob.glob(DATA + "*_M1_rates.parquet"))
    syms = [s for s in syms if s not in CRYPTO]
    with Pool(12) as p:
        T = pd.concat(p.map(run, syms), ignore_index=True)
    T.to_parquet(OUT)
    print(len(T), T.day.min(), T.day.max())
