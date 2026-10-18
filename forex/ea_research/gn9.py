"""GN9: late-day continuation on big-move days. ROD = previous session close -> decision minute; on days with |ROD| in the top
quartile of the previous 250 days, trade the last half hour in the direction of ROD (L1 NSDQ, L2 SP: 15:30-15:58 New York;
L3 XAUUSD: 13:00-13:28, COMEX). Stop 2 S (S = 14-day mean last-half-hour move), R = 2 S.
MT5 DEV 2022-24 / VAL 2025 / HOLD 2026, CME futures 2020-21 out of time. Pre-registration: forex/ea_research/PREREG_GN9.md.
   python -m forex.ea_research.gn9 --dry-run | --run"""
import argparse, collections, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts
from forex.ea_research.orbx import ct
from forex.ea_research.gn2 import info
from forex.ea_research.gn5 import load_fut, roll_mondays
from forex.ea_research.gn6 import mt5_spread, bad_minutes

NYZ = "America/New_York"
FUTP = "futures/data/databento/futures_{}.F_1m.parquet"
# trial: MT5 broker market, futures root, decision minute, exit minute (its close), reference minute of the previous session
TRIALS = {"L1": ("NSDQ", "NQ", (15, 29), (15, 58), (15, 59)),
          "L2": ("SP", "ES", (15, 29), (15, 58), (15, 59)),
          "L3": ("XAUUSD", "GC", (12, 59), (13, 28), (13, 29))}
TBAR, NCT, PCT, LOOK, MINH, NS = 2.13, 5, 75, 250, 60, 14
DEV, VAL, HOLD = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-10-17")
OOT = ("2020-01-02", "2021-12-31")
mt5_SPAN = ("2021-12-01", "2026-10-16")


def lateday(D, start, end_day, dec, xit, ref, skip=frozenset(), bad=None, seed=0, flip=False):
    """flip=True trades AGAINST ROD (the GN10 reversal); the default reproduces GN9 exactly"""
    t = D["t"]; n = len(t); rng = np.random.default_rng(seed)
    mid = (D["bc"] + D["ac"]) / 2
    hrod, hs = collections.deque(maxlen=LOOK), collections.deque(maxlen=NS)
    last_ref = None; out, ctrl = [], []

    def at(ep):
        i = int(np.searchsorted(t, ep))
        return i if i < n and t[i] == ep else -1

    for d in pd.bdate_range(start, end_day):
        sd, sx, sr = (ts(d.year, d.month, d.day, *hm, NYZ) for hm in (dec, xit, ref))
        jd, jx, jr = at(sd), at(sx), at(sr)
        prev = last_ref
        if jr >= 0:
            last_ref = (sr, mid[jr])                       # today's close becomes the next session's reference
        if d in skip or jd < 0 or jx < 0 or jd + 1 >= n or t[jd + 1] != sd + 60 or prev is None or sd - prev[0] > 5 * 86400:
            continue
        if bad is not None and len(bad) and np.searchsorted(bad, prev[0]) < np.searchsorted(bad, sx + 60):
            continue
        rod = mid[jd] / prev[1] - 1
        S = float(np.mean(hs)) if len(hs) == NS else np.nan
        thr = float(np.percentile(hrod, PCT)) if len(hrod) >= MINH else np.nan
        hrod.append(abs(rod)); hs.append(abs(mid[jx] - mid[jd]))   # appended after use: only earlier days set S and thr
        if not (np.isfinite(S) and np.isfinite(thr)) or S <= 0 or rod == 0:
            continue
        side = (1 if rod > 0 else -1) * (-1 if flip else 1); f = jd + 1; R = 2 * S

        def trade(s_):
            e = D["ao"][f] if s_ == 1 else D["bo"][f]
            ex, _ = walk(D, s_, f, jx + 1, e - s_ * R, None)
            return s_ * (ex - e) / R

        big = abs(rod) >= thr
        out.append(dict(day=d, rod=rod, thr=thr, big=big, side=side, S=S, spr=D["ao"][f] - D["bo"][f], t_entry=int(t[f]),
                        entry=D["ao"][f] if side == 1 else D["bo"][f], R=trade(side), R_long=trade(1)))
        for _ in range(NCT):
            ctrl.append(dict(day=d, big=big, R=trade(int(rng.choice([1, -1])))))
    return pd.DataFrame(out), pd.DataFrame(ctrl)


