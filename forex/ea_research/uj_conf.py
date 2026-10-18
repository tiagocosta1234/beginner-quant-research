"""UJ_CONF: 9 pre-registered confluences for the USDJPY London-open breakout at today's cost (PREREG_UJ_CONF.md).
   python -m forex.ea_research.uj_conf"""
import numpy as np, pandas as pd
from forex.ea_research.crt import load
from forex.ea_research.breakouts import local_clock
from forex.ea_research.brk_exits import exits
from forex.ea_research.usdjpy_sens import run as sens_run
from forex.ea_research.usdjpy_spreadfix import zero_fix, respread, END
from forex.ea_research.brk50 import Mkt, ts, LIS
from forex.ea_research.brk_fvg import fvgs
from forex.ea_research.orbx import ct

H, M_ = 3600, 60
FL = ["C1_beyond_asia", "C2_trend20", "C3_risk_on", "C4_usd_wide", "C5_fvg", "C6_not_small_box", "C7_late_trigger", "C8_not_stretched", "C9_asia_aligned"]


def trades():
    D = load("USDJPY", END); lc = local_clock(D["t"], "Europe/London")
    E = respread(D, np.maximum(zero_fix(D), 0.006))
    t = E["t"]; mh, ml, mc = E["mh"], E["ml"], E["mc"]
    base = sens_run(E, lc, 8, 30, 17)                                   # the registered engine, for the reproduction check
    U = Mkt("USDJPY"); Dd = U.Dd.copy(); Dd["sma20"] = Dd.C.shift(1).rolling(20, min_periods=15).mean()
    Dd["r5"] = Dd.C.shift(1) - Dd.C.shift(6)
    N, EU, GU = Mkt("NSDQ"), Mkt("EURUSD"), Mkt("GBPUSD")
    F = fvgs(E); fo = F.formed.to_numpy(); out = []
    for d in np.unique(lc // 86400):
        base_ = d * 86400
        i0, i1 = np.searchsorted(lc, base_ + 8 * H), np.searchsorted(lc, base_ + 8 * H + 30 * M_)
        w1, xe = np.searchsorted(lc, base_ + 8 * H + 30 * M_ + 150 * M_), np.searchsorted(lc, base_ + 17 * H)
        if xe >= len(lc) or i1 - i0 < 30 * 0.6 or lc[i0] // 86400 != d or w1 <= i1 + 30 or (t[min(xe, len(lc) - 1)] % 86400) // H in (23, 0):
            continue
        Hb, Lb = E["bh"][i0:i1].max(), E["bl"][i0:i1].min()
        up = np.flatnonzero(E["ah"][i1:w1] >= Hb); dn = np.flatnonzero(E["bl"][i1:w1] <= Lb)
        ku = i1 + up[0] if len(up) else None; kd = i1 + dn[0] if len(dn) else None
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        e = max(Hb, E["ao"][k]) if side > 0 else min(Lb, E["bo"][k])
        R = abs(e - (Lb if side > 0 else Hb))
        if k >= xe or not (R > 0 and R >= 2 * (E["ao"][k] - E["bo"][k])):
            continue
        x = exits(E, k, xe, side, e, R)
        if not x:
            continue
        day = pd.Timestamp(base_, unit="s")
        sday = int(t[i0]) // 86400; p = U.pos.get(sday)
        if p is None or p < 6:
            continue
        r_, y = Dd.iloc[p], Dd.iloc[p - 1]; atr = r_.atr
        # Asian range 00:00-07:00 London (local clock)
        a0, a1 = np.searchsorted(lc, base_), np.searchsorted(lc, base_ + 7 * H)
        if a1 - a0 < 120 or not (atr > 0):
            continue
        asia_h, asia_l = mh[a0:a1].max(), ml[a0:a1].min()
        t0800, t0830 = int(t[i0]), int(t[i1]); t0000 = int(t[a0]); s01 = sday * 86400 + H
        nq = N.mid_at(t0800) - N.mid_at(s01)
        eu = (EU.mid_at(t0830) / EU.mid_at(t0000) - 1); gu = (GU.mid_at(t0830) / GU.mid_at(t0000) - 1); usd = -(eu + gu) / 2
        d0 = ts(day.year, day.month, day.day, 0, 0, LIS)
        a_, b_ = np.searchsorted(fo, d0), np.searchsorted(fo, int(t[k]), side="right")
        cand = F.iloc[a_:b_]; spb = np.median(E["ao"][i0:i1] - E["bo"][i0:i1])
        cand = cand[(cand.kind == side) & (cand.bot >= Lb) & (cand.top <= Hb) & ((cand.top - cand.bot) >= spb)]
        fvg = False
        for g in cand.itertuples():
            j0 = int(np.searchsorted(t, g.formed))
            if j0 >= k or ((ml[j0:k].min() >= g.top) if side > 0 else (mh[j0:k].max() <= g.bot)):
                fvg = True; break
        out.append(dict(day=day, side=side, R=x[3], box_atr=(Hb - Lb) / atr,
                        C1_beyond_asia=bool(Hb > asia_h if side > 0 else Lb < asia_l), C2_trend20=bool(side * (y.C - r_.sma20) > 0),
                        C3_risk_on=bool(np.isfinite(nq) and np.sign(nq) == side), C4_usd_wide=bool(np.isfinite(usd) and np.sign(usd) == side),
                        C5_fvg=fvg, C7_late_trigger=bool((lc[k] - (base_ + 8 * H + 30 * M_)) // 60 > 8),
                        C8_not_stretched=bool(side * r_.r5 / atr < 0.59), C9_asia_aligned=bool(side * (mc[i0] - mc[a0]) > 0)))
    T = pd.DataFrame(out); T = T[T.day >= "2022-01-01"].reset_index(drop=True)
    q33 = T[T.day < "2025-01-01"].box_atr.quantile(1 / 3); T["C6_not_small_box"] = T.box_atr >= q33
    b = base[base.day >= "2022-01-01"]
    return T, q33, b


def welch(a, b):
    if len(a) < 2 or len(b) < 2:
        return np.nan
    se = np.sqrt(a.var() / len(a) + b.var() / len(b)); return (a.mean() - b.mean()) / se if se > 0 else np.nan


def main():
    from forex.ea_research.usdjpy_account_env import account, HZ
    T, q33, b = trades()
    chk = T.merge(b, on="day", suffixes=("", "_b"))
    print(f"reproduction vs usdjpy_sens.run: {len(T)} trades here vs {len(b)} there; matched days {len(chk)}, max |dR| {np.abs(chk.R - chk.R_b).max():.2e}")
    dev, val = T[T.day < "2025-01-01"], T[(T.day >= "2025-01-01") & (T.day < "2026-01-01")]
    print(f"base: DEV n {len(dev)} {dev.R.mean():+.3f} R, VAL n {len(val)} {val.R.mean():+.3f} R; C6 cut box/ATR >= {q33:.3f}\n")
    kept = []
    for c in FL:
        w, wo = dev[dev[c]], dev[~dev[c]]; tt = welch(w.R, wo.R)
        keep = len(w) >= 150 and w.R.mean() > 0 and w.R.mean() > wo.R.mean() and tt >= 2.0
        kept += [c] if keep else []
        vw, vwo = val[val[c]], val[~val[c]]
        print(f"{c:18s} DEV with n {len(w):3d} {w.R.mean():+.3f} | without n {len(wo):3d} {wo.R.mean():+.3f} | t {tt:+.2f} -> {'KEEP' if keep else 'drop'}"
              f"   (VAL descriptive: with {vw.R.mean():+.3f} n {len(vw)} / without {vwo.R.mean():+.3f})")
    print("\nkept on DEV:", kept or "none")
    rule = lambda X: X[np.logical_and.reduce([X[c] for c in kept])] if kept else X
    rd, rv = rule(dev), rule(val); md, td = ct(rd); mv, tv = ct(rv)
    print(f"combined rule ({' AND '.join(kept) if kept else 'base'}): DEV n {len(rd)} {md:+.3f} (t {td:+.2f}) | VAL n {len(rv)} {mv:+.3f} (t {tv:+.2f}) vs base VAL {val.R.mean():+.3f}")
    if kept and mv > 0 and tv >= 1.65 and mv > val.R.mean():
        h = rule(T[T.day >= "2026-01-01"]); mh, th = ct(h)
        print(f"HOLD 2026 (one look): n {len(h)} {mh:+.3f} (t {th:+.2f}) -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}")
    else:
        print("VAL confirmation failed or nothing kept: HOLD 2026 not used for the subsets")
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1624)
    x = rule(T[T.day < "2026-01-01"])
    for hc in (0.0, 0.06):
        Rd = x.set_index("day").R.reindex(days) - hc; trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        for risk in (150, 250):
            st, ev, _ = account(r[bi], trd[bi], risk)
            print(f"account USDJPY ${risk} haircut {hc} ({len(x)} trades 2022-25, {x.R.mean() - hc:+.3f} R): " + "  ".join(
                f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("22 Dec", "31 Mar 27", "30 Jun 27")))


if __name__ == "__main__":
    main()
