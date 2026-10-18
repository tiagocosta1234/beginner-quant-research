"""GN1: gold and Nasdaq breakouts, long-only in the 200-day uptrend, against a drift control (random long, same window, same stop
distance, same exit). Pre-registration: forex/ea_research/PREREG_GN1.md.   --dry-run: counts, truncation test, hand check.   --run"""
import argparse, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts
from forex.ea_research.orbx import ct

LDN, NYZ = "Europe/London", "America/New_York"
DEV, VAL, HOLD = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-10-17")
# trial: market, box tz, box start/end, window end, exit (h, m), exit day offset, regime close (tz, h, m)
TRIALS = {"G1": ("XAUUSD", LDN, (8, 0), (8, 30), (11, 0), (17, 0), 0, (LDN, 17, 0)),
          "G2": ("XAUUSD", LDN, (8, 0), (8, 30), (11, 0), (17, 0), 1, (LDN, 17, 0)),
          "G3": ("XAUUSD", NYZ, (9, 30), (10, 0), (12, 0), (16, 0), 0, (LDN, 17, 0)),
          "N1": ("NSDQ", NYZ, (9, 30), (10, 0), (12, 0), (15, 55), 0, (NYZ, 16, 0)),
          "N2": ("NSDQ", NYZ, (9, 30), (10, 0), (12, 0), (15, 55), 1, (NYZ, 16, 0))}
NCTRL = 5


def regime(D, tz, h, m):
    """per local date: the mid close at h:m (last minute before it) and whether the PREVIOUS day's close was above the SMA200
    of closes up to that previous day"""
    t = D["t"]; mc = (D["bc"] + D["ac"]) / 2
    loc = pd.to_datetime(t, unit="s").tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").tz_convert(tz)
    dates = pd.DatetimeIndex(loc.tz_localize(None).normalize()).dropna().unique()
    rows = []
    for d in dates:
        if d.weekday() >= 5:
            continue
        x = ts(d.year, d.month, d.day, h, m, tz); j = int(np.searchsorted(t, x)) - 1
        if j >= 0 and x - t[j] <= 1800:
            rows.append((d, mc[j]))
    R = pd.DataFrame(rows, columns=["date", "close"]).set_index("date")
    R["sma200"] = R.close.rolling(200, min_periods=200).mean()
    R["on"] = (R.close.shift(1) > R.sma200.shift(1))
    return R


def trades(sym, trial, D=None, cut=None, rng_seed=0):
    mkt, tz, b0, b1, w1, xh, xoff, (rtz, rh, rm) = TRIALS[trial]
    D = D if D is not None else load(sym if sym else mkt, cut)
    t = D["t"]; n = len(t); end = cut if cut is not None else int(t[-1]) + 60
    R = regime(D, rtz, rh, rm); days = R.index
    rng = np.random.default_rng(rng_seed or sum(map(ord, trial)) * 31337)
    out, ctrl = [], []
    for i, d in enumerate(days):
        if not R.on.iat[i] or d < pd.Timestamp("2022-01-01"):
            continue
        xd = days[i + xoff] if i + xoff < len(days) else None
        if xd is None:
            continue
        s0, s1, e1 = ts(d.year, d.month, d.day, *b0, tz), ts(d.year, d.month, d.day, *b1, tz), ts(d.year, d.month, d.day, *w1, tz)
        xe = ts(xd.year, xd.month, xd.day, *xh, tz)
        if xe > end:
            continue
        i0, i1, iw, ix = np.searchsorted(t, [s0, s1, e1, xe])
        if i1 - i0 < 24 or iw - i1 < 30 or ix >= n or ix <= i1 + 1:
            continue
        hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); W = hi - lo
        if W <= 0:
            continue
        nr = ~D["roll"][i1:iw]
        up = np.flatnonzero((D["ah"][i1:iw] >= hi) & nr)
        if len(up):
            k = i1 + int(up[0]); e = max(hi, D["ao"][k])
            if k < ix - 1 and e > lo:
                ex, _ = walk(D, 1, k, ix, lo, None)
                out.append(dict(trial=trial, day=d, t_entry=int(t[k]), entry=e, stop=lo, R=(ex - e) / (e - lo), W=W))
        cand = np.flatnonzero(nr)
        for j in rng.choice(cand, size=min(NCTRL, len(cand)), replace=False):
            k = i1 + int(j); e = D["ao"][k]; st = e - W
            if k < ix - 1:
                ex, _ = walk(D, 1, k, ix, st, None)
                ctrl.append(dict(trial=trial, day=d, R=(ex - e) / W))
    return pd.DataFrame(out), pd.DataFrame(ctrl), R


