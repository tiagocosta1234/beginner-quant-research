"""UTBOT exactly as in PREREG_UTBOT.md.  python -m forex.ea_research.utbot [--dry] [--hold] [--jobs N]"""
import sys, os, glob, time
import numpy as np
import pandas as pd
from multiprocessing import Pool

HOLD = "--hold" in sys.argv
DRY = "--dry" in sys.argv
JOBS = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 8
DATA = "forex/data_mt5/"
END_T = int(pd.Timestamp("2026-10-03" if HOLD else "2026-01-01").timestamp())
TFS = {"M1": 60, "M3": 180, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H2": 7200, "H4": 14400}
KEY, ATRP = 1.0, 10
VARIANTS = ({"k2": (2.0, False), "k3": (3.0, False), "ha": (1.0, True)} if "--variants" in sys.argv else {"base": (1.0, False)})
PER = {"DEV": (pd.Timestamp("2021-12-01").timestamp(), pd.Timestamp("2024-01-01").timestamp()),
       "VAL": (pd.Timestamp("2024-01-01").timestamp(), pd.Timestamp("2026-01-01").timestamp()),
       "HOLD": (pd.Timestamp("2026-01-01").timestamp(), pd.Timestamp("2026-10-03").timestamp())}


def bars(m1: pd.DataFrame, step: int) -> pd.DataFrame:
    g = m1.groupby((m1.t // step) * step, sort=True)
    b = pd.DataFrame({"bo": g.bo.first(), "ao": g.ao.first(), "mo": g.mo.first(), "mh": g.mh.max(), "ml": g.ml.min(), "mc": g.mc.last()})
    b.index.name = "t"
    return b.reset_index()


def trailing(src: np.ndarray, nloss: np.ndarray):
    n = len(src)
    ts = np.zeros(n)
    prev_ts, prev_src = 0.0, 0.0
    s, nl, out = src.tolist(), nloss.tolist(), [0.0] * n
    for i in range(n):
        c = s[i]
        nlo = nl[i]
        if c > prev_ts and prev_src > prev_ts:
            v = max(prev_ts, c - nlo)
        elif c < prev_ts and prev_src < prev_ts:
            v = min(prev_ts, c + nlo)
        elif c > prev_ts:
            v = c - nlo
        else:
            v = c + nlo
        out[i] = v
        prev_ts, prev_src = v, c
    return np.array(out)


def signals(b: pd.DataFrame, key=KEY, ha=False):
    src = ((b.mo + b.mh + b.ml + b.mc) / 4).to_numpy() if ha else b.mc.to_numpy()
    cl = b.mc.to_numpy()
    cp = np.r_[cl[0], cl[:-1]]                      # true range always from the regular candles
    tr = np.maximum.reduce([b.mh.to_numpy() - b.ml.to_numpy(), np.abs(b.mh.to_numpy() - cp), np.abs(b.ml.to_numpy() - cp)])
    atr = pd.Series(tr).ewm(alpha=1.0 / ATRP, adjust=False).mean().to_numpy()
    ts = trailing(src, key * atr)
    s1, t1 = np.r_[src[0], src[:-1]], np.r_[0.0, ts[:-1]]
    buy = (src > ts) & (s1 <= t1)
    sell = (src < ts) & (t1 <= s1) & (ts > src)
    sg = np.zeros(len(src), np.int8)
    sg[buy] = 1
    sg[sell & ~buy] = -1
    sg[:ATRP * 5] = 0            # ATR warm-up
    return sg


def allowed_next(t):
    """index of the first bar at or after j whose open is not in server hours 23/0 (vectorised)."""
    ok = ~np.isin((t // 3600) % 24, (23, 0))
    big = len(t)
    cand = np.where(ok, np.arange(len(t)), big)
    nxt = np.minimum.accumulate(cand[::-1])[::-1]
    return np.r_[nxt, big]


def trades_from(sg, t, bo, ao, nxt, shift=0):
    """stop-and-reverse fills at the first allowed bar open after each signal; returns arrays (exit_time, side, ret_bp)."""
    if shift:
        sg = np.roll(sg, shift)
    idx = np.nonzero(sg)[0]
    empty = (np.array([]), np.array([]), np.array([]))
    if len(idx) == 0:
        return empty
    ex = nxt[np.minimum(idx + 1, len(t))]
    sd = sg[idx]
    keep = ex < len(t)
    ex, sd = ex[keep], sd[keep]
    if len(ex) == 0:
        return empty
    last = np.r_[ex[1:] != ex[:-1], True]            # the later signal for the same exec bar wins
    e, s = ex[last], sd[last]
    chg = np.r_[True, s[1:] != s[:-1]]
    e, s = e[chg], s[chg]
    if len(e) < 2:
        return empty
    ent = np.where(s[:-1] > 0, ao[e[:-1]], bo[e[:-1]])
    ext = np.where(s[:-1] > 0, bo[e[1:]], ao[e[1:]])
    ret = np.where(s[:-1] > 0, ext / ent - 1, ent / ext - 1) * 1e4
    return t[e[1:]], s[:-1], ret


def stats(tx, ret, lo, hi):
    m = (tx >= lo) & (tx < hi)
    r = ret[m]
    n = len(r)
    if n < 3 or r.std() == 0:
        return n, np.nan, np.nan, np.nan
    return n, r.mean(), r.mean() / (r.std(ddof=1) / np.sqrt(n)), (r > 0).mean()


def one_cell(sym, tf, var, step, sg, t, bo, ao, nxt, rng):
    tx, sd, ret = trades_from(sg, t, bo, ao, nxt)
    row = dict(sym=sym, tf=tf, var=var, bars=len(t), signals=int((sg != 0).sum()))
    for p in ("DEV", "VAL") + (("HOLD",) if HOLD else ()):
        n, mu, tt, hit = stats(tx, ret, *PER[p])
        row.update({f"n_{p}": n, f"mu_{p}": mu, f"t_{p}": tt, f"hit_{p}": hit})
    i0 = np.searchsorted(t, PER["DEV"][0]); i1 = np.searchsorted(t, PER["VAL"][0]); i2 = np.searchsorted(t, PER["VAL"][1])
    row["bh_DEV_bp"] = (bo[max(i1 - 1, 0)] / ao[i0] - 1) * 1e4
    row["bh_VAL_bp"] = (bo[min(i2, len(t)) - 1] / ao[i1] - 1) * 1e4
    row["tot_DEV_bp"] = ret[(tx >= PER["DEV"][0]) & (tx < PER["DEV"][1])].sum()
    row["tot_VAL_bp"] = ret[(tx >= PER["VAL"][0]) & (tx < PER["VAL"][1])].sum()
    pl = []
    for _ in range(100):
        sh = int(rng.integers(5 * 86400 // step, max(len(t) - 5 * 86400 // step, 5 * 86400 // step + 1)))
        tx2, sd2, ret2 = trades_from(sg, t, bo, ao, nxt, shift=sh)
        n, mu, tt, hit = stats(tx2, ret2, *PER["DEV"])
        pl.append(tt if n >= 100 and tt == tt else np.nan)
    return row, pl


def one_symbol(path):
    sym = os.path.basename(path).replace("_M1_rates.parquet", "")
    d = pd.read_parquet(path, columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t").drop_duplicates("t")
    d = d[(d.t < END_T) & (d.bo > 0) & (d.ao >= d.bo)]
    m1 = pd.DataFrame({"t": d.t.to_numpy(), "bo": d.bo.to_numpy(), "ao": d.ao.to_numpy(), "mo": ((d.bo + d.ao) / 2).to_numpy(), "mh": ((d.bh + d.ah) / 2).to_numpy(), "ml": ((d.bl + d.al) / 2).to_numpy(), "mc": ((d.bc + d.ac) / 2).to_numpy()})
    rng = np.random.default_rng(abs(hash(sym)) % (2 ** 32))
    rows, plc = [], {}
    for tf, step in TFS.items():
        b = bars(m1, step)
        if len(b) < 500:
            continue
        t, bo, ao = b.t.to_numpy(), b.bo.to_numpy(), b.ao.to_numpy()
        nxt = allowed_next(t)
        for var, (key, ha) in VARIANTS.items():
            sg = signals(b, key, ha)
            rows_, plc_ = one_cell(sym, tf, var, step, sg, t, bo, ao, nxt, rng)
            rows.append(rows_)
            plc[(sym, tf, var)] = plc_
    return rows, plc


if __name__ == "__main__":
    files = sorted(f for f in glob.glob(DATA + "*_M1_rates.parquet"))
    if DRY:
        sym = "EURUSD"
        d = pd.read_parquet(DATA + f"{sym}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t")
        d = d[d.t < END_T]
        m1 = pd.DataFrame({"t": d.t.to_numpy(), "bo": d.bo.to_numpy(), "ao": d.ao.to_numpy(), "mo": ((d.bo + d.ao) / 2).to_numpy(), "mh": ((d.bh + d.ah) / 2).to_numpy(), "ml": ((d.bl + d.al) / 2).to_numpy(), "mc": ((d.bc + d.ac) / 2).to_numpy()})
        b = bars(m1, 3600)
        sg = signals(b)
        print("EURUSD H1 bars", len(b), "signals", int((sg != 0).sum()), "buys", int((sg > 0).sum()), "sells", int((sg < 0).sum()))
        t0 = time.time()
        tt_ = b.t.to_numpy()
        tx, sd, ret = trades_from(sg, tt_, b.bo.to_numpy(), b.ao.to_numpy(), allowed_next(tt_))
        print("trades", len(ret), "mean bp %.3f" % ret.mean(), "first trades:", [(str(pd.Timestamp(x, unit='s')), int(s), round(float(r), 1)) for x, s, r in zip(tx[:4], sd[:4], ret[:4])], "| exec secs %.2f" % (time.time() - t0))
        idx = np.nonzero(sg)[0][:3]
        for i in idx:
            print("signal", int(sg[i]), "at bar", pd.Timestamp(b.t.iloc[i], unit="s"), "close %.5f" % b.mc.iloc[i], "-> next bar open", pd.Timestamp(b.t.iloc[i + 1], unit="s"))
        sys.exit()
    t0 = time.time()
    with Pool(JOBS) as pool:
        res = pool.map(one_symbol, files)
    rows = [r for rr, _ in res for r in rr]
    plc = {}
    for _, p in res:
        plc.update(p)
    R = pd.DataFrame(rows)
    R.to_csv("data/tmp/utbot_variant_cells.csv" if "--variants" in sys.argv else "data/tmp/utbot_cells.csv", index=False)
    pm = np.array([[x for x in v] for v in plc.values()], dtype=float)
    mx = np.nanmax(pm, axis=0)
    ceil = np.nanpercentile(mx, 95)
    R["cand"] = (R.mu_DEV > 0) & (R.t_DEV >= (4.1 if "--variants" in sys.argv else 3.8)) & (R.n_DEV >= 100) & (R.mu_VAL > 0) & (R.t_VAL >= 1.65) & (R.n_VAL >= 50) & (R.t_DEV > ceil)
    print(f"cells {len(R)} | placebo max-t over all cells: median {np.nanmedian(mx):.2f}, 95th {ceil:.2f} | secs {time.time() - t0:.0f}")
    print("share of cells with positive net: DEV %.1f%%, VAL %.1f%%, both %.1f%%" % ((R.mu_DEV > 0).mean() * 100, (R.mu_VAL > 0).mean() * 100, ((R.mu_DEV > 0) & (R.mu_VAL > 0)).mean() * 100))
    print("median net bp per trade by variant (DEV / VAL):", R.groupby("var")[["mu_DEV", "mu_VAL"]].median().round(2).to_dict("index"))
    print("share positive in both by variant:", R.assign(b=(R.mu_DEV > 0) & (R.mu_VAL > 0)).groupby("var").b.mean().round(3).to_dict())
    print("median net bp per trade by timeframe (DEV / VAL):")
    print(R.groupby("tf")[["mu_DEV", "mu_VAL"]].median().round(2).T.to_string())
    print("median trades per cell by timeframe (DEV):", R.groupby("tf").n_DEV.median().round(0).to_dict())
    top = R.sort_values("t_DEV", ascending=False).head(10)
    print("TOP 10 by DEV t:\n", top[["sym", "tf", "var", "n_DEV", "mu_DEV", "t_DEV", "n_VAL", "mu_VAL", "t_VAL"]].round(2).to_string(index=False))
    print("CANDIDATES (all gates):", R[R.cand][["sym", "tf", "var", "mu_DEV", "t_DEV", "mu_VAL", "t_VAL"]].round(2).to_dict("records"))
    both = R[(R.mu_DEV > 0) & (R.mu_VAL > 0)].sort_values("t_VAL", ascending=False).head(10)
    print("Positive in both, top 10 by VAL t:\n", both[["sym", "tf", "var", "n_DEV", "mu_DEV", "t_DEV", "n_VAL", "mu_VAL", "t_VAL"]].round(2).to_string(index=False))
