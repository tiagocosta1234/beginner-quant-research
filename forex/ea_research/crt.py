"""CRT exactly as in PREREG_CRT.md (daily Candle Range Theory on every MT5 broker market).
   python -m forex.ea_research.crt --dry     counts, truncation test, hand check (no P&L)
   python -m forex.ea_research.crt           real run + placebo worlds 51-53"""
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from forex.ea_research.analog import mclass
from forex.ea_research.ict2 import SYMS, nw_t, sim

END = pd.Timestamp("2026-01-01").timestamp()           # 2026 sealed
H = 3600
SEEDS = (51, 52, 53)
CELLS = {"CRT1": 1, "CRT5": 5}
DEV = ("2022-01-01", "2024-12-31")
VAL = ("2025-01-01", "2025-12-31")
YEARS = (2022, 2023, 2024, 2025)
COLS = ["mkt", "cell", "world", "day", "side", "R", "gR", "t_entry", "fs", "ft"]


def load(sym, end=END):
    d = pd.read_parquet(f"forex/data_mt5/{sym}_M1_rates.parquet")
    d = d[(d.t < end) & (d.bo > 0) & (d.ao >= d.bo)].drop_duplicates("t").sort_values("t")
    D = {c: d[c].to_numpy() for c in ("t", "bo", "bh", "bl", "ao", "ah", "al", "bc", "ac")}
    D["mh"], D["ml"], D["mc"] = (D["bh"] + D["ah"]) / 2, (D["bl"] + D["al"]) / 2, (D["bc"] + D["ac"]) / 2
    return D


def days_of(D):
    t = D["t"]
    day, sod = t // 86400, t % 86400
    st = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    en = np.r_[st[1:], len(t)]
    out = []
    for a, b in zip(st, en):
        w = np.arange(a, b)[(sod[a:b] >= H) & (sod[a:b] < 23 * H)]
        k1 = a + np.searchsorted(sod[a:b], H + 300)
        out.append(dict(day=int(day[a]), a=a, b=b, n=len(w),
                        hi=D["mh"][w].max() if len(w) else np.nan, lo=D["ml"][w].min() if len(w) else np.nan,
                        cl=D["mc"][w[-1]] if len(w) else np.nan,
                        k_in=k1 if k1 < b and sod[k1] < 2 * H else None,
                        k_out=a + min(np.searchsorted(sod[a:b], 22 * H + 55 * 60), b - a - 1)))
    return out


def trade(D, dl, i, side, fs, ft, hold):
    """enter at 01:05 of day i; stop/target as shares of the entry price; exit at 22:55 of the hold-th day."""
    k = dl[i]["k_in"]
    if k is None or i + hold - 1 >= len(dl):
        return None
    e = D["ao"][k] if side > 0 else D["bo"][k]
    return k, e, e - side * fs * e, e + side * ft * e, dl[i + hold - 1]["k_out"]


def market(args):
    sym, end, with_placebo = args
    D = load(sym, end)
    dl = days_of(D)
    real = []
    prev = None
    for i, d in enumerate(dl):
        if d["n"] < 300:
            continue
        if prev is not None and i + 1 < len(dl):
            c1 = dl[prev]
            L1, H1 = c1["lo"], c1["hi"]
            bull = d["lo"] < L1 and L1 < d["cl"] < H1 and d["hi"] <= H1
            bear = d["hi"] > H1 and L1 < d["cl"] < H1 and d["lo"] >= L1
            if bull or bear:
                side = 1 if bull else -1
                stop, tgt = (d["lo"], H1) if bull else (d["hi"], L1)
                for cell, hold in CELLS.items():
                    j = i + 1
                    k = dl[j]["k_in"]
                    if k is None or j + hold - 1 >= len(dl):
                        continue
                    e = D["ao"][k] if side > 0 else D["bo"][k]
                    if abs(e - stop) < 2 * (D["ao"][k] - D["bo"][k]):
                        continue
                    r = sim(D, k, side, e, stop, tgt, dl[j + hold - 1]["k_out"])
                    if r is not None:
                        real.append((sym, cell, "real", pd.Timestamp(dl[j]["day"] * 86400, unit="s"), side, r[0], r[1], int(D["t"][k]),
                                     abs(e - stop) / e, abs(tgt - e) / e))
        prev = i
    out = list(real)
    if with_placebo:
        dd = np.array([x["day"] for x in dl])
        for sd in SEEDS:
            rng = np.random.default_rng([sd, zlib.crc32(sym.encode())])
            for (s, cell, _, day, side, _, _, _, fs, ft) in real:
                lo, hi = (DEV if day <= pd.Timestamp(DEV[1]) else VAL)
                cand = np.flatnonzero((dd * 86400 >= pd.Timestamp(lo).timestamp()) & (dd * 86400 <= pd.Timestamp(hi).timestamp()))
                i = int(rng.choice(cand))
                x = trade(D, dl, i, side, fs, ft, CELLS[cell])
                if x is None:
                    continue
                r = sim(D, *x[:1], side, *x[1:])
                if r is not None:
                    out.append((sym, cell, str(sd), pd.Timestamp(dl[i]["day"] * 86400, unit="s"), side, r[0], r[1], int(D["t"][x[0]]), fs, ft))
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
    cut = pd.Timestamp("2024-03-13 12:00").timestamp()
    bad = 0
    for s in ("EURUSD", "XAUUSD", "SP", "BTCUSD"):
        f = pd.DataFrame(market((s, END, False)), columns=COLS)
        p = pd.DataFrame(market((s, cut, False)), columns=COLS)
        f = f[(f.t_entry < cut - 7 * 86400)].reset_index(drop=True)   # CRT5 trades need up to 5 trading days after entry
        p = p[(p.t_entry < cut - 7 * 86400)].reset_index(drop=True)
        bad += int(not (len(f) == len(p) and np.allclose(f.R, p.R) and (f.side.values == p.side.values).all()))
    print("truncation test:", "PASS" if bad == 0 else f"FAIL {bad}")
    D = load("XAUUSD")
    dl = days_of(D)
    x = df[(df.mkt == "XAUUSD") & (df.cell == "CRT1")].iloc[50]
    j = [i for i, d in enumerate(dl) if d["day"] * 86400 == x.day.timestamp()][0]
    c2 = dl[j - 1]
    c1 = [d for d in dl[:j - 1] if d["n"] >= 300][-1]
    print(f"hand check XAUUSD {x.day.date()} side {x.side}: candle1 {pd.Timestamp(c1['day'] * 86400, unit='s').date()} L {c1['lo']:.2f} H {c1['hi']:.2f} | "
          f"candle2 {pd.Timestamp(c2['day'] * 86400, unit='s').date()} L {c2['lo']:.2f} H {c2['hi']:.2f} C {c2['cl']:.2f} | entry {pd.Timestamp(x.t_entry, unit='s')}")


