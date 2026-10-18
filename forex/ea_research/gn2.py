"""GN2: gold and Nasdaq long breakouts on the day after a pullback (uptrend + down day / 3-day pullback) or a dip (z3 <= -1.5),
against random longs on the same days and against the GN1 base. Pre-registration: forex/ea_research/PREREG_GN2.md.
   python -m forex.ea_research.gn2 --dry-run | --run"""
import argparse, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts
from forex.ea_research.orbx import ct
from forex.ea_research.gn1 import regime, per, LDN, NYZ, DEV, VAL, HOLD, NCTRL, trades as gn1_trades

SESS = {"XAUUSD": (LDN, (8, 0), (8, 30), (11, 0), (17, 0), (LDN, 17, 0)),
        "NSDQ": (NYZ, (9, 30), (10, 0), (12, 0), (15, 55), (NYZ, 16, 0))}
TRIALS = {"P1": ("XAUUSD", "down"), "P2": ("NSDQ", "down"), "P3": ("XAUUSD", "pull3"), "P4": ("NSDQ", "pull3"),
          "P5": ("XAUUSD", "dip"), "P6": ("NSDQ", "dip")}
BASE = {"XAUUSD": "G1", "NSDQ": "N1"}
# amendment 1 (before any P&L): P3+P4 and P5+P6 pooled; the registered trials are P1, P2, P34, P56 (Bonferroni t >= 2.24)
POOLED = {"P1": ("P1",), "P2": ("P2",), "P34": ("P3", "P4"), "P56": ("P5", "P6")}
TBAR = 2.24


def conditions(R):
    c = R.close; r1 = c.pct_change(); sd = r1.rolling(60, min_periods=40).std()
    z3 = np.log(c / c.shift(3)) / (sd * np.sqrt(3)); up = c > R.sma200
    prev = lambda s: s.shift(1).fillna(False).astype(bool)
    return {"down": prev(up & (r1 < 0)), "pull3": prev(up & (z3 <= -1.0)), "dip": prev(z3 <= -1.5)}


def trades(trial, D=None, cut=None):
    mkt, kind = TRIALS[trial]; tz, b0, b1, w1, xh, (rtz, rh, rm) = SESS[mkt]
    D = D if D is not None else load(mkt, cut)
    t = D["t"]; n = len(t); end = cut if cut is not None else int(t[-1]) + 60
    R = regime(D, rtz, rh, rm); cond = conditions(R)[kind]
    rng = np.random.default_rng(sum(map(ord, trial)) * 7919)
    out, ctrl, ndays = [], [], []
    for d, on in cond.items():
        if not on or d < pd.Timestamp("2022-01-01"):
            continue
        s0, s1, e1, xe = (ts(d.year, d.month, d.day, *hm, tz) for hm in (b0, b1, w1, xh))
        if xe > end:
            continue
        i0, i1, iw, ix = np.searchsorted(t, [s0, s1, e1, xe])
        if i1 - i0 < 24 or iw - i1 < 30 or ix >= n or ix <= i1 + 1:
            continue
        hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); W = hi - lo
        if W <= 0:
            continue
        ndays.append(d)
        nr = ~D["roll"][i1:iw]
        up = np.flatnonzero((D["ah"][i1:iw] >= hi) & nr)
        if len(up):
            k = i1 + int(up[0]); e = max(hi, D["ao"][k])
            if k < ix - 1 and e > lo:
                ex, _ = walk(D, 1, k, ix, lo, None)
                out.append(dict(trial=trial, day=d, t_entry=int(t[k]), entry=e, stop=lo, R=(ex - e) / (e - lo), W=W))
        cand = np.flatnonzero(nr)
        for j in rng.choice(cand, size=min(NCTRL, len(cand)), replace=False):
            k = i1 + int(j); e = D["ao"][k]
            if k < ix - 1:
                ex, _ = walk(D, 1, k, ix, e - W, None)
                ctrl.append(dict(trial=trial, day=d, R=(ex - e) / W))
    return pd.DataFrame(out), pd.DataFrame(ctrl), pd.DatetimeIndex(ndays)


def info(T, C):
    if len(T) < 3 or len(C) < 3:
        return np.nan, np.nan
    m1, t1 = ct(T); se1 = abs(m1 / t1) if t1 else np.nan
    cd = C.groupby("day").R.mean(); se2 = cd.std(ddof=1) / np.sqrt(len(cd))
    diff = m1 - cd.mean(); return diff, diff / np.sqrt(se1 ** 2 + se2 ** 2)


