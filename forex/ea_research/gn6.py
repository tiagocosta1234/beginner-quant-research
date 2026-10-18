"""GN6: the overnight-range breakout on S&P 500 (X1), Dow (X2) and gold (X3), MT5 DEV / VAL / HOLD plus a 2020-21 futures
out-of-time check (ES, GC). Pre-registration: forex/ea_research/PREREG_GN6.md.   python -m forex.ea_research.gn6 --dry-run | --run"""
import argparse, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts
from forex.ea_research.orbx import ct
from forex.ea_research.gn1 import per, DEV, VAL, HOLD, NCTRL
from forex.ea_research.gn2 import info
from forex.ea_research.gn5 import load_fut, roll_mondays

NYZ = "America/New_York"
FUTP = "futures/data/databento/futures_{}.F_1m.parquet"
# trial: MT5 broker market, futures root (None = no OOT), range end / window start, window end, exit (New York)
TRIALS = {"X1": ("SP", "ES", (9, 30), (12, 0), (15, 55)),
          "X2": ("DOW", None, (9, 30), (12, 0), (15, 55)),
          "X3": ("XAUUSD", "GC", (8, 20), (11, 0), (13, 25))}
TBAR = 2.13
OOT = ("2020-01-02", "2021-12-31")


def orb_on(D, start, end_day, b1, w1, xh, skip=frozenset(), bad=None, trial="X"):
    """gn5.o1 with the market's times; `bad` = sorted server epochs of contract-switch / flip minutes (skip days containing one)"""
    t = D["t"]; n = len(t); end = int(t[-1]) + 60
    rng = np.random.default_rng(sum(map(ord, trial)) * 104729)
    out, ctrl, wid = [], [], []
    for d in pd.bdate_range(start, end_day):
        if d in skip:
            continue
        p = d - pd.Timedelta(days=1)
        s0 = ts(p.year, p.month, p.day, 18, 0, NYZ)
        s1, e1, xe = (ts(d.year, d.month, d.day, *hm, NYZ) for hm in (b1, w1, xh))
        if xe > end:
            continue
        if bad is not None and len(bad) and np.searchsorted(bad, s0) < np.searchsorted(bad, xe):
            continue
        i0, i1, iw, ix = (int(v) for v in np.searchsorted(t, [s0, s1, e1, xe]))
        if i1 - i0 < 0.8 * (s1 - s0) / 60 or iw - i1 < 30 or ix >= n or ix <= i1 + 1:
            continue
        hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); W = hi - lo
        if W <= 0:
            continue
        sp = np.median(D["ao"][i0:i1] - D["bo"][i0:i1]); wid.append(W / sp if sp > 0 else np.nan)
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
    return pd.DataFrame(out), pd.DataFrame(ctrl), np.array(wid)


def mt5_spread(D, b1, xh):
    """median MT5 broker spread (price units) inside the trading window, 2022-26"""
    loc = pd.to_datetime(D["t"], unit="s").tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").tz_convert(NYZ)
    hm = loc.hour * 60 + loc.minute; m = (hm >= b1[0] * 60 + b1[1]) & (hm < xh[0] * 60 + xh[1])
    return float(np.median(D["sp"][np.asarray(m)]))


def bad_minutes(D, thr=0.003):
    """server epochs of contract switches (jump > thr at 00:00 UTC +/- 1 min) and flips (opposite jumps > thr within 60 min)"""
    t = D["t"]; r = D["bo"][1:] / D["bc"][:-1] - 1; dt = np.diff(t); j = np.flatnonzero((np.abs(r) > thr) & (dt <= 120)) + 1
    utc = pd.to_datetime(t[j], unit="s").tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    um = np.asarray(utc.hour * 60 + utc.minute)
    sw = j[(um <= 1) | (um >= 1439)]
    fl = [j[a] for a in range(len(j)) for b in range(a + 1, len(j)) if t[j[b]] - t[j[a]] <= 3600 and np.sign(r[j[a] - 1]) != np.sign(r[j[b] - 1])]
    return np.unique(np.r_[t[sw], t[np.array(fl, dtype=int)] if fl else np.array([], int)])


def futures(tr, spread):
    mkt, root, b1, w1, xh = TRIALS[tr]
    F = load_fut(FUTP.format(root), spread)
    sk = roll_mondays() if root == "ES" else frozenset()
    bad = bad_minutes(F) if root == "GC" else None
    return F, sk, bad


