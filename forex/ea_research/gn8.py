"""GN8: dealer-gamma regime (VIX close of the day before >= 20 = stress, < 20 = calm) and the New York 30-minute opening-range
breakout on Nasdaq and S&P: FOLLOW on stress days (V1 NSDQ, V2 SP), FADE on calm days (V3 NSDQ, V4 SP).
MT5 DEV 2022-24 / VAL 2025 / HOLD 2026, CME futures 2020-21 out of time. Pre-registration: forex/ea_research/PREREG_GN8.md.
   python -m forex.ea_research.gn8 --dry-run | --run"""
import argparse, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts
from forex.ea_research.orbx import ct
from forex.ea_research.gn2 import info
from forex.ea_research.gn5 import load_fut, roll_mondays
from forex.ea_research.gn6 import mt5_spread

NYZ = "America/New_York"
FUTP = "futures/data/databento/futures_{}.F_1m.parquet"
VIXP = "futures/data/daily/^VIX_yahoo_daily.csv"
B0, B1, W1, XH = (9, 30), (10, 0), (12, 0), (15, 55)
TRIALS = {"V1": ("NSDQ", "NQ", "follow", "stress"), "V2": ("SP", "ES", "follow", "stress"),
          "V3": ("NSDQ", "NQ", "fade", "calm"), "V4": ("SP", "ES", "fade", "calm")}
LEVEL, TBAR, NCT = 20.0, 2.24, 5
DEV, VAL, HOLD = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-09-23")
OOT = ("2020-01-02", "2021-12-31")
mt5_SPAN = ("2022-01-03", "2026-09-22")
OPP = {"stress": "calm", "calm": "stress"}
BIG = 1 << 40


def vix_series(cut=None):
    v = pd.read_csv(VIXP, parse_dates=["date"]).set_index("date").close.dropna().sort_index()
    return v[v.index < pd.Timestamp(cut)] if cut is not None else v


def vix_before(v, d):
    """VIX close of the last trading day strictly before d (NaN if older than 7 calendar days)"""
    i = int(v.index.searchsorted(d)) - 1
    if i < 0 or (d - v.index[i]).days > 7:
        return np.nan
    return float(v.iloc[i])


def first(mask):
    k = np.flatnonzero(mask)
    return int(k[0]) if len(k) else BIG


def events(D, start, end_day, vix, skip=frozenset(), seed=0):
    """per eligible day: the FOLLOW trade, the FADE trade and 5 random controls of each type, tagged with the VIX regime"""
    t = D["t"]; n = len(t); end = int(t[-1]) + 60
    rng = np.random.default_rng(seed)
    F, A, CF, CA = [], [], [], []
    for d in pd.bdate_range(start, end_day):
        if d in skip:
            continue
        vx = vix_before(vix, d)
        if not np.isfinite(vx):
            continue
        s0, s1, e1, xe = (ts(d.year, d.month, d.day, *hm, NYZ) for hm in (B0, B1, W1, XH))
        if xe > end:
            continue
        i0, i1, iw, ix = (int(x) for x in np.searchsorted(t, [s0, s1, e1, xe]))
        if i1 - i0 < 24 or iw - i1 < 90 or ix >= n or ix <= iw or t[ix] - xe > 600:
            continue
        hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); W = hi - lo
        if W <= 0:
            continue
        sp = np.median(D["ao"][i0:i1] - D["bo"][i0:i1])
        base = dict(day=d, vix=vx, reg="stress" if vx >= LEVEL else "calm", W=W, wsp=W / sp if sp > 0 else np.nan)
        nr = ~D["roll"][i1:iw]
        kl, ks = first((D["ah"][i1:iw] >= hi) & nr), first((D["bl"][i1:iw] <= lo) & nr)
        if kl != ks and min(kl, ks) < BIG:                                   # FOLLOW: stop orders at the box edges
            side = 1 if kl < ks else -1; k = i1 + min(kl, ks)
            e = max(hi, D["ao"][k]) if side == 1 else min(lo, D["bo"][k]); st = lo if side == 1 else hi
            if side * (e - st) > 0:
                ex, _ = walk(D, side, k, ix, st, None)
                F.append(dict(base, side=side, t_entry=int(t[k]), entry=e, stop=st, R=side * (ex - e) / abs(e - st)))
        ku, kd = first((D["bh"][i1:iw] >= hi) & nr), first((D["al"][i1:iw] <= lo) & nr)
        if ku != kd and min(ku, kd) < BIG:                                   # FADE: limit orders at the box edges
            side = -1 if ku < kd else 1; k = i1 + min(ku, kd)
            if side == -1:
                e, st, tp = max(hi, D["bo"][k]), hi + W, lo
            else:
                e, st, tp = min(lo, D["ao"][k]), lo - W, hi
            if side * (e - st) > 0 and side * (tp - e) > 0:
                ex, _ = walk(D, side, k, ix, st, tp)
                A.append(dict(base, side=side, t_entry=int(t[k]), entry=e, stop=st, R=side * (ex - e) / abs(e - st)))
        cand = np.flatnonzero(nr)
        for j in rng.choice(cand, size=min(NCT, len(cand)), replace=False):
            k = i1 + int(j); side = int(rng.choice([1, -1])); e = D["ao"][k] if side == 1 else D["bo"][k]
            ex, _ = walk(D, side, k, ix, e - side * W, None); CF.append(dict(base, R=side * (ex - e) / W))
            ex, _ = walk(D, side, k, ix, e - side * W, e + side * W); CA.append(dict(base, R=side * (ex - e) / W))
    return pd.DataFrame(F), pd.DataFrame(A), pd.DataFrame(CF), pd.DataFrame(CA)