def per(x, p):
    return x[(x.day >= p[0]) & (x.day < p[1])]


def seed_of(s):
    return sum(map(ord, s)) * 2246822519 % (1 << 32)


def mt5_run(mkt, dec, xit, ref, D=None, end_day=mt5_SPAN[1]):
    D = D if D is not None else load(mkt)
    return D, lateday(D, mt5_SPAN[0], end_day, dec, xit, ref, seed=seed_of(mkt))


def fut_run(root, spread, dec, xit, ref, start=OOT[0], end_day=OOT[1]):
    F = load_fut(FUTP.format(root), spread)
    sk = roll_mondays() if root in ("NQ", "ES") else frozenset(); bad = bad_minutes(F) if root == "GC" else None
    return lateday(F, start, end_day, dec, xit, ref, sk, bad, seed=seed_of(root))


def cut_data(D, cut):
    k = int(np.searchsorted(D["t"], cut))
    return {key: (val[:k] if isinstance(val, np.ndarray) and len(val) == len(D["t"]) else val) for key, val in D.items()}


def window_spread(E, dec, xit):
    return mt5_spread(E, (dec[0], dec[1] + 1) if dec[1] < 59 else (dec[0] + 1, 0), xit)


def dry_run():
    rows = list(TRIALS.items()) + [("DOW", ("DOW", None, (15, 29), (15, 58), (15, 59)))]
    for tr, (mkt, root, dec, xit, ref) in rows:
        E, (T, C) = mt5_run(mkt, dec, xit, ref)
        sp = window_spread(E, dec, xit)
        cnt = " ".join(f"{pn} {len(per(T, p))}/{int(per(T, p).big.sum())}" for pn, p in (("DEV", DEV), ("VAL", VAL), ("HOLD", HOLD)))
        print(f"{tr} {mkt}: eligible/big days {cnt} | first trade {T.day.min().date()} | median S {np.median(T.S / T.spr):.1f} spreads"
              f" (stop 2 S = {np.median(2 * T.S / T.spr):.1f}) | MT5 broker window spread {sp:.3f}")
        for _, r in T[T.big].sample(2, random_state=5).iterrows():
            loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens").tz_convert(NYZ)
            print(f"   hand check {r.day.date()} ROD {100 * r.rod:+.2f}% (threshold {100 * r.thr:.2f}%) side {r.side:+d} entry {r.entry:.2f} at {loc:%H:%M} NY, S {r.S:.2f}")
        cut = ts(2023, 6, 30, 12, 0, NYZ)
        _, (T2, C2) = mt5_run(mkt, dec, xit, ref, D=cut_data(E, cut), end_day="2023-06-29")
        a, b = T[T.day <= "2023-06-29"], T2
        ok = len(a) == len(b) and np.allclose(a.R.to_numpy(), b.R.to_numpy()) and (a.big.to_numpy() == b.big.to_numpy()).all()
        print(f"   truncation test (data cut 2023-06-30 12:00 NY): {'PASS' if ok else 'FAIL'}")
        if root:
            TF, _ = fut_run(root, sp, dec, xit, ref, OOT[0], "2024-12-31")
            o = per(TF, ("2020-01-01", "2022-01-01"))
            print(f"   OOT {root} 2020-21 (no P&L): eligible {len(o)}, big {int(o.big.sum())}, first trade {TF.day.min().date()}")
            m = per(T, DEV).merge(per(TF, DEV), on="day", suffixes=("_mt5", "_fut"))
            print(f"   port check 2022-24: common days {len(m)}, same side {np.mean(m.side_mt5 == m.side_fut):.0%}, R correlation"
                  f" {np.corrcoef(m.R_mt5, m.R_fut)[0, 1]:.2f}, same big flag {np.mean(m.big_mt5 == m.big_fut):.0%} (bars: 80%, 0.6)")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1627)

    def acct(x, risk):
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], risk)
        return "  ".join(f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("30 Nov", "22 Dec", "30 Jun 27"))

    res = {}
    for tr, (mkt, root, dec, xit, ref) in TRIALS.items():
        E, (A, CA) = mt5_run(mkt, dec, xit, ref)
        T, C, O = A[A.big], CA[CA.big], A[~A.big]; res[tr] = T
        d, v, cD, cV, oD = per(T, DEV), per(T, VAL), per(C, DEV), per(C, VAL), per(O, DEV)
        md, td = ct(d); mv, tv = ct(v); iD, tiD = info(d, cD); iV, _ = info(v, cV)
        yc = d.groupby(d.day.dt.year).R.agg(["mean", "size"])
        okd = len(d) >= 80 and md > 0 and td >= TBAR and iD > 0 and tiD >= 1.65 and md > oD.R.mean() and (yc["mean"] > 0).sum() >= 2
        okv = mv > 0 and tv >= 1.65 and iV > 0
        AF, CF = fut_run(root, window_spread(E, dec, xit), dec, xit, ref)
        TF, CFb = AF[AF.big], CF[CF.big]; mo, to = ct(TF); io, _ = info(TF, CFb); yo = TF.groupby(TF.day.dt.year).R.mean()
        oko = mo > 0 and to >= 1.65
        line = (f"{tr} {mkt} big-move days: DEV n {len(d)} {md:+.3f} R (t {td:+.2f}) win {(d.R > 0).mean():.0%} | control {cD.groupby('day').R.mean().mean():+.3f}"
                f" info {iD:+.3f} (t {tiD:+.2f}) | other days n {len(oD)} {oD.R.mean():+.3f} | long-only same days {d.R_long.mean():+.3f} | yrs "
                + "/".join(f"{y}:{r['mean']:+.2f}({int(r['size'])})" for y, r in yc.iterrows()) + f" -> DEV {'PASS' if okd else 'FAIL'}"
                f"\n     VAL n {len(v)} {mv:+.3f} (t {tv:+.2f}) info {iV:+.3f} other days {per(O, VAL).R.mean():+.3f} -> {'PASS' if okv else 'FAIL'}"
                f" | OOT {root} 2020-21 n {len(TF)} {mo:+.3f} (t {to:+.2f}) info {io:+.3f} other days {AF[~AF.big].R.mean():+.3f} yrs "
                + "/".join(f"{x:+.3f}" for x in yo) + f" -> {'PASS' if oko else 'FAIL'}")
        if okd and okv and oko:
            h = per(T, HOLD); mh, th = ct(h); line += f" | HOLD n {len(h)} {mh:+.3f} (t {th:+.2f}) -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}"
        else:
            line += " | HOLD sealed"
        print(line)
        x = A[A.day < "2026-01-01"].copy(); x["q"] = pd.cut(x.rod.abs() / x.thr, [0, 0.33, 0.66, 1.0, 1.5, 99])
        xf = AF.copy(); xf["q"] = pd.cut(xf.rod.abs() / xf.thr, [0, 0.33, 0.66, 1.0, 1.5, 99])
        print("   by |ROD| / threshold (MT5 2022-25 | futures 2020-21): " + " ".join(f"{iv.left:g}-{iv.right:g} {g.R.mean():+.3f}({len(g)})" for iv, g in x.groupby("q", observed=True))
              + " | " + " ".join(f"{iv.left:g}-{iv.right:g} {g.R.mean():+.3f}({len(g)})" for iv, g in xf.groupby("q", observed=True)))
    E, (A, _) = mt5_run("DOW", (15, 29), (15, 58), (15, 59))
    print(f"\nDescriptive DOW big-move days: DEV {per(A[A.big], DEV).R.mean():+.3f} (n {len(per(A[A.big], DEV))}) VAL {per(A[A.big], VAL).R.mean():+.3f} | other days DEV {per(A[~A.big], DEV).R.mean():+.3f}")
    print("\nAccount view (2022-25 trades, from 95,472, MT5 broker rules; pass% / breach% by date; R = 2 S):")
    for tr, T in res.items():
        x = T[T.day < "2026-01-01"]
        for risk in (250, 500):
            print(f"  {tr} ${risk}: ({len(x)} trades, {x.R.mean():+.3f} R) {acct(x, risk)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