def run():
    t0 = time.time()
    df = collect(END, True)
    print(f"run {time.time() - t0:.0f}s, {len(df)} trades", flush=True)
    df.to_parquet("D:/finance/si_ledgers/CRT_trades.parquet")
    rows = []
    for (cell, world), g in df.groupby(["cell", "world"]):
        r = dict(cell=cell, world=world)
        lag = 1 if cell == "CRT1" else 5
        for per, (a, b) in (("D", DEV), ("V", VAL)):
            x = g[(g.day >= a) & (g.day <= b)]
            r[f"n{per}"], r[f"m{per}"], r[f"g{per}"] = len(x), x.R.mean(), x.gR.mean()
            r[f"t{per}"] = nw_t(x.groupby("day").R.mean().to_numpy(), lag)
        for y in YEARS:
            r[f"y{y % 100}"] = g[g.day.dt.year == y].R.mean()
        rows.append(r)
    R = pd.DataFrame(rows)
    R.to_csv("D:/finance/si_ledgers/CRT_cells.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.round(3).to_string(index=False))
    plc = R[R.world != "real"]
    ceil = np.percentile(plc.tD, 95)
    print(f"\nplacebo (6 cells): max DEV t {plc.tD.max():.2f}, 95th pct {ceil:.2f}")
    for _, r in R[R.world == "real"].iterrows():
        dv = df[(df.cell == r.cell) & (df.world == "real") & (df.day <= DEV[1])]
        bym = dv.groupby("mkt").R.sum()
        conc = bym.max() / bym.sum() if bym.sum() > 0 else np.inf
        g = [r.mD >= 0.05 and r.tD >= 2.24, r.mV > 0 and r.tV >= 1.65, sum(r[f"y{y % 100}"] > 0 for y in YEARS) >= 3, r.tD > ceil, conc <= 0.40]
        print(f"{r.cell}: DEV n {r.nD} net {r.mD:+.3f}R (gross {r.gD:+.3f}) t {r.tD:+.2f} | VAL n {r.nV} net {r.mV:+.3f}R (gross {r.gV:+.3f}) t {r.tV:+.2f} | "
              f"years {r.y22:+.3f}/{r.y23:+.3f}/{r.y24:+.3f}/{r.y25:+.3f} | top market {conc:.2f} | gates {''.join('Y' if x else 'n' for x in g)} PASS {all(g)}")
        allr = df[(df.cell == r.cell) & (df.world == "real")]
        cls = allr.assign(c=allr.mkt.map(mclass), per=np.where(allr.day <= DEV[1], "DEV", "VAL")).groupby(["c", "per"]).agg(n=("R", "size"), R=("R", "mean"), gR=("gR", "mean"), win=("R", lambda v: (v > 0).mean()))
        print(cls.round(3).to_string())
        gold = allr[allr.mkt == "XAUUSD"]
        print(f"   XAUUSD: DEV n {len(gold[gold.day <= DEV[1]])} net {gold[gold.day <= DEV[1]].R.mean():+.3f} | VAL n {len(gold[gold.day > DEV[1]])} net {gold[gold.day > DEV[1]].R.mean():+.3f}")


if __name__ == "__main__":
    dry() if "--dry" in sys.argv else run()