def dry_run():
    for tr, (mkt, kind) in TRIALS.items():
        T, C, nd = trades(tr)
        print(f"{tr} {mkt} {kind}: condition days DEV {((nd >= DEV[0]) & (nd < DEV[1])).sum()} VAL {((nd >= VAL[0]) & (nd < VAL[1])).sum()}"
              f" HOLD {((nd >= HOLD[0]) & (nd < HOLD[1])).sum()} | breakout trades DEV {len(per(T, DEV))} VAL {len(per(T, VAL))} HOLD {len(per(T, HOLD))}"
              f" | fill rate {len(T) / max(len(nd), 1):.0%}")
        for _, r in T.sample(min(2, len(T)), random_state=7).iterrows():
            print(f"   hand check {r.day.date()} entry {r.entry:.2f} at {pd.Timestamp(r.t_entry, unit='s'):%H:%M} server, stop {r.stop:.2f}, box {r.W:.2f}")
    rng = np.random.default_rng(11)
    for tr in ("P1", "P6"):
        T, _, _ = trades(tr); cut = int(rng.uniform(T.t_entry.quantile(.4), T.t_entry.quantile(.8)))
        Tc, _, _ = trades(tr, cut=cut); cd = pd.Timestamp(cut // 86400 * 86400, unit="s") - pd.Timedelta(days=5)
        cols = ["day", "t_entry", "entry", "stop", "R"]
        a = T[T.day < cd][cols].reset_index(drop=True); b = Tc[Tc.day < cd][cols].reset_index(drop=True)
        print(f"truncation {tr}: cut {pd.Timestamp(cut, unit='s')}, trades before {len(a)} vs {len(b)}, identical {a.equals(b)}")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    base = {m: gn1_trades(None, b)[0] for m, b in BASE.items()}
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1627)
    def acct(x, risk):
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], risk)
        return "  ".join(f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("30 Nov", "22 Dec", "30 Jun 27"))
    res, single = {}, {tr: trades(tr) for tr in TRIALS}
    for tr, parts in list(POOLED.items()) + [(p, (p,)) for p in ("P3", "P4", "P5", "P6")]:
        T = pd.concat([single[p][0] for p in parts], ignore_index=True); C = pd.concat([single[p][1] for p in parts], ignore_index=True)
        mk = sorted({TRIALS[p][0] for p in parts}); kind = TRIALS[parts[0]][1]; mkt = "+".join(mk)
        if tr in POOLED:
            res[tr] = T
        else:
            mkt += " (descriptive)"
        B = pd.concat([base[m] for m in mk], ignore_index=True)
        d, v, cD, cV = per(T, DEV), per(T, VAL), per(C, DEV), per(C, VAL)
        md, td = ct(d) if len(d) > 2 else (np.nan, np.nan); mv, tv = ct(v) if len(v) > 2 else (np.nan, np.nan)
        iD, tiD = info(d, cD); iV, tiV = info(v, cV)
        bD = per(B, DEV).R.mean(); bV = per(B, VAL).R.mean()
        yc = d.groupby(d.day.dt.year).R.agg(["mean", "size"]); yq = yc[yc["size"] >= 15]
        ok = len(d) >= 60 and md > 0 and td >= TBAR and iD > 0 and tiD >= 1.65 and md - bD > 0 and (yq["mean"] > 0).sum() >= 2 and tr in POOLED
        okv = ok and mv > 0 and tv >= 1.65 and iV > 0
        line = (f"{tr} {mkt} {kind}: DEV n {len(d)} {md:+.3f} R (t {td:+.2f}) win {(d.R > 0).mean():.0%} | control {cD.groupby('day').R.mean().mean():+.3f}"
                f" info {iD:+.3f} (t {tiD:+.2f}) | vs GN1 base {md - bD:+.3f} | yrs " + "/".join(f"{y}:{r['mean']:+.2f}({int(r['size'])})" for y, r in yc.iterrows())
                + f" -> {'PASS' if ok else 'FAIL'} | VAL n {len(v)} {mv:+.3f} (t {tv:+.2f}) info {iV:+.3f} vs base {mv - bV:+.3f}")
        if okv:
            h = per(T, HOLD); mh, th = ct(h); line += f" | HOLD n {len(h)} {mh:+.3f} (t {th:+.2f}) -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}"
        else:
            line += " | HOLD sealed"
        print(line)
    print("\nAccount view (2022-25 trades, from 95,472, MT5 broker rules; pass% / breach% by date):")
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