def dry_run():
    for tr, (mkt, root, b1, w1, xh) in TRIALS.items():
        E = load(mkt); T, C, wid = orb_on(E, "2022-01-03", "2026-10-16", b1, w1, xh, trial=tr)
        sp = mt5_spread(E, b1, xh)
        print(f"{tr} {mkt}: trades DEV {len(per(T, DEV))} VAL {len(per(T, VAL))} HOLD {len(per(T, HOLD))} | median range {np.nanmedian(wid):.0f} spreads"
              f" | MT5 broker median spread in the window {sp:.3f} (OOT cost model)")
        for _, r in T.sample(2, random_state=21).iterrows():
            loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens").tz_convert(NYZ)
            print(f"   hand check {r.day.date()} side {r.side:+d} entry {r.entry:.2f} at {loc:%H:%M} NY, stop {r.stop:.2f} (range {r.W:.2f})")
        if root:
            F, sk, bad = futures(tr, sp)
            if bad is not None:
                bd = sorted({pd.Timestamp(x, unit="s").date() for x in bad if pd.Timestamp("2019-12-25") <= pd.Timestamp(x, unit="s") < pd.Timestamp("2022-01-05")})
                print(f"   GC switch / flip minutes 2020-21: {len(bd)} dates: {bd}")
            TF, _, _ = orb_on(F, *OOT, b1, w1, xh, sk, bad, trial=tr)
            TP, _, _ = orb_on(F, "2022-01-03", "2024-12-31", b1, w1, xh, sk, bad, trial=tr)
            m = per(T, DEV).merge(TP, on="day", suffixes=("_mt5", "_fut"))
            print(f"   OOT counts (no P&L): 2020 {(TF.day.dt.year == 2020).sum()} 2021 {(TF.day.dt.year == 2021).sum()} | port check 2022-24: common days {len(m)},"
                  f" same side {np.mean(m.side_mt5 == m.side_fut):.0%}, R correlation {np.corrcoef(m.R_mt5, m.R_fut)[0, 1]:.2f} (bar >= 0.6)")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1627)
    def acct(x, risk):
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], risk)
        return "  ".join(f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("30 Nov", "22 Dec", "30 Jun 27"))
    res = {}
    for tr, (mkt, root, b1, w1, xh) in TRIALS.items():
        E = load(mkt); T, C, _ = orb_on(E, "2022-01-03", "2026-10-16", b1, w1, xh, trial=tr); res[tr] = T
        d, v, cD, cV = per(T, DEV), per(T, VAL), per(C, DEV), per(C, VAL)
        md, td = ct(d); mv, tv = ct(v); iD, tiD = info(d, cD); iV, tiV = info(v, cV)
        yc = d.groupby(d.day.dt.year).R.agg(["mean", "size"])
        okd = len(d) >= 150 and md > 0 and td >= TBAR and iD > 0 and tiD >= 1.65 and (yc["mean"] > 0).sum() >= 2
        okv = mv > 0 and tv >= 1.65 and iV > 0
        line = (f"{tr} {mkt}: DEV n {len(d)} {md:+.3f} R (t {td:+.2f}) win {(d.R > 0).mean():.0%} | control {cD.groupby('day').R.mean().mean():+.3f} info {iD:+.3f} (t {tiD:+.2f})"
                f" | yrs " + "/".join(f"{y}:{r['mean']:+.2f}" for y, r in yc.iterrows()) + f" | longs {d[d.side == 1].R.mean():+.3f} shorts {d[d.side == -1].R.mean():+.3f}"
                f" -> DEV {'PASS' if okd else 'FAIL'} | VAL n {len(v)} {mv:+.3f} (t {tv:+.2f}) info {iV:+.3f} -> {'PASS' if okv else 'FAIL'}")
        oko = True
        if root:
            F, sk, bad = futures(tr, mt5_spread(E, b1, xh))
            TF, CF, _ = orb_on(F, *OOT, b1, w1, xh, sk, bad, trial=tr)
            mo, to = ct(TF); io, tio = info(TF, CF); yo = TF.groupby(TF.day.dt.year).R.mean()
            oko = mo > 0 and to >= 1.65 and (yo > 0).all()
            line += f" | OOT {root} 2020-21 n {len(TF)} {mo:+.3f} (t {to:+.2f}) info {io:+.3f} yrs " + "/".join(f"{x:+.3f}" for x in yo) + f" -> {'PASS' if oko else 'FAIL'}"
        if okd and okv and oko:
            h = per(T, HOLD); mh, th = ct(h); line += f" | HOLD n {len(h)} {mh:+.3f} (t {th:+.2f}) -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}"
        else:
            line += " | HOLD sealed"
        print(line)
    print("\nAccount view (2022-25 trades, from 95,472, MT5 broker rules; pass% / breach% by date):")
    from forex.ea_research.gn3 import trades as gn3_trades
    res["O1 (closed)"] = gn3_trades("O1")[0]
    for tr, T in res.items():
        x = T[T.day < "2026-01-01"]
        for risk in (250, 500):
            print(f"  {tr} ${risk}: ({len(x)} trades, {x.R.mean():+.3f} R) {acct(x, risk)}")
    x = pd.concat(res.values()); x = x[x.day < "2026-01-01"]
    print(f"  book X1+X2+X3+O1 $150 a trade: ({len(x)} trades, {x.R.mean():+.3f} R) {acct(x, 150)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
