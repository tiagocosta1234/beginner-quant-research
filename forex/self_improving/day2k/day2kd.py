"""DAY2K-D: gold only, long or short, one 1:1 trade a day. Pre-registration: PREREG_DAY2K_D.md. Run from the repo root.
  python -m forex.self_improving.day2k.day2kd --dry-run | --calibrate | --run"""
import sys, itertools
import numpy as np, pandas as pd
from forex.self_improving.day2k import day2k as D, day2kb as B, day2kc as C

D.DEV_T = 2.91
COLS = ["m1", "m5", "m20", "am", "pdh", "pdl", "apos", "rr", "arng", "spr", "tvr", "dow", "surp", "nhigh"]
HP_D = dict(B.HP, min_samples_leaf=100)


def gold():
    days, R, RES, S, F = C.build_all(); g = C.NAMES.index("XAUUSD")
    R, RES, S, F = R[:, g:g + 1].copy(), RES[:, g:g + 1].copy(), S[:, g:g + 1].copy(), F[:, g:g + 1].copy()
    full = D.trading_days("2021-10-01", D.VAL_HI); sur, nh = B.cal_feats(B.events(), full); m = np.isin(full, days); u = B.CCY.index("USD")
    F[:, 0, :, B.FI["surp"]] = -sur[m][:, :, u]; F[:, 0, :, B.FI["nhigh"]] = nh[m][:, :, u]
    return days, R, RES, S, F


def long_yard(R, ti, ki):
    return R[:, 0, ti, ki, 0].astype(float)


def rule_cells(R, S, days, seed=None, oracle=False):
    rng = np.random.default_rng(seed) if seed is not None else None
    dev = days <= D.d64(D.DEV_HI); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI)); out = []
    for c in D.cells():
        sg, cont, ti, ki = c; s = S[:, 0, ti, sg].astype(float)
        if rng is not None: s = np.where(np.isfinite(s), rng.standard_normal(len(s)), np.nan)
        rl, rs = R[:, 0, ti, ki, 0].astype(float), R[:, 0, ti, ki, 1].astype(float)
        long = (s > 0) if cont else (s < 0)
        if oracle: long = rl >= rs
        r = np.where(long, rl, rs); r[~np.isfinite(s) | (s == 0)] = np.nan
        out.append(row(D.name(c), r, R, ti, ki, dev, val))
    return pd.DataFrame(out)


def row(nm, r, R, ti, ki, dev, val):
    b = np.nanmean(R[:, 0, ti, ki, :].astype(float), axis=1); y = long_yard(R, ti, ki)
    md, td = D.block_t(r[dev]); mv, tv = D.block_t(r[val]); nv = int(np.isfinite(r[val]).sum()); yd = float(np.nanmean(y[dev & np.isfinite(r)])); yv = float(np.nanmean(y[val & np.isfinite(r)]))
    return dict(cell=nm, n_dev=int(np.isfinite(r[dev]).sum()), dev_R=md, dev_t=td, dev_base=float(np.nanmean(b[dev])), dev_long=yd, n_val=nv, val_R=mv, val_t=tv, val_long=yv,
                S1=bool(md > 0 and td >= D.DEV_T and md > float(np.nanmean(b[dev])) and md > yd and mv > 0 and tv >= 1.65 and nv >= 200 and mv > yv))


def ml_cells(F, R, days, perm=None, leak=False):
    if perm is not None: R = R[perm]
    dev = (days >= B.SCORE_START) & (days <= D.d64(D.DEV_HI)); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI)); out = []; old = B.HP
    B.HP = HP_D
    try:
        for ti, ki in itertools.product(range(2), range(2)):
            r = B.walk_forward(F, R, days, ti, ki, COLS, leak); out.append(row(f"ML-D-T{D.TS[ti]//3600:02d}{(D.TS[ti]%3600)//60:02d}-k{D.KS[ki]}", r, R, ti, ki, dev, val))
    finally:
        B.HP = old
    return pd.DataFrame(out)


def main():
    a = sys.argv[1:]; days, R, RES, S, F = gold(); pd.set_option("display.width", 230)
    if "--dry-run" in a:
        print("gold days", len(days), "valid T10:05", int(np.isfinite(R[:, 0, 0, 0, 0]).sum()), "T16:35", int(np.isfinite(R[:, 0, 1, 0, 0]).sum()))
        print("USD surprise non-zero share (T10:05 / T16:35):", round(float((F[:, 0, 0, B.FI['surp']] != 0).mean()), 3), round(float((F[:, 0, 1, B.FI['surp']] != 0).mean()), 3), "| USD high events ahead share:", round(float((F[:, 0, 0, B.FI['nhigh']] > 0).mean()), 3), round(float((F[:, 0, 1, B.FI['nhigh']] > 0).mean()), 3))
        print("feature coverage:", {c: round(float(np.isfinite(F[:, 0, 0, B.FI[c]]).mean()), 3) for c in COLS}); return
    if "--calibrate" in a:
        print("ORACLE rules dev R:", rule_cells(R, S, days, oracle=True).dev_R.round(2).tolist()[:4], "| LEAK ML dev R:", ml_cells(F, R, days, leak=True).dev_R.round(2).tolist(), flush=True)
        for sr, sm in zip((121, 122, 123), (131, 132, 133)):
            r1 = rule_cells(R, S, days, seed=sr); r2 = ml_cells(F, R, days, perm=np.random.default_rng(sm).permutation(len(days)))
            print(f"placebo rules {sr}: S1 {int(r1.S1.sum())} best dev t {r1.dev_t.max():.2f} | ML {sm}: S1 {int(r2.S1.sum())} best dev t {r2.dev_t.max():.2f}", flush=True)
        return
    if "--run" in a:
        e = pd.concat([rule_cells(R, S, days), ml_cells(F, R, days)]); e.to_csv(D.CACHE / "DAY2KD_cells.csv", index=False); print(e.round(3).to_string(index=False)); print("S1 survivors:", int(e.S1.sum()))
        for ti, ki in itertools.product(range(2), range(2)):
            y = long_yard(R, ti, ki); s = R[:, 0, ti, ki, 1].astype(float); dev = days <= D.d64(D.DEV_HI); val = days >= D.d64(D.VAL_LO)
            print(f"yardstick T{D.TS[ti]//3600:02d}{(D.TS[ti]%3600)//60:02d} k{D.KS[ki]}: always long DEV {D.block_t(y[dev])[0]:+.3f} VAL {D.block_t(y[val])[0]:+.3f} | always short DEV {D.block_t(s[dev])[0]:+.3f} VAL {D.block_t(s[val])[0]:+.3f}")
        return
    print(__doc__)


if __name__ == "__main__":
    main()