def per(x, p):
    return x[(x.day >= p[0]) & (x.day < p[1])]


def seed_of(mkt):
    return sum(map(ord, mkt)) * 2654435761 % (1 << 32)


def mt5_events(mkt, vix):
    E = load(mkt)
    return E, events(E, *mt5_SPAN, vix, seed=seed_of(mkt))


def fut_events(root, spread, vix, start=OOT[0], end_day=OOT[1]):
    Fu = load_fut(FUTP.format(root), spread)
    return Fu, events(Fu, start, end_day, vix, skip=roll_mondays(), seed=seed_of(root))


def pick(ev, kind, reg):
    F, A, CF, CA = ev
    T, C = (F, CF) if kind == "follow" else (A, CA)
    if len(T) == 0:
        return T, C
    return T[T.reg == reg], C[C.reg == reg]


def cut_data(D, cut):
    k = int(np.searchsorted(D["t"], cut))
    return {key: (val[:k] if isinstance(val, np.ndarray) and len(val) == len(D["t"]) else val) for key, val in D.items()}


def dry_run():
    vix = vix_series()
    for mkt, root in (("NSDQ", "NQ"), ("SP", "ES"), ("DOW", None)):
        E, ev = mt5_events(mkt, vix); F, A, CF, CA = ev
        sp = mt5_spread(E, B0, XH)
        cnt = " | ".join(f"{nm} " + " ".join(f"{pn} {len(per(X[X.reg == 'stress'], p))}/{len(per(X[X.reg == 'calm'], p))}"
                                             for pn, p in (("DEV", DEV), ("VAL", VAL), ("HOLD", HOLD))) for nm, X in (("follow", F), ("fade", A)))
        print(f"{mkt}: trades stress/calm: {cnt} | median box {np.nanmedian(F.wsp):.0f} spreads | MT5 broker window spread {sp:.3f}")
        for nm, X in (("follow", F), ("fade", A)):
            r = X.sample(1, random_state=8).iloc[0]
            loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens").tz_convert(NYZ)
            print(f"   hand check {nm} {r.day.date()} VIX(d-1) {r.vix:.2f} ({r.reg}) side {r.side:+d} entry {r.entry:.2f} at {loc:%H:%M} NY, stop {r.stop:.2f}, box {r.W:.2f}")
        cut = ts(2023, 6, 30, 12, 0, NYZ)
        ev2 = events(cut_data(E, cut), mt5_SPAN[0], "2023-06-29", vix_series("2023-06-30"), seed=seed_of(mkt))
        same = all(len(a[a.day <= "2023-06-29"]) == len(b) and np.allclose(a[a.day <= "2023-06-29"].R.to_numpy(), b.R.to_numpy())
                   for a, b in zip(ev, ev2))
        print(f"   truncation test (data and VIX cut 2023-06-30 12:00 NY): {'PASS' if same else 'FAIL'}")
        if root:
            Fu, evf = fut_events(root, sp, vix, "2020-01-02", "2024-12-31")
            Ff, Af = evf[0], evf[1]
            o = per(Ff, ("2020-01-01", "2022-01-01")); oa = per(Af, ("2020-01-01", "2022-01-01"))
            print(f"   OOT {root} 2020-21 counts (no P&L): follow stress {len(o[o.reg == 'stress'])} calm {len(o[o.reg == 'calm'])} |"
                  f" fade stress {len(oa[oa.reg == 'stress'])} calm {len(oa[oa.reg == 'calm'])}")
            for nm, X, Y in (("follow", F, Ff), ("fade", A, Af)):
                m = per(X, DEV).merge(per(Y, DEV), on="day", suffixes=("_mt5", "_fut"))
                print(f"   port check {nm} 2022-24: common days {len(m)}, same side {np.mean(m.side_mt5 == m.side_fut):.0%},"
                      f" R correlation {np.corrcoef(m.R_mt5, m.R_fut)[0, 1]:.2f} (bars: 80%, 0.6)")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    vix = vix_series(); days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1627)

    def acct(x, risk):
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], risk)
        return "  ".join(f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("30 Nov", "22 Dec", "30 Jun 27"))

    MT5, FU = {}, {}
    for mkt, root in (("NSDQ", "NQ"), ("SP", "ES"), ("DOW", None)):
        E, ev = mt5_events(mkt, vix); MT5[mkt] = ev
        if root:
            FU[mkt] = fut_events(root, mt5_spread(E, B0, XH), vix)[1]
    res = {}
    for tr, (mkt, root, kind, reg) in TRIALS.items():
        T, C = pick(MT5[mkt], kind, reg); O, _ = pick(MT5[mkt], kind, OPP[reg]); res[tr] = T
        d, v, cD, cV, oD = per(T, DEV), per(T, VAL), per(C, DEV), per(C, VAL), per(O, DEV)
        md, td = ct(d); mv, tv = ct(v); iD, tiD = info(d, cD); iV, _ = info(v, cV)
        yc = d.groupby(d.day.dt.year).R.agg(["mean", "size"]); yq = yc[yc["size"] >= 10]
        yok = (yq["mean"] > 0).sum() >= 2 if len(yq) >= 2 else bool(len(yq)) and (yq["mean"] > 0).all()
        okd = len(d) >= 80 and md > 0 and td >= TBAR and iD > 0 and tiD >= 1.65 and md > oD.R.mean() and yok
        okv = mv > 0 and tv >= 1.65 and iV > 0
        TF, CFu = pick(FU[mkt], kind, reg); mo, to = ct(TF); io, _ = info(TF, CFu); yo = TF.groupby(TF.day.dt.year).R.mean()
        oko = mo > 0 and to >= 1.65
        line = (f"{tr} {mkt} {kind} on {reg} days: DEV n {len(d)} {md:+.3f} R (t {td:+.2f}) win {(d.R > 0).mean():.0%} | control {cD.groupby('day').R.mean().mean():+.3f}"
                f" info {iD:+.3f} (t {tiD:+.2f}) | {OPP[reg]} days n {len(oD)} {oD.R.mean():+.3f} | yrs " + "/".join(f"{y}:{r['mean']:+.2f}({int(r['size'])})" for y, r in yc.iterrows())
                + f" -> DEV {'PASS' if okd else 'FAIL'}\n     VAL n {len(v)} {mv:+.3f} (t {tv:+.2f}) info {iV:+.3f} -> {'PASS' if okv else 'FAIL'}"
                f" | OOT {root} 2020-21 n {len(TF)} {mo:+.3f} (t {to:+.2f}) info {io:+.3f} yrs " + "/".join(f"{x:+.3f}" for x in yo) + f" -> {'PASS' if oko else 'FAIL'}")
        if okd and okv and oko:
            h = per(T, HOLD); mh, th = ct(h); line += f" | HOLD n {len(h)} {mh:+.3f} (t {th:+.2f}) -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}"
        else:
            line += " | HOLD sealed"
        print(line)
    print("\nDescriptive: each rule on each regime (net R a trade; DEV / VAL / OOT 2020-21; information over the random control in DEV)")
    for mkt in ("NSDQ", "SP", "DOW"):
        for kind in ("follow", "fade"):
            cells = []
            for reg in ("stress", "calm"):
                T, C = pick(MT5[mkt], kind, reg); d = per(T, DEV); iD, tiD = info(d, per(C, DEV))
                oot = f"{pick(FU[mkt], kind, reg)[0].R.mean():+.3f}" if mkt in FU else "  -  "
                cells.append(f"{reg} {d.R.mean():+.3f}/{per(T, VAL).R.mean():+.3f}/{oot} (n {len(d)}/{len(per(T, VAL))}, info {iD:+.3f} t {tiD:+.2f})")
            print(f"  {mkt:4s} {kind:6s}: " + " | ".join(cells))
    print("\nDescriptive: by VIX band, MT5 2022-25 (net R a trade, n) and futures 2020-21")
    bands = [0, 15, 20, 25, 30, 99]
    for mkt in ("NSDQ", "SP"):
        for kind, X in (("follow", 0), ("fade", 1)):
            T = MT5[mkt][X]; T = T[T.day < "2026-01-01"]; Tf = FU[mkt][X]
            g = T.groupby(pd.cut(T.vix, bands), observed=True).R.agg(["mean", "size"]); gf = Tf.groupby(pd.cut(Tf.vix, bands), observed=True).R.agg(["mean", "size"])
            print(f"  {mkt:4s} {kind:6s} MT5: " + " ".join(f"{iv.left:.0f}-{iv.right:.0f} {r['mean']:+.3f}({int(r['size'])})" for iv, r in g.iterrows())
                  + " | fut: " + " ".join(f"{iv.left:.0f}-{iv.right:.0f} {r['mean']:+.3f}({int(r['size'])})" for iv, r in gf.iterrows()))
    print("\nAccount view (2022-25 trades, from 95,472, MT5 broker rules; pass% / breach% by date):")
    for tr, T in res.items():
        x = T[T.day < "2026-01-01"]
        for risk in (250, 500):
            print(f"  {tr} ${risk}: ({len(x)} trades, {x.R.mean():+.3f} R) {acct(x, risk)}")
    book = pd.concat([res[k] for k in TRIALS]); book = book[book.day < "2026-01-01"]
    print(f"  book V1-V4 $150 a trade: ({len(book)} trades, {book.R.mean():+.3f} R) {acct(book, 150)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
