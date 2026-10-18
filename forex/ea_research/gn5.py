"""GN5: out-of-time check of GN3's O1 (Nasdaq overnight-range breakout) on 2020-21 Databento NQ futures with the MT5 broker cost model.
Pre-registration: forex/ea_research/PREREG_GN5.md.   python -m forex.ea_research.gn5 --dry-run | --run"""
import argparse, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts
from forex.ea_research.orbx import ct
from forex.ea_research.gn1 import NCTRL
from forex.ea_research.gn2 import info

NYZ = "America/New_York"
SPREAD = 1.67                                   # MT5 NSDQ median spread 2022-26, points
FUT = "futures/data/databento/futures_NQ.F_1m.parquet"


def load_fut(path=FUT, spread=SPREAD):
    """Databento 1-min trade bars -> the MT5 broker engine's dict: server-clock (Athens) epoch, bid = trade price, ask = bid + spread"""
    d = pd.read_parquet(path, columns=["ts", "open", "high", "low", "close"]).sort_values("ts")
    srv = d.ts.dt.tz_convert("Europe/Athens").dt.tz_localize(None)
    t = ((srv - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy().astype(np.int64)
    keep = np.r_[True, t[1:] > t[:-1]]
    D = {"t": t[keep]}
    for k, c in zip("ohlc", ("open", "high", "low", "close")):
        v = d[c].to_numpy()[keep].astype(float); D["b" + k] = v; D["a" + k] = v + spread
    D["sp"] = np.full(len(D["t"]), spread); sod = D["t"] % 86400
    D["roll"] = (sod >= 23 * 3600) | (sod < 3600); D["sod"] = sod
    return D


def roll_mondays(y0=2019, y1=2027):
    out = set()
    for y in range(y0, y1):
        for m in (3, 6, 9, 12):
            f = pd.Timestamp(y, m, 1); f += pd.Timedelta(days=(4 - f.weekday()) % 7 + 14)      # third Friday
            out.add((f - pd.Timedelta(days=4)).normalize())
    return out


def o1(D, start, end_day, skip=frozenset(), trial="O1"):
    """GN3 O1 copied from gn3.trades, with a date range and a skip set"""
    t = D["t"]; n = len(t); end = int(t[-1]) + 60
    rng = np.random.default_rng(sum(map(ord, trial)) * 104729)
    out, ctrl = [], []
    for d in pd.bdate_range(start, end_day):
        if d in skip:
            continue
        p = d - pd.Timedelta(days=1)
        s0 = ts(p.year, p.month, p.day, 18, 0, NYZ)
        s1, e1, xe = (ts(d.year, d.month, d.day, *hm, NYZ) for hm in ((9, 30), (12, 0), (15, 55)))
        if xe > end:
            continue
        i0, i1, iw, ix = (int(v) for v in np.searchsorted(t, [s0, s1, e1, xe]))
        if i1 - i0 < 0.8 * (s1 - s0) / 60 or iw - i1 < 30 or ix >= n or ix <= i1 + 1:
            continue
        hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); W = hi - lo
        if W <= 0:
            continue
        dist = W / 2
        nr = ~D["roll"][i1:iw]
        kl = np.flatnonzero((D["ah"][i1:iw] >= hi) & nr); ks = np.flatnonzero((D["bl"][i1:iw] <= lo) & nr)
        kl = int(kl[0]) if len(kl) else 1 << 40; ks = int(ks[0]) if len(ks) else 1 << 40
        if kl != ks and min(kl, ks) < 1 << 40:
            side = 1 if kl < ks else -1; k = i1 + min(kl, ks)
            e = max(hi, D["ao"][k]) if side == 1 else min(lo, D["bo"][k]); st = (hi + lo) / 2
            if k < ix - 1 and side * (e - st) > 0:
                ex, _ = walk(D, side, k, ix, st, None)
                out.append(dict(trial=trial, day=d, side=side, t_entry=int(t[k]), entry=e, stop=st, R=side * (ex - e) / abs(e - st), W=W))
        cand = np.flatnonzero(nr)
        for j in rng.choice(cand, size=min(NCTRL, len(cand)), replace=False):
            k = i1 + int(j); side = int(rng.choice([1, -1]))
            e = D["ao"][k] if side == 1 else D["bo"][k]
            if k < ix - 1:
                ex, _ = walk(D, side, k, ix, e - side * dist, None)
                ctrl.append(dict(trial=trial, day=d, R=side * (ex - e) / dist))
    return pd.DataFrame(out), pd.DataFrame(ctrl)


def checks():
    from forex.ea_research.gn3 import trades as gn3_trades
    E = load("NSDQ")
    T3, C3, _ = gn3_trades("O1", D=E); T5, C5 = o1(E, "2022-01-03", "2026-10-16")
    cols = ["day", "side", "t_entry", "entry", "stop", "R"]
    print(f"identity vs gn3 O1 on MT5: trades {len(T3)} vs {len(T5)} identical {T3[cols].equals(T5[cols])}; controls identical {C3.R.round(12).equals(C5.R.round(12))}")
    F = load_fut(); sk = roll_mondays()
    TF, _ = o1(F, "2022-01-03", "2024-12-31", sk); TE = T3[(T3.day >= "2022-01-01") & (T3.day < "2025-01-01")]
    m = TE.merge(TF, on="day", suffixes=("_mt5", "_fut"))
    print(f"port check 2022-24: MT5 broker n {len(TE)} {TE.R.mean():+.3f} R | futures n {len(TF)} {TF.R.mean():+.3f} R (diff {TF.R.mean() - TE.R.mean():+.3f}, bar +/-0.06)"
          f" | common days {len(m)}, same side {np.mean(m.side_mt5 == m.side_fut):.0%}, R correlation {np.corrcoef(m.R_mt5, m.R_fut)[0, 1]:.2f} (bar >= 0.6)")
    return F, sk


def dry_run():
    F, sk = checks()
    T, C = o1(F, "2020-01-02", "2021-12-31", sk)
    print(f"OOT counts (no P&L): trades 2020 {(T.day.dt.year == 2020).sum()} 2021 {(T.day.dt.year == 2021).sum()} | roll Mondays skipped "
          f"{sum(1 for x in sk if pd.Timestamp('2020-01-01') <= x < pd.Timestamp('2022-01-01'))} | control draws {len(C)}")
    for _, r in T.sample(2, random_state=8).iterrows():
        loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens").tz_convert(NYZ)
        print(f"   hand check {r.day.date()} side {r.side:+d} entry {r.entry:.2f} at {loc:%H:%M} NY, stop {r.stop:.2f} (range {r.W:.1f} points)")


def run():
    F, sk = checks()
    T, C = o1(F, "2020-01-02", "2021-12-31", sk)
    m, tt = ct(T); i_, ti = info(T, C); yr = T.groupby(T.day.dt.year).R.agg(["mean", "size"])
    ok = m > 0 and tt >= 1.65 and (yr["mean"] > 0).all()
    print(f"OOT 2020-21 O1 on NQ futures (MT5 broker cost): n {len(T)} {m:+.3f} R (t {tt:+.2f}) win {(T.R > 0).mean():.0%} | control {C.groupby('day').R.mean().mean():+.3f}"
          f" info {i_:+.3f} (t {ti:+.2f}) | " + " ".join(f"{y}: {r['mean']:+.3f} ({int(r['size'])})" for y, r in yr.iterrows())
          + f" | longs {T[T.side == 1].R.mean():+.3f} shorts {T[T.side == -1].R.mean():+.3f} -> {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
