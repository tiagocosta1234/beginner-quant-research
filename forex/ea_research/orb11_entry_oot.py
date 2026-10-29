"""ORB11_ENTRY_OOT (PREREG_ORB11_ENTRY_OOT.md): the three walk-forward entry picks on HistData 2020-01-02..2021-11-30, today's MT5 broker spreads.
   python -m forex.ea_research.orb11_entry_oot"""
import io
import zipfile

import numpy as np
import pandas as pd

import forex.ea_research.orb11_entry as oe
import forex.ea_research.presample as ps
from forex.ea_research.analog import mclass

LO, HI = pd.Timestamp("2020-01-02").timestamp(), pd.Timestamp("2021-12-01").timestamp()
HD = {"SP": "SPXUSD", "NSDQ": "NSXUSD", "NIKKEI": "JPXJPY", "ASX": "AUXAUD", "DAX": "GRXEUR"}
DAX_END = pd.Timestamp("2020-06-12").timestamp()
PICKS = {"P1 London FX": ("LON", "fx", "TOUCH", lambda T: T.tr & T.wide),
         "P2 London indices": ("LON", "index", "HOLD15", lambda T: T.sq),
         "P3 New York metals": ("NY", "metal", "TOUCH", lambda T: T.tr & T.wide)}
SESS_HRS = {"LON": ("Europe/London", 8, 17), "NY": ("America/New_York", 9, 16)}


def load_hd(sym, spread):
    code = HD.get(sym, sym); frames = []
    for yr in (2020, 2021):
        z = zipfile.ZipFile(f"data/data_histdata/DAT_ASCII_{code}_M1_{yr}.zip")
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        frames.append(pd.read_csv(io.BytesIO(z.read(name)), sep=";", header=None, names=["dt", "bo", "bh", "bl", "bc", "v"]))
    d = pd.concat(frames)
    tu = pd.to_datetime(d.dt, format="%Y%m%d %H%M%S") + pd.Timedelta(hours=5)          # HistData EST (UTC-5, no DST) -> UTC
    d["tu"] = tu.astype("datetime64[s]").astype("int64")
    d = d.sort_values("tu").drop_duplicates("tu")
    d = d[(d.tu >= LO) & (d.tu < (DAX_END if sym == "DAX" else HI))]
    srv = pd.to_datetime(d.tu, unit="s").dt.tz_localize("UTC").dt.tz_convert("Europe/Athens").dt.tz_localize(None)
    D = {k: d[k].to_numpy(float) for k in ("bo", "bh", "bl", "bc")}
    for a, b in (("ao", "bo"), ("ah", "bh"), ("al", "bl"), ("ac", "bc")):
        D[a] = D[b] + spread
    D["t"] = srv.astype("datetime64[s]").astype("int64").to_numpy()
    o = np.argsort(D["t"], kind="stable"); D = {k: v[o] for k, v in D.items()}
    D["mh"], D["ml"], D["mc"] = (D["bh"] + D["ah"]) / 2, (D["bl"] + D["al"]) / 2, (D["bc"] + D["ac"]) / 2
    return D


def run_pick(name, sess, cls, trig, filt):
    syms = [s for s in oe.SYMS if mclass(s) == cls and s != "DOW"]
    tz, a, b = SESS_HRS[sess]; out = []
    for s in syms:
        sp = ps.mt5_floor(s, tz, a, b); D = load_hd(s, sp)
        oe.load = lambda sym, end, D=D: D
        T = pd.DataFrame(oe.market((s, oe.END)), columns=oe.COLS)
        T = T[T.sess == sess]
        C = T[T.trig == "CTRL"].set_index("day").rh.rename("ch")
        X = T[T.trig == trig].join(C, on="day")
        X = X[filt(X).to_numpy()]
        out.append(X)
    X = pd.concat(out); d = X.groupby("day").rh.mean(); dc = X.groupby("day").ch.mean()
    yrs = {y: round(g.mean(), 3) for y, g in d.groupby(d.index.year)}
    t = oe.tstat(d); ok = bool(d.mean() > 0 and t >= 2.13 and all(v > 0 for v in yrs.values()))
    by_m = X.groupby("mkt").rh.agg(["size", "mean"]).round(3)
    print(f"{name}: {trig} {sess} {cls}, {len(syms)} markets, {len(X)} trades on {len(d)} days | daily mean {d.mean():+.3f} R, t {t:+.2f} | by year {yrs} | random same days {dc.mean():+.3f} | PASS {ok}")
    print("   per market:", {m: (int(r['size']), r['mean']) for m, r in by_m.iterrows()})
    X.to_parquet(f"data/si_ledgers/ORB11_ENTRY_OOT_{name.split()[0]}.parquet")
    return ok


def main():
    res = {n: run_pick(n, *p) for n, p in PICKS.items()}
    print("passing:", [n for n, v in res.items() if v])


if __name__ == "__main__":
    main()
