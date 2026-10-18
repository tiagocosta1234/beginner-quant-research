"""GN7: Zarattini-Aziz 5-minute opening-range breakout on high relative-volume (RVOL5 >= 1.5) days, CME futures with exchange
volume, MT5 broker cost model. Q1 Nasdaq (NQ, 09:30 NY), Q2 gold (GC, 08:20 NY). Pre-registration: forex/ea_research/PREREG_GN7.md.
   python -m forex.ea_research.gn7 --dry-run | --run"""
import argparse, collections, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import walk
from forex.ea_research.brk50 import ts
from forex.ea_research.orbx import ct
from forex.ea_research.gn2 import info
from forex.ea_research.gn5 import roll_mondays
from forex.ea_research.gn6 import bad_minutes

NYZ = "America/New_York"
FUTP = "futures/data/databento/futures_{}.F_1m.parquet"
TRIALS = {"Q1": ("NQ", 1.67, (9, 30), (15, 55)), "Q2": ("GC", 0.190, (8, 20), (13, 25))}
RV, TBAR, NCT = 1.5, 1.96, 5
DEV, VAL, HOLD = ("2020-01-01", "2024-01-01"), ("2024-01-01", "2026-01-01"), ("2026-01-01", "2026-09-26")


def load_futv(root, spread):
    d = pd.read_parquet(FUTP.format(root), columns=["ts", "open", "high", "low", "close", "volume"]).sort_values("ts")
    srv = d.ts.dt.tz_convert("Europe/Athens").dt.tz_localize(None)
    t = ((srv - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy().astype(np.int64)
    keep = np.r_[True, t[1:] > t[:-1]]; D = {"t": t[keep]}
    for k, c in zip("ohlc", ("open", "high", "low", "close")):
        v = d[c].to_numpy()[keep].astype(float); D["b" + k] = v; D["a" + k] = v + spread
    D["v"] = d.volume.to_numpy()[keep].astype(float); sod = D["t"] % 86400
    D["roll"] = (sod >= 23 * 3600) | (sod < 3600); D["sp"] = np.full(len(D["t"]), spread)
    return D


def trades(trial, D=None):
    root, spread, op, xh = TRIALS[trial]
    D = D if D is not None else load_futv(root, spread)
    t = D["t"]; n = len(t)
    skip = roll_mondays() if root == "NQ" else frozenset(); bad = bad_minutes(D) if root == "GC" else np.array([], int)
    rng = np.random.default_rng(sum(map(ord, trial)) * 7368787)
    hist = collections.deque(maxlen=14); out, ctrl, past = [], [], []      # past: earlier RVOL5 values (amendment 1)
    for d in pd.bdate_range("2020-01-02", "2026-09-25"):
        s0 = ts(d.year, d.month, d.day, *op, NYZ); xe = ts(d.year, d.month, d.day, *xh, NYZ)
        i0, i5, ix = (int(v) for v in np.searchsorted(t, [s0, s0 + 300, xe]))
        if i5 - i0 != 5 or t[i0] != s0 or i5 >= n or t[i5] - (s0 + 300) > 120 or ix >= n or ix <= i5 + 1:
            continue
        p = d - pd.Timedelta(days=1); pb = ts(p.year, p.month, p.day, 18, 0, NYZ)
        if d in skip or (len(bad) and np.searchsorted(bad, pb) < np.searchsorted(bad, xe)):
            continue
        v5 = D["v"][i0:i5].sum(); rv = v5 / np.mean(hist) if len(hist) == 14 and np.mean(hist) > 0 else np.nan
        hist.append(v5)
        o, c = D["bo"][i0], D["bc"][i5 - 1]; hi, lo = D["bh"][i0:i5].max(), D["bl"][i0:i5].min()
        if not np.isfinite(rv):
            continue
        thr = np.percentile(past, 80) if len(past) >= 60 else np.inf; past.append(rv)
        if c == o or not np.isfinite(thr):
            continue
        side = 1 if c > o else -1; f = i5
        e = D["ao"][f] if side == 1 else D["bo"][f]; st = lo if side == 1 else hi
        if side * (e - st) <= 0:
            continue
        dist = abs(e - st); tp = e + side * 10 * dist
        ex, _ = walk(D, side, f, ix, st, tp)
        out.append(dict(trial=trial, day=d, rv=rv, thr=thr, inplay=rv >= thr, side=side, t_entry=int(t[f]), entry=e, stop=st, R=side * (ex - e) / dist, risk_sp=dist / spread))
        if rv >= thr:
            for _ in range(NCT):
                s2 = int(rng.choice([1, -1])); e2 = D["ao"][f] if s2 == 1 else D["bo"][f]
                ex2, _ = walk(D, s2, f, ix, e2 - s2 * dist, e2 + s2 * 10 * dist)
                ctrl.append(dict(trial=trial, day=d, R=s2 * (ex2 - e2) / dist))
    return pd.DataFrame(out), pd.DataFrame(ctrl)


def per(x, p):
    return x[(x.day >= p[0]) & (x.day < p[1])]


def dry_run():
    for tr, (root, *_ ) in TRIALS.items():
        T, C = trades(tr); I = T[T.inplay]
        print(f"{tr} {root}: rule days {len(T)} | in-play share by year " + " ".join(f"{y}:{g.inplay.mean():.0%}" for y, g in T.groupby(T.day.dt.year))
              + f" | in-play trades DEV {len(per(I, DEV))} VAL {len(per(I, VAL))} HOLD {len(per(I, HOLD))} | median risk {I.risk_sp.median():.0f} spreads")
        for _, r in I.sample(2, random_state=2).iterrows():
            loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens").tz_convert(NYZ)
            print(f"   hand check {r.day.date()} RVOL5 {r.rv:.2f} side {r.side:+d} entry {r.entry:.2f} at {loc:%H:%M} NY, stop {r.stop:.2f}")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    days = pd.bdate_range("2020-01-02", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1627)
    def acct(x, risk):
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], risk)
        return "  ".join(f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("30 Nov", "22 Dec", "30 Jun 27"))
    res = {}
    for tr, (root, *_ ) in TRIALS.items():
        T, C = trades(tr); I, O = T[T.inplay], T[~T.inplay]; res[tr] = I
        d, v, oD = per(I, DEV), per(I, VAL), per(O, DEV)
        md, td = ct(d); mv, tv = ct(v); iD, tiD = info(d, per(C, DEV)); iV, _ = info(v, per(C, VAL))
        yc = d.groupby(d.day.dt.year).R.mean()
        ok = len(d) >= 80 and md > 0 and td >= TBAR and iD > 0 and tiD >= 1.65 and md > oD.R.mean() and (yc > 0).sum() >= 3
        okv = ok and mv > 0 and tv >= 1.65 and iV > 0
        line = (f"{tr} {root} in-play: DEV n {len(d)} {md:+.3f} R (t {td:+.2f}) win {(d.R > 0).mean():.0%} | random-direction control {per(C, DEV).groupby('day').R.mean().mean():+.3f}"
                f" info {iD:+.3f} (t {tiD:+.2f}) | other days n {len(oD)} {oD.R.mean():+.3f} | yrs " + "/".join(f"{x:+.2f}" for x in yc)
                + f" -> {'PASS' if ok else 'FAIL'} | VAL n {len(v)} {mv:+.3f} (t {tv:+.2f}) info {iV:+.3f} | VAL other days {per(O, VAL).R.mean():+.3f}")
        if okv:
            h = per(I, HOLD); mh, th = ct(h); line += f" | HOLD n {len(h)} {mh:+.3f} (t {th:+.2f}) -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}"
        else:
            line += " | HOLD sealed"
        print(line)
        print(f"   by RVOL5 band (2020-25, descriptive): " + " ".join(f"{lab} {g.R.mean():+.3f} ({len(g)})" for lab, g in
              T[T.day < "2026-01-01"].groupby(pd.cut(T[T.day < "2026-01-01"].rv, [0, 0.75, 1.0, 1.25, 1.5, 2.0, 99]), observed=True)))
    print("\nAccount view (2020-25 in-play trades, from 95,472, MT5 broker rules; pass% / breach% by date):")
    for tr, I in res.items():
        x = I[I.day < "2026-01-01"]
        for risk in (250, 500):
            print(f"  {tr} ${risk}: ({len(x)} trades, {x.R.mean():+.3f} R) {acct(x, risk)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
