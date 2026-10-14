"""DAY2K-C: the daily 1:1 / 2,000 USD trade over all 46 MT5. Pre-registration: PREREG_DAY2K_C.md. Run from the repo root.
  python -m forex.self_improving.day2k.day2kc --dry-run | --calibrate | --run | --hold CELL"""
import sys, itertools
import numpy as np, pandas as pd
from forex.self_improving.day2k import day2k as D, day2kb as B

FX = list(D.PAIRS)
OTHER = {"XAUUSD": "metal", "XAGUSD": "metal", "BRENT": "energy", "WTI": "energy", "SP": "index", "NSDQ": "index", "DOW": "index", "DAX": "index", "NIKKEI": "index", "ASX": "index",
         "BTCUSD": "crypto", "ETHUSD": "crypto", "LTCUSD": "crypto", "XRPUSD": "crypto", "SOLUSD": "crypto", "BNBUSD": "crypto", "BCHUSD": "crypto", "ADAUSD": "crypto"}
UNI = FX + list(OTHER)
CLASS = {s: "fx" for s in FX}; CLASS.update(OTHER); CODE = {"fx": 0, "metal": 1, "energy": 2, "index": 3, "crypto": 4}
D.PAIRS = UNI; D.DEV_T = 2.91
COLS_C = [f for f in B.PRICE_ONLY if f not in ("cs1", "cs5")] + ["tvr", "nhigh"]            # the 'nhigh' slot carries the asset-class code in this round (no calendar here)
NAMES = list(D.PAIRS)


def build_all():
    days, R, RES, S = D.build(D.LO, D.VAL_HI, "Cdevval")
    f = D.CACHE / "day2kc_feats.npz"
    if f.exists(): return days, R, RES, S, np.load(f)["F"]
    full = D.trading_days("2021-10-01", D.VAL_HI); F = np.full((len(full), len(UNI), 2, len(B.FEATS)), np.nan, np.float32)
    for pi, sym in enumerate(UNI):
        A = D.load(sym); atr = D.atr20(A, full); sc = D.scores_for(A, full, atr); tv = pd.read_parquet(B.TV / f"{sym}.parquet", columns=["time", "tick_volume"])
        F[:, pi] = B.pair_feats(sym, A, tv, full, atr, sc); F[:, pi, :, B.FI["nhigh"]] = CODE[CLASS[sym]]; print("  feats", sym, flush=True)
    F = F[np.isin(full, days)]; np.savez_compressed(f, F=F); return days, R, RES, S, F


def ml_cells(F, R, days, perm=None, leak=False):
    if perm is not None: R = R[perm]
    dev = (days >= B.SCORE_START) & (days <= D.d64(D.DEV_HI)); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI)); out = []
    for ti, ki in itertools.product(range(2), range(2)):
        r = B.walk_forward(F, R, days, ti, ki, COLS_C, leak); b = D.baseline(R, ti, ki); md, td = D.block_t(r[dev]); mv, tv = D.block_t(r[val]); nv = int(np.isfinite(r[val]).sum()); bd = float(np.nanmean(b[dev]))
        out.append(dict(cell=f"ML-C-T{D.TS[ti]//3600:02d}{(D.TS[ti]%3600)//60:02d}-k{D.KS[ki]}", n_dev=int(np.isfinite(r[dev]).sum()), dev_R=md, dev_t=td, dev_base=bd, n_val=nv, val_R=mv, val_t=tv, val_base=float(np.nanmean(b[val])),
                        S1=bool(md > 0 and td >= D.DEV_T and md > bd and mv > 0 and tv >= 1.65 and nv >= 200)))
    return pd.DataFrame(out)


def yardsticks(R, days):
    dev = (days >= B.SCORE_START) & (days <= D.d64(D.DEV_HI)); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI)); rows = []
    for cl in CODE:
        idx = [i for i, s in enumerate(NAMES) if CLASS[s] == cl]
        for ti, ki in ((0, 0), (1, 0), (0, 1)):
            for side, sn in ((0, "long"), (1, "short")):
                x = np.nanmean(R[:, idx, ti, ki, side], axis=1); rows.append(dict(cls=cl, T=f"T{D.TS[ti]//3600:02d}{(D.TS[ti]%3600)//60:02d}", k=D.KS[ki], side=sn, n=len(idx), dev_R=D.block_t(x[dev])[0], dev_t=D.block_t(x[dev])[1], val_R=D.block_t(x[val])[0], val_t=D.block_t(x[val])[1]))
    return pd.DataFrame(rows)


