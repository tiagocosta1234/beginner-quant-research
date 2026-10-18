"""GN3: gold Shanghai-open breakout (A1 both sides, A2 long) and Nasdaq overnight-range breakout after the cash open (O1 both
sides, O2 long), against random entries on the same days. Pre-registration: forex/ea_research/PREREG_GN3.md.
   python -m forex.ea_research.gn3 --dry-run | --run"""
import argparse, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts
from forex.ea_research.orbx import ct
from forex.ea_research.gn1 import per, DEV, VAL, HOLD, NCTRL
from forex.ea_research.gn2 import info

SHA, NYZ = "Asia/Shanghai", "America/New_York"
# trial: market, tz, kind, box start, box end / window start, window end, exit, both sides
TRIALS = {"A1": ("XAUUSD", SHA, "box", (9, 0), (9, 30), (11, 30), (15, 30), True),
          "A2": ("XAUUSD", SHA, "box", (9, 0), (9, 30), (11, 30), (15, 30), False),
          "O1": ("NSDQ", NYZ, "on", (18, 0), (9, 30), (12, 0), (15, 55), True),
          "O2": ("NSDQ", NYZ, "on", (18, 0), (9, 30), (12, 0), (15, 55), False)}
TBAR = 2.24


def trades(trial, D=None, cut=None, diag=False):
    mkt, tz, kind, b0, b1, w1, xh, both = TRIALS[trial]
    D = D if D is not None else load(mkt, cut)
    t = D["t"]; n = len(t); end = cut if cut is not None else int(t[-1]) + 60
    rng = np.random.default_rng(sum(map(ord, trial)) * 104729)
    out, ctrl, elig, lowpos = [], [], [], []
    for d in pd.bdate_range("2022-01-03", "2026-10-16"):
        p = d - pd.Timedelta(days=1)
        s0 = ts(d.year, d.month, d.day, *b0, tz) if kind == "box" else ts(p.year, p.month, p.day, *b0, tz)
        s1, e1, xe = (ts(d.year, d.month, d.day, *hm, tz) for hm in (b1, w1, xh))
        if xe > end:
            continue
        i0, i1, iw, ix = (int(v) for v in np.searchsorted(t, [s0, s1, e1, xe]))
        if i1 - i0 < 0.8 * (s1 - s0) / 60 or iw - i1 < 30 or ix >= n or ix <= i1 + 1:
            continue
        hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min(); W = hi - lo
        if W <= 0:
            continue
        sp = np.median(D["ao"][i0:i1] - D["bo"][i0:i1])
        elig.append((d, W / sp if sp > 0 else np.nan))
        if diag and kind == "on":
            lowpos.append((t[i0 + int(np.argmin(D["bl"][i0:i1]))] - s0) / 60)
        dist = W if kind == "box" else W / 2
        nr = ~D["roll"][i1:iw]
        kl = np.flatnonzero((D["ah"][i1:iw] >= hi) & nr); ks = np.flatnonzero((D["bl"][i1:iw] <= lo) & nr) if both else np.array([], int)
        kl = int(kl[0]) if len(kl) else 1 << 40; ks = int(ks[0]) if len(ks) else 1 << 40
        if kl != ks and min(kl, ks) < 1 << 40:
            side = 1 if kl < ks else -1; k = i1 + min(kl, ks)
            if side == 1:
                e = max(hi, D["ao"][k]); st = lo if kind == "box" else (hi + lo) / 2
            else:
                e = min(lo, D["bo"][k]); st = hi if kind == "box" else (hi + lo) / 2
            if k < ix - 1 and side * (e - st) > 0:
                ex, _ = walk(D, side, k, ix, st, None)
                out.append(dict(trial=trial, day=d, side=side, t_entry=int(t[k]), entry=e, stop=st, R=side * (ex - e) / abs(e - st), W=W))
        cand = np.flatnonzero(nr)
        for j in rng.choice(cand, size=min(NCTRL, len(cand)), replace=False):
            k = i1 + int(j); side = int(rng.choice([1, -1])) if both else 1
            e = D["ao"][k] if side == 1 else D["bo"][k]
            if k < ix - 1:
                ex, _ = walk(D, side, k, ix, e - side * dist, None)
                ctrl.append(dict(trial=trial, day=d, R=side * (ex - e) / dist))
    E = pd.DataFrame(elig, columns=["day", "w_spreads"])
    return (pd.DataFrame(out), pd.DataFrame(ctrl), E, np.array(lowpos)) if diag else (pd.DataFrame(out), pd.DataFrame(ctrl), E)


