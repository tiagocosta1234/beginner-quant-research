"""GN13: one-sided session breakout in the direction of the 10-year Treasury trend (ZN close of the day before vs its 20-day mean;
bonds up = yields falling = long), B1 NSDQ / B2 SP (09:30 box, exit 15:55) and B3 XAUUSD (08:20 COMEX box, exit 13:25).
MT5 DEV 2022-24 / VAL 2025 / HOLD 2026, CME futures 2020-21 out of time. Pre-registration: forex/ea_research/PREREG_GN13.md.
   python -m forex.ea_research.gn13 --dry-run | --run"""
import argparse, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts
from forex.ea_research.orbx import ct
from forex.ea_research.gn2 import info
from forex.ea_research.gn5 import load_fut, roll_mondays
from forex.ea_research.gn6 import mt5_spread, bad_minutes

NYZ = "America/New_York"
FUTP = "futures/data/databento/futures_{}.F_1m.parquet"
ZNP = "futures/data/daily/ZN=F_yahoo_daily.csv"
# trial: MT5 broker market, futures root, box start, window start, window end, exit, minimum window minutes
TRIALS = {"B1": ("NSDQ", "NQ", (9, 30), (10, 0), (12, 0), (15, 55), 90),
          "B2": ("SP", "ES", (9, 30), (10, 0), (12, 0), (15, 55), 90),
          "B3": ("XAUUSD", "GC", (8, 20), (8, 50), (11, 0), (13, 25), 100)}
TBAR, NCT = 2.13, 5
DEV, VAL, HOLD = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-09-23")
OOT = ("2020-01-02", "2021-12-31")
mt5_SPAN = ("2022-01-03", "2026-09-22")
ES_SWITCH_FRI = frozenset(pd.Timestamp(x) for x in ("2020-03-13", "2020-06-12", "2020-09-11", "2020-12-11", "2021-03-12", "2021-06-11", "2021-09-10", "2021-12-10"))
BIG = 1 << 40


def bond_sides(cut=None):
    """day -> +1 (ZN close of the last trading day before d above its 20-day mean) / -1, as a lookup function"""
    z = pd.read_csv(ZNP, parse_dates=["date"]).set_index("date").close.dropna().sort_index()
    if cut is not None:
        z = z[z.index < pd.Timestamp(cut)]
    side = np.where(z > z.rolling(20, min_periods=20).mean(), 1, -1).astype(float)
    side[np.isnan(z.rolling(20, min_periods=20).mean().to_numpy())] = np.nan
    s = pd.Series(side, index=z.index)

    def f(d):
        i = int(s.index.searchsorted(d)) - 1
        return s.iloc[i] if i >= 0 and (d - s.index[i]).days <= 7 else np.nan
    return f


def first(mask):
    k = np.flatnonzero(mask)
    return int(k[0]) if len(k) else BIG


def one_sided(D, side, hi, lo, i1, iw, ix, nr):
    """stop order on one side only: the trade R or None"""
    if side == 1:
        k = first((D["ah"][i1:iw] >= hi) & nr)
        if k == BIG:
            return None
        k += i1; e = max(hi, D["ao"][k]); st = lo
    else:
        k = first((D["bl"][i1:iw] <= lo) & nr)
        if k == BIG:
            return None
        k += i1; e = min(lo, D["bo"][k]); st = hi
    if side * (e - st) <= 0:
        return None
    ex, _ = walk(D, side, k, ix, st, None)
    return k, e, st, side * (ex - e) / abs(e - st)


