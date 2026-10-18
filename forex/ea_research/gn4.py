"""GN4: market-profile value-area rules on Nasdaq and gold: V1 / V2 acceptance breakout (open inside yesterday's value, a 30-min
period closes outside -> follow, stop at yesterday's POC), V3 / V4 80% rule (open outside value, two 30-min closes back inside
-> trade to the other edge). Pre-registration: forex/ea_research/PREREG_GN4.md.   python -m forex.ea_research.gn4 --dry-run | --run"""
import argparse, numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts
from forex.ea_research.orbx import ct
from forex.ea_research.gn1 import per, DEV, VAL, HOLD, NCTRL
from forex.ea_research.gn2 import info

NYZ = "America/New_York"
MK = {"NSDQ": dict(s=(9, 30), e=(16, 0), acc=(12, 0), r80=(13, 0), x=(15, 55)),
      "XAUUSD": dict(s=(8, 20), e=(13, 30), acc=(11, 20), r80=(12, 20), x=(13, 25))}
TRIALS = {"V1": ("NSDQ", "acc"), "V2": ("XAUUSD", "acc"), "V3": ("NSDQ", "r80"), "V4": ("XAUUSD", "r80")}
TBAR = 2.24


def profile(mid):
    """POC, VAL, VAH of a session from its minute mids: 100 equal bins, POC = most minutes (ties nearest the mid), value area
    grown from the POC by the neighbour bin with more minutes until >= 70%"""
    lo, hi = float(mid.min()), float(mid.max())
    if hi <= lo:
        return None
    edges = np.linspace(lo, hi, 101); cnt, _ = np.histogram(mid, bins=edges); cen = (edges[:-1] + edges[1:]) / 2
    c = np.flatnonzero(cnt == cnt.max()); poc = int(c[np.argmin(np.abs(cen[c] - (lo + hi) / 2))])
    a = b = poc; s = cnt[poc]; tot = cnt.sum()
    while s < 0.7 * tot:
        up = cnt[b + 1] if b + 1 < 100 else -1; dn = cnt[a - 1] if a >= 1 else -1
        if up > dn:
            b += 1; s += up
        elif dn > up:
            a -= 1; s += dn
        else:
            if up < 0:
                break
            a -= 1; b += 1; s += up + dn
    return cen[poc], edges[a], edges[b + 1]


def sessions(D, m):
    t = D["t"]; p = MK[m]; out = []
    for d in pd.bdate_range("2021-12-20", "2026-10-16"):
        s0, s1 = ts(d.year, d.month, d.day, *p["s"], NYZ), ts(d.year, d.month, d.day, *p["e"], NYZ)
        i0, i1 = (int(v) for v in np.searchsorted(t, [s0, s1]))
        if i1 - i0 >= 0.8 * (s1 - s0) / 60 and i0 < len(t) and t[i0] - s0 < 300:
            out.append((d, s0, i0, i1))
    return out