def dry_run():
    for tr, spec in TRIALS.items():
        T, C, E, lp = trades(tr, diag=True)
        print(f"{tr} {spec[0]} {spec[2]} {'both' if spec[7] else 'long'}: eligible days {len(E)} | trades DEV {len(per(T, DEV))} VAL {len(per(T, VAL))} HOLD {len(per(T, HOLD))}"
              f" | fill {len(T) / max(len(E), 1):.0%} | median width {E.w_spreads.median():.0f} spreads (share < 25: {(E.w_spreads < 25).mean():.0%})"
              + (f" | longs {(T.side == 1).mean():.0%}" if spec[7] and len(T) else ""))
        if len(lp):
            print(f"   overnight-range low set in the first 15 min after 18:00 NY on {(lp < 15).mean():.1%} of days (wide-spread reopen check)")
        for _, r in T.sample(min(2, len(T)), random_state=5).iterrows():
            loc = pd.Timestamp(r.t_entry, unit="s").tz_localize("Europe/Athens").tz_convert(spec[1])
            print(f"   hand check {r.day.date()} side {r.side:+d} entry {r.entry:.2f} at {pd.Timestamp(r.t_entry, unit='s'):%H:%M} server = {loc:%H:%M} local, stop {r.stop:.2f}, width {r.W:.2f}")
    rng = np.random.default_rng(13)
    for tr in ("A1", "O1"):
        T, _, _ = trades(tr); cut = int(rng.uniform(T.t_entry.quantile(.4), T.t_entry.quantile(.8)))
        Tc, _, _ = trades(tr, cut=cut); cd = pd.Timestamp(cut // 86400 * 86400, unit="s") - pd.Timedelta(days=5)
        cols = ["day", "side", "t_entry", "entry", "stop", "R"]
        a = T[T.day < cd][cols].reset_index(drop=True); b = Tc[Tc.day < cd][cols].reset_index(drop=True)
        print(f"truncation {tr}: cut {pd.Timestamp(cut, unit='s')}, trades before {len(a)} vs {len(b)}, identical {a.equals(b)}")


def run():
    from forex.ea_research.usdjpy_account_env import account, HZ
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1627)
    def acct(x, risk):
        Rd = x.groupby("day").R.sum().reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], risk)
        return "  ".join(f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("30 Nov", "22 Dec", "30 Jun 27"))
    res = {}
    for tr, spec in TRIALS.items():
        T, C, _ = trades(tr); res[tr] = T
        d, v, cD, cV = per(T, DEV), per(T, VAL), per(C, DEV), per(C, VAL)
        md, td = ct(d) if len(d) > 2 else (np.nan, np.nan); mv, tv = ct(v) if len(v) > 2 else (np.nan, np.nan)
        iD, tiD = info(d, cD); iV, tiV = info(v, cV)
        yc = d.groupby(d.day.dt.year).R.agg(["mean", "size"])
        ok = len(d) >= 60 and md > 0 and td >= TBAR and iD > 0 and tiD >= 1.65 and (yc["mean"] > 0).sum() >= 2
        okv = ok and mv > 0 and tv >= 1.65 and iV > 0
        sides = ""
        if spec[7]:
            sides = " | DEV longs " + f"{d[d.side == 1].R.mean():+.3f} ({(d.side == 1).sum()}) shorts {d[d.side == -1].R.mean():+.3f} ({(d.side == -1).sum()})"
        line = (f"{tr} {spec[0]}: DEV n {len(d)} {md:+.3f} R (t {td:+.2f}) win {(d.R > 0).mean():.0%} | control {cD.groupby('day').R.mean().mean():+.3f}"
                f" info {iD:+.3f} (t {tiD:+.2f}) | yrs " + "/".join(f"{y}:{r['mean']:+.2f}({int(r['size'])})" for y, r in yc.iterrows())
                + f"{sides} -> {'PASS' if ok else 'FAIL'} | VAL n {len(v)} {mv:+.3f} (t {tv:+.2f}) control {cV.groupby('day').R.mean().mean():+.3f} info {iV:+.3f}")
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