def trades(D, tr, start, end_day, bside, skip=frozenset(), bad=None, seed=0):
    mkt, root, b0, b1, w1, xh, minw = TRIALS[tr]
    t = D["t"]; n = len(t); rng = np.random.default_rng(seed)
    A, M, C = [], [], []
    for d in pd.bdate_range(start, end_day):
        bs = bside(d)
        if d in skip or not np.isfinite(bs):
            continue
        bs = int(bs)
        s0, s1, e1, xe = (ts(d.year, d.month, d.day, *hm, NYZ) for hm in (b0, b1, w1, xh))
        i0, i1, iw, ix = (int(x) for x in np.searchsorted(t, [s0, s1, e1, xe]))
        if i1 - i0 < 24 or iw - i1 < minw or ix >= n or ix <= iw or t[ix] - xe > 600:
            continue
        if bad is not None and len(bad) and np.searchsorted(bad, s0) < np.searchsorted(bad, xe + 60):
            continue
        hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); W = hi - lo
        if W <= 0:
            continue
        nr = ~D["roll"][i1:iw]; base = dict(day=d, bond=bs, W=W)
        a = one_sided(D, bs, hi, lo, i1, iw, ix, nr)
        if a:
            A.append(dict(base, side=bs, t_entry=int(t[a[0]]), entry=a[1], stop=a[2], R=a[3]))
        m = one_sided(D, -bs, hi, lo, i1, iw, ix, nr)
        if m:
            M.append(dict(base, side=-bs, R=m[3]))
        cand = np.flatnonzero(nr)
        for j in rng.choice(cand, size=min(NCT, len(cand)), replace=False):
            k = i1 + int(j); e = D["ao"][k] if bs == 1 else D["bo"][k]
            ex, _ = walk(D, bs, k, ix, e - bs * W, None); C.append(dict(base, R=bs * (ex - e) / W))
    return pd.DataFrame(A), pd.DataFrame(M), pd.DataFrame(C)


def per(x, p):
    return x[(x.day >= p[0]) & (x.day < p[1])]


def seed_of(s):
    return sum(map(ord, s)) * 40503 % (1 << 32)


def fut_data(tr, E):
    mkt, root, b0, b1, w1, xh, minw = TRIALS[tr]
    F = load_fut(FUTP.format(root), mt5_spread(E, b0, xh))
    skip = roll_mondays() | (ES_SWITCH_FRI if root == "ES" else frozenset()) if root in ("NQ", "ES") else frozenset()
    bad = bad_minutes(F) if root == "GC" else None
    return F, skip, bad


def cut_data(D, cut):
    k = int(np.searchsorted(D["t"], cut))
    return {key: (val[:k] if isinstance(val, np.ndarray) and len(val) == len(D["t"]) else val) for key, val in D.items()}


