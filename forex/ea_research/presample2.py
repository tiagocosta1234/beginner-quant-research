"""PRESAMPLE2 exactly as in PREREG_PRESAMPLE2.md: the London session breakout (PRESAMPLE L1 rule) on GBPUSD, EURUSD, CADJPY, USDCHF, 2020-01-02..2021-11-30, HistData.
   python -m forex.ea_research.presample2"""
import io
import zipfile

import numpy as np
import pandas as pd

import forex.ea_research.presample as ps
from forex.ea_research.ict2 import nw_t

PAIRS = ("GBPUSD", "EURUSD", "CADJPY", "USDCHF")
LO, HI = pd.Timestamp("2020-01-02").timestamp(), pd.Timestamp("2021-12-01").timestamp()


def load_hd(sym, floor):
    frames = []
    for yr in (2020, 2021):
        z = zipfile.ZipFile(f"D:/finance/data_histdata/DAT_ASCII_{sym}_M1_{yr}.zip")
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        frames.append(pd.read_csv(io.BytesIO(z.read(name)), sep=";", header=None, names=["dt", "bo", "bh", "bl", "bc", "v"]))
    d = pd.concat(frames)
    d["t_utc"] = (pd.to_datetime(d.dt, format="%Y%m%d %H%M%S") + pd.Timedelta(hours=5)).astype("datetime64[s]").astype("int64")
    d = d.sort_values("t_utc").drop_duplicates("t_utc")
    d = d[(d.t_utc >= LO) & (d.t_utc < HI)]
    D = {k: d[k].to_numpy(float) for k in ("bo", "bh", "bl", "bc")}
    for a, b in (("ao", "bo"), ("ah", "bh"), ("al", "bl"), ("ac", "bc")):
        D[a] = D[b] + floor
    D["t"] = d.t_utc.to_numpy(np.int64)
    loc = pd.to_datetime(D["t"], unit="s").tz_localize("UTC").tz_convert("Europe/London").tz_localize(None)
    D["lc"] = loc.values.astype("datetime64[s]").astype(np.int64)
    return D


def tstat(x):
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def main():
    rng = np.random.default_rng(2021)
    res = {}
    for sym in PAIRS:
        fl = ps.mt5_floor(sym, "Europe/London", 8, 17)
        D = load_hd(sym, fl)
        df = ps.l1_usdjpy(D, rng)
        res[sym] = df
        yrs = {y: round(g.R.mean(), 3) for y, g in df.groupby(df.day.dt.year)}
        g = [df.R.mean() > 0 and tstat(df.R) >= 2.33, all(v > 0 for v in yrs.values())]
        print(f"{sym} (MT5 broker spread floor {fl:.5f}, price median {np.median(D['bc']):.4f}): n {len(df)} {df.R.mean():+.3f} R (t {tstat(df.R):+.2f}) | random {df.C.mean():+.3f} | by year {yrs} | gates {''.join('Y' if z else 'n' for z in g)} PASS {all(g)}")
    allp = pd.concat([v.assign(mkt=k) for k, v in res.items()])
    allp.to_parquet("D:/finance/si_ledgers/PRESAMPLE2.parquet")
    dm = allp.groupby("day").R.mean()
    yrs = {y: round(g.mean(), 3) for y, g in dm.groupby(dm.index.year)}
    g = [dm.mean() > 0 and nw_t(dm.to_numpy()) >= 2.33, all(v > 0 for v in yrs.values())]
    print(f"P5 the four pooled: days {len(dm)} {dm.mean():+.3f} R a day-trade (daily t {nw_t(dm.to_numpy()):+.2f}) | by year {yrs} | gates {''.join('Y' if z else 'n' for z in g)} PASS {all(g)}")
    pre = pd.read_parquet("D:/finance/si_ledgers/PRESAMPLE.parquet")
    book = pd.concat([allp[["day", "R"]], pre[pre.lead == "L1"][["day", "R"]]])
    bm = book.groupby("day").R.mean()
    print(f"context - five-pair book with USDJPY: {bm.mean():+.3f} R a day-trade (daily t {nw_t(bm.to_numpy()):+.2f}); correlation of daily R between pairs:")
    piv = allp.pivot_table(index="day", columns="mkt", values="R").join(pre[pre.lead == "L1"].set_index("day").R.rename("USDJPY"))
    print(piv.corr().round(2).to_string())


if __name__ == "__main__":
    main()
