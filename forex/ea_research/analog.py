"""ANALOG exactly as in PREREG_ANALOG.md (chart pattern memory pooled over every MT5 broker market).
   python -m forex.ea_research.analog --dry     counts, truncation test, library causality, hand check (no P&L)
   python -m forex.ea_research.analog           real run + placebo worlds 91-93"""
import glob
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

DRY = "--dry" in sys.argv
END = pd.Timestamp("2026-01-01").timestamp()          # 2026 sealed: nothing at or after this is loaded
DEC_H = (9, 13, 17)
WS, HS, K = (12, 48), (4, 22), 50
LONG_V, SHORT_V = 0.60, 0.40
DEV = ("2022-07-01", "2024-12-31")
VAL = ("2025-01-01", "2025-12-31")
YEARS = (("2022H2", "2022-07-01", "2022-12-31"), ("2023", "2023-01-01", "2023-12-31"),
         ("2024", "2024-01-01", "2024-12-31"), ("2025", "2025-01-01", "2025-12-31"))
OUT = Path("D:/finance/si_ledgers")
SYMS = sorted(Path(p).name.replace("_M1_rates.parquet", "") for p in glob.glob("forex/data_mt5/*_M1_rates.parquet"))


def mclass(s):
    if s in ("XAUUSD", "XAGUSD"):
        return "metal"
    if s in ("BRENT", "WTI"):
        return "energy"
    if s in ("ASX", "DAX", "DOW", "NIKKEI", "NSDQ", "SP"):
        return "index"
    if s in ("ADAUSD", "BCHUSD", "BNBUSD", "BTCUSD", "ETHUSD", "LTCUSD", "SOLUSD", "XRPUSD"):
        return "crypto"
    return "fx"


