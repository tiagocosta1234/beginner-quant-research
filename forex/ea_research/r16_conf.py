"""R16_CONF: 8 pre-registered confluences for reel 16's NY-box breakout (trader 1) on MT5 NSDQ (PREREG_R16_CONF.md).
Selection on DEV 2022-24, confirmation on VAL 2025, HOLD 2026 only if the combined rule passes.   python -m forex.ea_research.r16_conf"""
import numpy as np, pandas as pd
from forex.ea_research.brk50 import Mkt, ts, NYZ, LIS
from forex.ea_research.brk_patterns import walk
from forex.ea_research.brk_fvg import fvgs
from forex.ea_research.orbx import ct

FL = ["C1_fvg", "C2_trend20", "C3_not_small_box", "C4_gap_aligned", "C5_strong_candle", "C6_twap_side", "C7_sp_confirms", "C8_vol_expanding"]


def events():
    M = Mkt("NSDQ"); S = Mkt("SP"); D = M.D; t = M.t; mc = M.mc
    Dd = M.Dd.copy(); rg = Dd.H - Dd.L
    Dd["atr100"] = rg.shift(1).rolling(100, min_periods=60).mean(); Dd["sma20"] = Dd.C.shift(1).rolling(20, min_periods=15).mean()
    F = fvgs(D); fo = F.formed.to_numpy(); out = []
    for p, dn in enumerate(M.days):
        day = pd.Timestamp(int(dn) * 86400, unit="s")
        if day < pd.Timestamp("2022-01-01") or day.weekday() >= 5 or p < 1:
            continue
        b0, b1, w1, x1 = (ts(day.year, day.month, day.day, h, m, NYZ) for h, m in ((9, 30), (10, 0), (12, 0), (16, 0)))
        i0, i1, iw, ix = np.searchsorted(t, [b0, b1, w1, x1])
        if i1 - i0 < 24 or ix >= len(t) or iw - i1 < 30:
            continue
        hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        jj = (t[i1:iw] - b1) // 300; sig = None
        for c in range(int((w1 - b1) // 300)):
            sel = np.flatnonzero(jj == c)
            if len(sel) < 3:
                continue
            cl = mc[i1 + sel[-1]]
            if cl > hi or cl < lo:
                sig = (c, i1 + sel[0], i1 + sel[-1], cl); break
        if sig is None:
            continue
        c, sa, sb, cl = sig; side = 1 if cl > hi else -1
        k = int(np.searchsorted(t, b1 + (c + 1) * 300))
        if k >= ix - 1:
            continue
        e1 = D["ao"][k] if side > 0 else D["bo"][k]; stop = lo if side > 0 else hi; risk = abs(e1 - stop)
        if side * (e1 - stop) <= 0:
            continue
        tgt = e1 + side * risk
        ex1, _ = walk(D, side, k, ix, stop, tgt); R1 = (ex1 - e1) * side / risk
        edge = hi if side > 0 else lo; R2 = np.nan
        for q in range(k, ix - 1):
            if (D["al"][q] <= edge) if side > 0 else (D["bh"][q] >= edge):
                e2 = min(edge, D["ao"][q]) if side > 0 else max(edge, D["bo"][q]); ex2, _ = walk(D, side, q, ix, stop, tgt); R2 = (ex2 - e2) * side / risk; break
            if (D["bh"][q] >= tgt) if side > 0 else (D["al"][q] <= tgt):
                break
        r = Dd.iloc[p]; y = Dd.iloc[p - 1]; atr = r.atr
        spb = np.median(D["sp"][i0:i1]); d0 = ts(day.year, day.month, day.day, 0, 0, LIS)
        a, b = np.searchsorted(fo, d0), np.searchsorted(fo, t[sb] + 60, side="right")
        cand = F.iloc[a:b]; cand = cand[(cand.kind == side) & (cand.bot >= lo) & (cand.top <= hi) & ((cand.top - cand.bot) >= spb)]
        fvg = False
        for g in cand.itertuples():
            j0 = int(np.searchsorted(t, g.formed))
            if j0 >= k or ((M.ml[j0:k].min() >= g.top) if side > 0 else (M.mh[j0:k].max() <= g.bot)):
                fvg = True; break
        sh, sl_, = M.mh[sa:sb + 1].max(), M.ml[sa:sb + 1].min()
        pos = (cl - sl_) / (sh - sl_) if sh > sl_ else 0.5
        Sb = S.box(b0, b1, 24); spm = S.mid_at(int(t[sb]))
        sp_ok = bool(Sb and np.isfinite(spm) and ((spm > Sb[0]) if side > 0 else (spm < Sb[1])))
        out.append(dict(day=day, side=side, R1=R1, R2=R2, box_atr=(hi - lo) / atr if atr > 0 else np.nan,
                        C1_fvg=fvg, C2_trend20=bool(side * (y.C - r.sma20) > 0), C4_gap_aligned=bool(side * (mc[i0] - y.C) > 0),
                        C5_strong_candle=bool(pos >= 0.75 if side > 0 else pos <= 0.25), C6_twap_side=bool(side * (cl - mc[i0:sb + 1].mean()) > 0),
                        C7_sp_confirms=sp_ok, C8_vol_expanding=bool(r.atr / r.atr100 > 1) if r.atr100 > 0 else False))
    E = pd.DataFrame(out)
    q33 = E[E.day < "2025-01-01"].box_atr.quantile(1 / 3); E["C3_not_small_box"] = E.box_atr >= q33
    return E, q33


def welch(a, b):
    if len(a) < 2 or len(b) < 2:
        return np.nan                                                     # a flag that is always true / false cannot be tested
    se = np.sqrt(a.var() / len(a) + b.var() / len(b)); return (a.mean() - b.mean()) / se if se > 0 else np.nan


def main():
    from forex.ea_research.usdjpy_account_env import account, HZ
    E, q33 = events()
    dev, val = E[E.day < "2025-01-01"], E[(E.day >= "2025-01-01") & (E.day < "2026-01-01")]
    print(f"R16-T1 events: DEV {len(dev)} ({dev.R1.mean():+.3f} R), VAL {len(val)} ({val.R1.mean():+.3f} R); C3 cut box/ATR >= {q33:.3f} (DEV 33rd pct)\n")
    kept = []
    for c in FL:
        w, wo = dev[dev[c]], dev[~dev[c]]; t = welch(w.R1, wo.R1)
        keep = len(w) >= 150 and w.R1.mean() > 0 and w.R1.mean() > wo.R1.mean() and t >= 2.0
        kept += [c] if keep else []
        vw, vwo = val[val[c]], val[~val[c]]
        print(f"{c:18s} DEV with n {len(w):3d} {w.R1.mean():+.3f} | without n {len(wo):3d} {wo.R1.mean():+.3f} | t {t:+.2f} -> {'KEEP' if keep else 'drop'}"
              f"   (VAL, descriptive: with {vw.R1.mean():+.3f} n {len(vw)} / without {vwo.R1.mean():+.3f}; T2 retest DEV with {w.R2.mean():+.3f})")
    print("\nkept on DEV:", kept or "none")
    rule = lambda X: X[np.logical_and.reduce([X[c] for c in kept])] if kept else X
    rd, rv = rule(dev), rule(val)
    md, td = ct(rd.assign(R=rd.R1)); mv, tv = ct(rv.assign(R=rv.R1))
    print(f"combined rule ({' AND '.join(kept) if kept else 'base'}): DEV n {len(rd)} {md:+.3f} R (t {td:+.2f}) | VAL n {len(rv)} {mv:+.3f} R (t {tv:+.2f}) vs base VAL {val.R1.mean():+.3f}")
    okv = bool(kept) and mv > 0 and tv >= 1.65 and mv > val.R1.mean()
    if okv:
        h = rule(E[E.day >= "2026-01-01"]); mh, th = ct(h.assign(R=h.R1))
        print(f"HOLD 2026 (one look): n {len(h)} {mh:+.3f} R (t {th:+.2f}) -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}")
    else:
        print("VAL confirmation failed or nothing kept: HOLD 2026 stays sealed")
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1623)
    x = rule(E[E.day < "2026-01-01"])
    Rd = x.set_index("day").R1.reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
    s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
    for risk in (250, 500):
        st, ev, _ = account(r[bi], trd[bi], risk)
        print(f"account NSDQ ${risk} a trade ({len(x)} trades 2022-25, {x.R1.mean():+.3f} R; DEV part is in-sample for the selection): " + "  ".join(
            f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("22 Dec", "31 Mar 27", "30 Jun 27")))


if __name__ == "__main__":
    main()