def per(x, p):
    return x[(x.day >= p[0]) & (x.day < p[1])]


def paired(T, C):
    c = C.groupby("day").R.mean().rename("Rc")
    m = T.merge(c, left_on="day", right_index=True, how="inner")
    dd = m.assign(R=m.R - m.Rc)
    return ct(dd) if len(dd) > 2 else (np.nan, np.nan), m


def dry_run():
    for tr, spec in TRIALS.items():
        T, C, R = trades(None, tr)
        on = R[(R.index >= "2022-01-01")].on.mean()
        print(f"{tr} {spec[0]}: trades DEV {len(per(T, DEV))} VAL {len(per(T, VAL))} HOLD {len(per(T, HOLD))} | control draws DEV {len(per(C, DEV))}"
              f" | regime ON {on:.0%} of days since 2022 | median box {T.W.median() if len(T) else float('nan'):.2f}")
        if len(T):
            for _, r in T.sample(min(2, len(T)), random_state=4).iterrows():
                print(f"   hand check {r.day.date()} entry {r.entry:.2f} at {pd.Timestamp(r.t_entry, unit='s'):%H:%M} server, stop {r.stop:.2f}, box {r.W:.2f}")
    rng = np.random.default_rng(9)
    for tr in ("G1", "N2"):
        T, _, _ = trades(None, tr)
        cut = int(rng.uniform(T.t_entry.quantile(.4), T.t_entry.quantile(.8)))
        Tc, _, _ = trades(None, tr, cut=cut)
        cd = pd.Timestamp(cut // 86400 * 86400, unit="s") - pd.Timedelta(days=5)
        a = T[T.day < cd][["day", "t_entry", "entry", "stop", "R"]].reset_index(drop=True); b = Tc[Tc.day < cd][["day", "t_entry", "entry", "stop", "R"]].reset_index(drop=True)
        print(f"truncation {tr}: cut {pd.Timestamp(cut, unit='s')}, trades before the cut {len(a)} vs {len(b)}, identical {a.equals(b)}")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    res = {}
    for tr in TRIALS:
        T, C, _ = trades(None, tr); res[tr] = (T, C)
        d, v = per(T, DEV), per(T, VAL)
        md, td = ct(d) if len(d) > 2 else (np.nan, np.nan); mv, tv = ct(v) if len(v) > 2 else (np.nan, np.nan)
        (mi, ti), _ = paired(d, per(C, DEV)); (miv, tiv), _ = paired(v, per(C, VAL))
        yrs = d.groupby(d.day.dt.year).R.mean()
        ok = len(d) >= 150 and md > 0 and td >= 2.33 and mi > 0 and ti >= 2.0 and (yrs > 0).sum() >= 2
        okv = ok and mv > 0 and tv >= 1.65 and miv > 0
        line = (f"{tr} DEV n {len(d)} {md:+.3f} R (t {td:+.2f}) win {(d.R > 0).mean():.0%} | control {per(C, DEV).R.mean():+.3f} | info {mi:+.3f} (t {ti:+.2f})"
                f" | yrs {'/'.join(f'{y:+.2f}' for y in yrs)} -> {'PASS' if ok else 'FAIL'} | VAL n {len(v)} {mv:+.3f} (t {tv:+.2f}) control {per(C, VAL).R.mean():+.3f} info {miv:+.3f}")
        if okv:
            h = per(T, HOLD); mh, th = ct(h); line += f" | HOLD n {len(h)} {mh:+.3f} (t {th:+.2f}) -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}"
        else:
            line += " | HOLD sealed"
        print(line)
    print("\nAccount view (2022-25 trades, from 95,472, MT5 broker rules; pass% / breach%):")
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1627)
    def acct(x, risk):
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], risk)
        return "  ".join(f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("30 Nov", "22 Dec", "30 Jun 27"))
    for tr, (T, C) in res.items():
        x = T[T.day < "2026-01-01"]
        for risk in (250, 500):
            print(f"  {tr} ${risk}: ({len(x)} trades, {x.R.mean():+.3f} R) {acct(x, risk)}")
    for a_, b_ in (("G1", "N1"), ("G2", "N2")):
        x = pd.concat([res[a_][0], res[b_][0]]); x = x[x.day < "2026-01-01"]
        print(f"  pair {a_}+{b_} $250: ({len(x)} trades, {x.R.mean():+.3f} R) {acct(x, 250)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