def dry_run():
    bside = bond_sides()
    days = pd.bdate_range("2020-01-02", "2026-09-22"); sd = pd.Series([bside(d) for d in days], index=days)
    print("share of bonds-up days by year: " + " ".join(f"{y}: {g.eq(1).mean():.0%}" for y, g in sd.groupby(sd.index.year)))
    for tr, (mkt, root, *_r) in TRIALS.items():
        E = load(mkt); A, M, C = trades(E, tr, *mt5_SPAN, bside, seed=seed_of(mkt))
        print(f"{tr} {mkt}: aligned trades DEV {len(per(A, DEV))} VAL {len(per(A, VAL))} HOLD {len(per(A, HOLD))} | misaligned DEV {len(per(M, DEV))}"
              f" | aligned longs share DEV {per(A, DEV).side.eq(1).mean():.0%}")
        r = A.iloc[len(A) // 4]; loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens").tz_convert(NYZ)
        print(f"   hand check {r.day.date()} bond trend {r.bond:+d} side {r.side:+d} entry {r.entry:.2f} at {loc:%H:%M} NY, stop {r.stop:.2f}, box {r.W:.2f}")
        cut = ts(2023, 6, 30, 12, 0, NYZ)
        A2, M2, C2 = trades(cut_data(E, cut), tr, mt5_SPAN[0], "2023-06-29", bond_sides("2023-06-30"), seed=seed_of(mkt))
        ok = all(len(a[a.day <= "2023-06-29"]) == len(b) and np.allclose(a[a.day <= "2023-06-29"].R.to_numpy(), b.R.to_numpy()) for a, b in ((A, A2), (M, M2), (C, C2)))
        print(f"   truncation test (data and ZN cut 2023-06-30): {'PASS' if ok else 'FAIL'}")
        F, skip, bad = fut_data(tr, E)
        AF, _, _ = trades(F, tr, "2020-01-02", "2024-12-31", bside, skip, bad, seed=seed_of(root))
        o = per(AF, ("2020-01-01", "2022-01-01"))
        m = per(A, DEV).merge(per(AF, DEV), on="day", suffixes=("_mt5", "_fut"))
        print(f"   OOT {root} 2020-21 aligned trades (no P&L): {len(o)} | port check 2022-24: common days {len(m)}, same side {np.mean(m.side_mt5 == m.side_fut):.0%},"
              f" R correlation {np.corrcoef(m.R_mt5, m.R_fut)[0, 1]:.2f} (bars 80%, 0.6)")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    bside = bond_sides(); days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1627)

    def acct(x, risk):
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], risk)
        return "  ".join(f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("30 Nov", "22 Dec", "30 Jun 27"))

    res = {}
    for tr, (mkt, root, *_r) in TRIALS.items():
        E = load(mkt); A, M, C = trades(E, tr, *mt5_SPAN, bside, seed=seed_of(mkt)); res[tr] = A
        d, v, cD, cV, mD = per(A, DEV), per(A, VAL), per(C, DEV), per(C, VAL), per(M, DEV)
        md, td = ct(d); mv, tv = ct(v); iD, tiD = info(d, cD); iV, _ = info(v, cV)
        yc = d.groupby(d.day.dt.year).R.agg(["mean", "size"])
        okd = len(d) >= 80 and md > 0 and td >= TBAR and iD > 0 and tiD >= 1.65 and md > mD.R.mean() and (yc["mean"] > 0).sum() >= 2
        okv = mv > 0 and tv >= 1.65 and iV > 0
        F, skip, bad = fut_data(tr, E); AF, MF, CF = trades(F, tr, *OOT, bside, skip, bad, seed=seed_of(root))
        mo, to = ct(AF); io, _ = info(AF, CF); oko = mo > 0 and to >= 1.65
        line = (f"{tr} {mkt} bond-aligned: DEV n {len(d)} {md:+.3f} R (t {td:+.2f}) win {(d.R > 0).mean():.0%} | aligned random {cD.groupby('day').R.mean().mean():+.3f}"
                f" info {iD:+.3f} (t {tiD:+.2f}) | misaligned n {len(mD)} {mD.R.mean():+.3f} | longs {d[d.side == 1].R.mean():+.3f} shorts {d[d.side == -1].R.mean():+.3f} | yrs "
                + "/".join(f"{y}:{r['mean']:+.2f}({int(r['size'])})" for y, r in yc.iterrows()) + f" -> DEV {'PASS' if okd else 'FAIL'}"
                f"\n     VAL n {len(v)} {mv:+.3f} (t {tv:+.2f}) info {iV:+.3f} misaligned {per(M, VAL).R.mean():+.3f} -> {'PASS' if okv else 'FAIL'}"
                f" | OOT {root} 2020-21 n {len(AF)} {mo:+.3f} (t {to:+.2f}) info {io:+.3f} misaligned {MF.R.mean():+.3f} -> {'PASS' if oko else 'FAIL'}")
        if okd and okv and oko:
            h = per(A, HOLD); mh, th = ct(h); line += f" | HOLD n {len(h)} {mh:+.3f} (t {th:+.2f}) -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}"
        else:
            line += " | HOLD sealed"
        print(line)
    print("\nAccount view (2022-25 trades, from 95,472, MT5 broker rules; pass% / breach% by date):")
    for tr, A in res.items():
        x = A[A.day < "2026-01-01"]
        for risk in (250, 500):
            print(f"  {tr} ${risk}: ({len(x)} trades, {x.R.mean():+.3f} R) {acct(x, risk)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