def dry_run():
    days, R, RES, S, F = build_all(); print("days", len(days), "markets", len(UNI), "R", R.shape)
    for cl in CODE:
        idx = [i for i, s in enumerate(NAMES) if CLASS[s] == cl]
        for ti in range(2):
            v = np.isfinite(R[:, idx, ti, 0, 0]); rs = RES[:, idx, ti, 0, :][np.isfinite(R[:, idx, ti, 0, :])]
            print(f"{cl:7s} ({len(idx):2d} markets) T{D.TS[ti]//3600:02d}{(D.TS[ti]%3600)//60:02d}: valid market-days {100*v.mean():.0f}% | resolved share k0.4 {rs.mean():.2f} k0.7 {RES[:, idx, ti, 1, :][np.isfinite(R[:, idx, ti, 1, :])].mean():.2f}")
    rng = np.random.default_rng(11); bad = n = 0
    for _ in range(40):
        pi = int(rng.integers(len(UNI))); di = int(rng.integers(40, len(days))); ti = int(rng.integers(2)); A = D.load(UNI[pi]); cut = int(days[di]) * 86400 + D.TS[ti]
        m = A["t"] < cut; Bz = {k: v[m] for k, v in A.items()}; dd = D.trading_days("2021-10-01", D.VAL_HI); sc = D.scores_for(Bz, dd, D.atr20(Bz, dd)); j = int(np.searchsorted(dd, days[di]))
        a = sc[j, ti]; b = S[di, pi, ti].astype(float); n += 1; bad += int(not np.allclose(np.nan_to_num(a, nan=-99), np.nan_to_num(b, nan=-99), atol=1e-4))
    print(f"truncation test (scores, incl. non-FX): {n - bad}/{n} identical")


def main():
    a = sys.argv[1:]
    if "--dry-run" in a: dry_run(); return
    days, R, RES, S, F = build_all()
    if "--calibrate" in a:
        e = D.evaluate(R, S, days, oracle=True); print("POSITIVE CONTROL rules (oracle side) dev R:", e.dev_R.round(2).tolist()[:8], "...", flush=True)
        e = ml_cells(F, R, days, leak=True); print("POSITIVE CONTROL ML (label leaked) dev R:", e.dev_R.round(2).tolist(), flush=True)
        for sr, sm in zip((101, 102, 103), (111, 112, 113)):
            r1 = D.evaluate(R, S, days, rng_seed=sr); r2 = ml_cells(F, R, days, perm=np.random.default_rng(sm).permutation(len(days)))
            print(f"placebo rules {sr}: S1 {int(r1.S1.sum())} best dev t {r1.dev_t.max():.2f} | ML {sm}: S1 {int(r2.S1.sum())} best dev t {r2.dev_t.max():.2f}", flush=True)
        return
    if "--run" in a:
        pd.set_option("display.width", 220); r1 = D.evaluate(R, S, days); r2 = ml_cells(F, R, days); e = pd.concat([r1, r2]); e.to_csv(D.CACHE / "DAY2KC_cells.csv", index=False)
        print(e.round(3).to_string(index=False)); print("S1 survivors:", int(e.S1.sum())); y = yardsticks(R, days); y.to_csv(D.CACHE / "DAY2KC_yardsticks.csv", index=False)
        print("\nYARDSTICKS (average over the class of always-long / always-short; T10:05 k0.4, T16:35 k0.4, T10:05 k0.7):"); print(y.round(3).to_string(index=False))
        rng = np.random.default_rng(5); dev = days <= D.d64(D.VAL_HI); res = []
        for w in range(40):
            r = np.full(len(days), np.nan)
            for d in range(len(days)):
                v = np.argwhere(np.isfinite(R[d, :, 0, 0, :]))
                if len(v): p, s = v[rng.integers(len(v))]; r[d] = R[d, p, 0, 0, s]
            res.append(D.mt5_rolling(r))
        ps = sum(o["pass_"] for o in res); br = sum(o["breach"] for o in res); print(f"\nrandom daily pick over 46 markets, T10:05 k0.4, MT5 broker rolling starts: pass {100*ps/(ps+br):.1f}% of finished, breach {100*br/(ps+br):.1f}%"); return
    print(__doc__)


if __name__ == "__main__":
    main()