def build(sym, end=END):
    """decision-mark rows of one market: shapes, labels, trade outcomes (all causal except the label/outcome)."""
    d = pd.read_parquet(f"forex/data_mt5/{sym}_M1_rates.parquet", columns=["t", "bo", "ao"])
    d = d[(d.t < end) & (d.bo > 0) & (d.ao >= d.bo)].drop_duplicates("t").sort_values("t")
    hr_all = (d.t // 3600) % 24
    m = d[((d.t % 3600) == 300) & ~hr_all.isin([23, 0])]
    t, bo, ao = m.t.to_numpy(), m.bo.to_numpy(), m.ao.to_numpy()
    lm = np.log((bo + ao) / 2)
    r = np.diff(lm, prepend=np.nan)
    vol = pd.Series(r).rolling(240, min_periods=120).std().to_numpy()
    hour = (t // 3600) % 24
    rows = np.flatnonzero(np.isin(hour, DEC_H) & np.isfinite(vol) & (vol > 0))
    o = {"mkt": np.full(len(rows), sym), "t": t[rows], "vol": vol[rows], "ask_in": ao[rows], "bid_in": bo[rows]}
    for W in WS:
        S = np.full((len(rows), W), np.nan, np.float32)
        ok = rows - W + 1 >= 1
        idx = rows[ok, None] + np.arange(-W + 1, 1)[None, :]
        S[ok] = r[idx] / vol[rows[ok], None]
        o[f"S{W}"] = S
    for H in HS:
        j = rows + H
        okj = j < len(t)
        jj = np.where(okj, j, 0)
        o[f"lab{H}"] = np.where(okj, (lm[jj] - lm[rows]) / vol[rows], np.nan)
        o[f"exit{H}"] = np.where(okj, t[jj], np.iinfo(np.int64).max)
        o[f"nl{H}"] = np.where(okj, np.log(bo[jj] / ao[rows]), np.nan)   # long: buy ask, sell bid
        o[f"ns{H}"] = np.where(okj, np.log(bo[rows] / ao[jj]), np.nan)   # short: sell bid, buy ask
    return o


def table():
    parts = [build(s) for s in SYMS]
    T = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    return T


def neighbours(T, W, H):
    """for every query row (month >= 2022-07): indices of its K nearest library rows (labels complete before the month)."""
    S = T[f"S{W}"]
    lab, ex = T[f"lab{H}"], T[f"exit{H}"]
    shp_ok = np.isfinite(S).all(1)
    lib_ok = shp_ok & np.isfinite(lab)
    q_ok = shp_ok & np.isfinite(T[f"nl{H}"])
    months = pd.date_range("2022-07-01", "2025-12-01", freq="MS")
    qi_all, nb_all = [], []
    worst = -np.inf
    for ms in months:
        a, b = ms.timestamp(), (ms + pd.offsets.MonthBegin(1)).timestamp()
        lib = np.flatnonzero(lib_ok & (ex < a))
        qi = np.flatnonzero(q_ok & (T["t"] >= a) & (T["t"] < b))
        if len(qi) == 0 or len(lib) < K:
            continue
        worst = max(worst, ex[lib].max() - a)
        L = S[lib]
        L2 = (L * L).sum(1)
        for c in range(0, len(qi), 512):
            Q = S[qi[c:c + 512]]
            d2 = (Q * Q).sum(1)[:, None] + L2[None, :] - 2 * Q @ L.T
            nb = np.argpartition(d2, K, axis=1)[:, :K]
            nb_all.append(lib[nb].astype(np.int32))
        qi_all.append(qi)
    assert worst < 0, "library causality violated"
    return np.concatenate(qi_all), np.concatenate(nb_all)


def nw_t(x, lag=2):
    x = np.asarray(x, float)
    n = len(x)
    if n < 10:
        return 0.0
    e = x - x.mean()
    s = e @ e / n
    for l in range(1, lag + 1):
        s += 2 * (1 - l / (lag + 1)) * (e[l:] @ e[:-l]) / n
    return x.mean() / np.sqrt(s / n)


def trades(T, H, qi, nb, labels):
    vote = (labels[nb] > 0).mean(1)
    side = np.where(vote >= LONG_V, 1, np.where(vote <= SHORT_V, -1, 0))
    k = side != 0
    q = qi[k]
    s = side[k]
    net = np.where(s > 0, T[f"nl{H}"][q], T[f"ns{H}"][q])
    return pd.DataFrame({"mkt": T["mkt"][q], "day": pd.to_datetime(T["t"][q], unit="s").normalize(), "side": s,
                         "vote": vote[k], "sig": net / (T["vol"][q] * np.sqrt(H)), "bp": net * 1e4})


def stats(df, a, b):
    x = df[(df.day >= a) & (df.day <= b)]
    daily = x.groupby("day").sig.mean()
    return len(x), x.sig.mean(), nw_t(daily.to_numpy()), x.bp.mean()


def dry():
    T = table()
    print(f"{len(SYMS)} markets; decision rows {len(T['t'])}; first {pd.Timestamp(T['t'].min(), unit='s')} last {pd.Timestamp(T['t'].max(), unit='s')}")
    for W in WS:
        for H in HS:
            ok = np.isfinite(T[f"S{W}"]).all(1) & np.isfinite(T[f"nl{H}"])
            day = pd.to_datetime(T["t"][ok], unit="s")
            print(f"W{W} H{H}: queries DEV {((day >= DEV[0]) & (day <= DEV[1] + ' 23:59')).sum()} VAL {((day >= VAL[0]) & (day <= VAL[1] + ' 23:59')).sum()}")
    cut = pd.Timestamp("2024-03-13 11:00").timestamp()
    bad = 0
    for s in ("EURUSD", "XAUUSD", "SP", "BTCUSD"):
        full, part = build(s), build(s, end=cut)
        n = len(part["t"])
        same_t = np.array_equal(full["t"][:n], part["t"])
        for W in WS:
            a, b = full[f"S{W}"][:n], part[f"S{W}"]
            bad += int(not (same_t and np.allclose(np.nan_to_num(a, nan=9e9), np.nan_to_num(b, nan=9e9)) and np.allclose(full["vol"][:n], part["vol"])))
    print("truncation test (shapes and vol before a cut unchanged):", "PASS" if bad == 0 else f"FAIL {bad}")
    i = np.flatnonzero(T["mkt"] == "EURUSD")[2000]
    ts = T["t"][i]
    raw = pd.read_parquet("forex/data_mt5/EURUSD_M1_rates.parquet")
    print("hand check EURUSD mark", pd.Timestamp(ts, unit="s"), "bid/ask", T["bid_in"][i], T["ask_in"][i], "| raw M1 row:", raw[raw.t == ts][["bo", "ao"]].to_numpy().tolist())
    t0 = time.time()
    qi, nb = neighbours(T, 12, 4)
    print(f"neighbour search W12 H4: {len(qi)} queries, causality assert passed, {time.time() - t0:.0f}s")


def run():
    T = table()
    rng_seeds = (91, 92, 93)
    perms = {}
    for sd in rng_seeds:
        rng = np.random.default_rng(sd)
        perms[sd] = {}
        for H in HS:
            lab = T[f"lab{H}"].copy()
            for s in SYMS:
                ix = np.flatnonzero((T["mkt"] == s) & np.isfinite(lab))
                lab[ix] = lab[rng.permutation(ix)]
            perms[sd][H] = lab
    rows, keep = [], {}
    for W in WS:
        for H in HS:
            t0 = time.time()
            qi, nb = neighbours(T, W, H)
            for world in ("real",) + rng_seeds:
                lab = T[f"lab{H}"] if world == "real" else perms[world][H]
                df = trades(T, H, qi, nb, lab)
                nD, mD, tD, bD = stats(df, *DEV)
                nV, mV, tV, bV = stats(df, *VAL)
                yrs = [stats(df, a, b)[1] for _, a, b in YEARS]
                rows.append(dict(cell=f"W{W}-H{H}", world=world, nD=nD, mD=mD, tD=tD, bpD=bD, nV=nV, mV=mV, tV=tV, bpV=bV,
                                 y22=yrs[0], y23=yrs[1], y24=yrs[2], y25=yrs[3]))
                if world == "real":
                    keep[f"W{W}-H{H}"] = df
            print(f"W{W} H{H} done {time.time() - t0:.0f}s", flush=True)
    R = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    R.to_csv(OUT / "ANALOG_cells.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.round(3).to_string(index=False))
    plc = R[R.world != "real"]
    ceil = np.percentile(np.abs(plc.tD), 95)
    print(f"\nplacebo (12 cells): max |DEV t| {np.abs(plc.tD).max():.2f}, 95th pct {ceil:.2f}")
    for _, r in R[R.world == "real"].iterrows():
        df = keep[r.cell]
        dv = df[(df.day >= DEV[0]) & (df.day <= DEV[1])]
        sg = np.sign(r.tD)
        by_m = dv.groupby("mkt").sig.sum() * sg
        conc = by_m.max() / by_m.sum() if by_m.sum() > 0 else np.inf
        g = [abs(r.tD) >= 2.50 and r.mD * sg >= 0.02, np.sign(r.tV) == sg and abs(r.tV) >= 1.65,
             sum(np.sign([r.y22, r.y23, r.y24, r.y25]) == sg) >= 3, abs(r.tD) > ceil, conc <= 0.40]
        print(f"{r.cell}: DEV n {r.nD} {r.mD:+.4f} sig/trade ({r.bpD:+.2f} bp) t {r.tD:+.2f} | VAL n {r.nV} {r.mV:+.4f} ({r.bpV:+.2f} bp) t {r.tV:+.2f} | "
              f"years {r.y22:+.3f}/{r.y23:+.3f}/{r.y24:+.3f}/{r.y25:+.3f} | top-market share {conc:.2f} | gates {''.join('Y' if x else 'n' for x in g)} PASS {all(g)}")
        cls = dv.assign(c=dv.mkt.map(mclass)).groupby("c").agg(n=("sig", "size"), sig=("sig", "mean"), bp=("bp", "mean"))
        lsd = dv.groupby("side").agg(n=("sig", "size"), sig=("sig", "mean"), bp=("bp", "mean"))
        strong = dv[(dv.vote >= 0.7) | (dv.vote <= 0.3)]
        print("   DEV by class:", "; ".join(f"{c} n{int(x.n)} {x.sig:+.3f} ({x.bp:+.1f}bp)" for c, x in cls.iterrows()),
              "| long/short:", "; ".join(f"{int(s):+d} n{int(x.n)} {x.sig:+.3f}" for s, x in lsd.iterrows()),
              f"| strong votes n{len(strong)} {strong.sig.mean():+.3f}")


if __name__ == "__main__":
    dry() if DRY else run()