def trades(trial, D=None, cut=None, diag=False):
    m, kind = TRIALS[trial]; p = MK[m]
    D = D if D is not None else load(m, cut)
    t = D["t"]; n = len(t); end = cut if cut is not None else int(t[-1]) + 60; mid = (D["bc"] + D["ac"]) / 2
    rng = np.random.default_rng(sum(map(ord, trial)) * 15485863)
    S = sessions(D, m); out, ctrl, cond, prof = [], [], [], []
    for (pd_, ps0, pi0, pi1), (d, s0, i0, i1) in zip(S[:-1], S[1:]):
        if d < pd.Timestamp("2022-01-01") or (d - pd_).days > 5:
            continue
        pr = profile(mid[pi0:pi1])
        if pr is None:
            continue
        poc, val, vah = pr; vaw = vah - val
        we = ts(d.year, d.month, d.day, *p[kind], NYZ); xe = ts(d.year, d.month, d.day, *p["x"], NYZ)
        if xe > end:
            continue
        ix = int(np.searchsorted(t, xe))
        if ix >= n or vaw <= 0:
            continue
        op = mid[i0]; inside = val <= op <= vah
        if kind == "acc" and not inside or kind == "r80" and inside:
            continue
        sp = np.median(D["ao"][pi0:pi1] - D["bo"][pi0:pi1])
        cond.append((d, vaw / sp if sp > 0 else np.nan, inside)); prof.append((d, poc, val, vah, float(np.mean((mid[pi0:pi1] >= val) & (mid[pi0:pi1] <= vah)))))
        np_ = int((we - s0) // 1800); closes, ends = [], []
        for k in range(np_):
            pe = s0 + 1800 * (k + 1); j = int(np.searchsorted(t, pe)) - 1
            closes.append(mid[j] if j >= i0 and t[j] >= pe - 1800 else np.nan); ends.append(pe)
        sig = None
        if kind == "acc":
            for k, c in enumerate(closes):
                if c > vah or c < val:
                    sig = (k, 1 if c > vah else -1); break
        else:
            for k in range(1, np_):
                if val <= closes[k - 1] <= vah and val <= closes[k] <= vah:
                    sig = (k, -1 if op > vah else 1); break
        if sig is not None:
            k, side = sig; f = int(np.searchsorted(t, ends[k]))
            if f < ix - 1 and t[f] - ends[k] < 300 and not D["roll"][f]:
                e = D["ao"][f] if side == 1 else D["bo"][f]
                if kind == "acc":
                    st, tp = poc, None
                else:
                    ext = D["bh"][i0:f].max() if side == -1 else D["bl"][i0:f].min()
                    st = max(ext, e + 0.25 * vaw) if side == -1 else min(ext, e - 0.25 * vaw); tp = val if side == -1 else vah
                    if side * (tp - e) <= 0:
                        st = None
                if st is not None and side * (e - st) > 0:
                    ex, xk = walk(D, side, f, ix, st, tp)
                    out.append(dict(trial=trial, day=d, side=side, t_entry=int(t[f]), entry=e, stop=st, R=side * (ex - e) / abs(e - st),
                                    hit_tp=bool(tp is not None and side * (ex - tp) >= 0), vaw=vaw))
        ws = s0 + (1800 if kind == "acc" else 3600); a0, a1 = (int(v) for v in np.searchsorted(t, [ws, we]))
        cand = np.flatnonzero(~D["roll"][a0:a1])
        for j in rng.choice(cand, size=min(NCTRL, len(cand)), replace=False) if len(cand) else []:
            f = a0 + int(j); side = int(rng.choice([1, -1])); e = D["ao"][f] if side == 1 else D["bo"][f]
            if kind == "acc":
                dist = max(abs(e - poc), 0.25 * vaw); tp = None
            else:
                dist = 0.25 * vaw; tg = vah if side == 1 else val; tp = tg if side * (tg - e) > 0 else None
            if f < ix - 1:
                ex, _ = walk(D, side, f, ix, e - side * dist, tp)
                ctrl.append(dict(trial=trial, day=d, R=side * (ex - e) / dist))
    T, C = pd.DataFrame(out), pd.DataFrame(ctrl)
    if diag:
        return T, C, pd.DataFrame(cond, columns=["day", "va_spreads", "inside"]), pd.DataFrame(prof, columns=["day", "poc", "val", "vah", "share_in"])
    return T, C


def dry_run():
    for tr, (m, kind) in TRIALS.items():
        T, C, K, P = trades(tr, diag=True)
        print(f"{tr} {m} {kind}: condition days {len(K)} (DEV {len(per(K, DEV))}) | trades DEV {len(per(T, DEV))} VAL {len(per(T, VAL))} HOLD {len(per(T, HOLD))}"
              f" | fire rate {len(T) / max(len(K), 1):.0%} | median VA width {K.va_spreads.median():.0f} spreads | VA holds {P.share_in.min():.0%}-{P.share_in.max():.0%} of minutes"
              + (f" | longs {(T.side == 1).mean():.0%}" if len(T) else ""))
        for _, r in T.sample(min(2, len(T)), random_state=3).iterrows():
            q = P[P.day == r.day].iloc[0]
            print(f"   hand check {r.day.date()} side {r.side:+d} entry {r.entry:.2f} at {pd.Timestamp(r.t_entry, unit='s'):%H:%M} server, stop {r.stop:.2f}"
                  f" | yesterday POC {q.poc:.2f} VAL {q.val:.2f} VAH {q.vah:.2f}")
    # hand check of one profile by an independent route: sorted-bin share and POC count
    D = load("NSDQ"); mid = (D["bc"] + D["ac"]) / 2; S = sessions(D, "NSDQ"); d, s0, i0, i1 = S[400]
    x = mid[i0:i1]; poc, val, vah = profile(x); cnt, ed = np.histogram(x, bins=np.linspace(x.min(), x.max(), 101))
    print(f"profile hand check NSDQ {d.date()}: {i1 - i0} minutes, range {x.min():.1f}-{x.max():.1f}, POC {poc:.1f} (bin count {cnt.max()}, "
          f"POC bin count {cnt[np.searchsorted(ed, poc) - 1]}), VA {val:.1f}-{vah:.1f} holds {np.mean((x >= val) & (x <= vah)):.1%} of minutes")
    rng = np.random.default_rng(17)
    for tr in ("V1", "V4"):
        T, _ = trades(tr); cut = int(rng.uniform(T.t_entry.quantile(.4), T.t_entry.quantile(.8)))
        Tc, _ = trades(tr, cut=cut); cd = pd.Timestamp(cut // 86400 * 86400, unit="s") - pd.Timedelta(days=5)
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
    for tr, (m, kind) in TRIALS.items():
        T, C = trades(tr); res[tr] = T
        d, v, cD, cV = per(T, DEV), per(T, VAL), per(C, DEV), per(C, VAL)
        md, td = ct(d) if len(d) > 2 else (np.nan, np.nan); mv, tv = ct(v) if len(v) > 2 else (np.nan, np.nan)
        iD, tiD = info(d, cD); iV, tiV = info(v, cV)
        yc = d.groupby(d.day.dt.year).R.agg(["mean", "size"])
        ok = len(d) >= 60 and md > 0 and td >= TBAR and iD > 0 and tiD >= 1.65 and (yc["mean"] > 0).sum() >= 2
        okv = ok and mv > 0 and tv >= 1.65 and iV > 0
        extra = f" | target hit {d.hit_tp.mean():.0%}" if kind == "r80" else ""
        line = (f"{tr} {m} {kind}: DEV n {len(d)} {md:+.3f} R (t {td:+.2f}) win {(d.R > 0).mean():.0%} | control {cD.groupby('day').R.mean().mean():+.3f}"
                f" info {iD:+.3f} (t {tiD:+.2f}) | yrs " + "/".join(f"{y}:{r['mean']:+.2f}({int(r['size'])})" for y, r in yc.iterrows())
                + f" | longs {d[d.side == 1].R.mean():+.3f} ({(d.side == 1).sum()}) shorts {d[d.side == -1].R.mean():+.3f} ({(d.side == -1).sum()}){extra}"
                + f" -> {'PASS' if ok else 'FAIL'} | VAL n {len(v)} {mv:+.3f} (t {tv:+.2f}) info {iV:+.3f}")
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
