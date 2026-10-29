"""DAY2K-B: a learned quality score for the one-setup-a-day 1:1 trade. Pre-registration: PREREG_DAY2K_B.md. Run from the repo root.
  python -m forex.self_improving.day2k.day2kb --dry-run | --calibrate | --run | --hold CELL"""
import sys, itertools, pathlib, warnings
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from forex.self_improving.day2k import day2k as D

warnings.filterwarnings("ignore")
CAL = pathlib.Path("data/data_macro/mt5_calendar.csv"); TV = pathlib.Path("data/ticks_vol")
FEATS = ["m1", "m5", "m20", "am", "pdh", "pdl", "apos", "cs1", "cs5", "surp", "rr", "arng", "spr", "tvr", "nhigh", "dow"]
SIGNED = ["m1", "m5", "m20", "am", "pdh", "pdl", "apos", "cs1", "cs5", "surp"]
PRICE_ONLY = [f for f in FEATS if f not in ("surp", "nhigh", "tvr")]
CCY = ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"]
FI = {f: i for i, f in enumerate(FEATS)}
SCORE_START = D.d64("2022-12-01"); HOLD_HI_B = "2026-08-14"
HP = dict(max_depth=3, max_iter=100, learning_rate=0.06, min_samples_leaf=300, l2_regularization=1.0, random_state=0)


def events():
    c = pd.read_csv(CAL, encoding="cp1252", usecols=["time", "currency", "importance", "impact"])
    c = c[c.importance >= 2].copy(); ts = pd.to_datetime(c.time, format="%Y.%m.%d %H:%M:%S").dt.tz_localize("UTC").dt.tz_convert("Europe/Athens").dt.tz_localize(None)
    c["t"] = ((ts - pd.Timestamp("1970-01-01")).dt.total_seconds()).astype("int64"); c["w"] = (c.importance - 1) * np.where(c.impact == 1, 1, np.where(c.impact == 2, -1, 0))
    out = {}
    for ccy, g in c.groupby("currency"):
        g = g.sort_values("t"); out[ccy] = (g.t.to_numpy(), np.concatenate([[0], np.cumsum(g.w.to_numpy())]), g.t[g.importance == 3].to_numpy())
    return out


def cal_feats(ev, full):
    sur = np.zeros((len(full), 2, len(CCY))); nh = np.zeros_like(sur)
    for ci, ccy in enumerate(CCY):
        et, cw, e3 = ev.get(ccy, (np.array([]), np.array([0]), np.array([])))
        for ti, T in enumerate(D.TS):
            a = np.searchsorted(et, full * 86400, side="left"); b = np.searchsorted(et, full * 86400 + T - 60, side="right"); sur[:, ti, ci] = cw[b] - cw[a]
            nh[:, ti, ci] = np.searchsorted(e3, full * 86400 + T + 4 * 3600, side="right") - np.searchsorted(e3, full * 86400 + T, side="right")
    return sur, nh


def pair_feats(sym, A, tv, full, atr, sc):
    """per-pair features for every day in `full` and both T; sc = scores_for output (m5, m1, am)"""
    t = A["t"]; di = t // 86400; u, st = np.unique(di, return_index=True); n = np.diff(np.append(st, len(t)))
    hi = np.maximum.reduceat(A["bh"], st); lo = np.minimum.reduceat(A["bl"], st); keep = ((u + 3) % 7 < 5) & (n >= 600); ku, kh, kl = u[keep], hi[keep], lo[keep]
    j = np.searchsorted(ku, full, side="left") - 1; jj = np.clip(j, 0, len(ku) - 1)
    rr = pd.Series(kh - kl).rolling(5, min_periods=4).mean().to_numpy()[jj] / atr; rr = np.where(j >= 0, rr, np.nan)
    c_ex = np.concatenate([[0], np.cumsum(tv["tick_volume"].to_numpy(np.float64))]); tt = tv["time"].to_numpy()
    out = np.full((len(full), 2, len(FEATS)), np.nan)
    for ti, T in enumerate(D.TS):
        pT = D.price_at(A, full * 86400 + T - 60)
        out[:, ti, FI["m5"]], out[:, ti, FI["m1"]], out[:, ti, FI["am"]] = sc[:, ti, 0], sc[:, ti, 1], sc[:, ti, 2]
        p20 = np.roll(pT, 20); p20[:20] = np.nan; out[:, ti, FI["m20"]] = (pT - p20) / atr
        out[:, ti, FI["pdh"]] = np.where(j >= 0, (pT - kh[jj]) / atr, np.nan); out[:, ti, FI["pdl"]] = np.where(j >= 0, (pT - kl[jj]) / atr, np.nan)
        out[:, ti, FI["rr"]] = rr
        ia = np.searchsorted(t, full * 86400 + D.AM_T); ib = np.searchsorted(t, full * 86400 + T)
        ap = np.full(len(full), np.nan); ar = np.full(len(full), np.nan)
        for k in range(len(full)):
            if ib[k] - ia[k] >= 60 and np.isfinite(pT[k]):
                h = A["bh"][ia[k]:ib[k]].max(); l = A["bl"][ia[k]:ib[k]].min()
                if h > l: ap[k] = (pT[k] - l) / (h - l) - 0.5; ar[k] = (h - l) / atr[k]
        out[:, ti, FI["apos"]], out[:, ti, FI["arng"]] = ap, ar
        isp = np.searchsorted(t, full * 86400 + T - 60, side="right") - 1; out[:, ti, FI["spr"]] = A["sp"][np.clip(isp, 0, len(t) - 1)] / atr
        w = c_ex[np.searchsorted(tt, full * 86400 + T)] - c_ex[np.searchsorted(tt, full * 86400 + D.AM_T)]
        ok = (np.searchsorted(tt, full * 86400 + T) - np.searchsorted(tt, full * 86400 + D.AM_T)) >= 60
        w = np.where(ok, w, np.nan); out[:, ti, FI["tvr"]] = w / pd.Series(w).rolling(20, min_periods=10).mean().shift(1).to_numpy()
        out[:, ti, FI["dow"]] = (full + 3) % 7
    return out


def build_feats(lo, hi, tag):
    f = D.CACHE / f"day2kb_{tag}.npz"; days = D.trading_days(lo, hi)
    if f.exists(): return days, np.load(f)["F"]
    full = D.trading_days("2021-10-01", hi); ev = events(); sur, nh = cal_feats(ev, full); F = np.full((len(full), len(D.PAIRS), 2, len(FEATS)), np.nan, np.float32)
    for pi, sym in enumerate(D.PAIRS):
        A = D.load(sym); atr = D.atr20(A, full); sc = D.scores_for(A, full, atr)
        tv = pd.read_parquet(TV / f"{sym}.parquet", columns=["time", "tick_volume"]); F[:, pi] = pair_feats(sym, A, tv, full, atr, sc)
        b, q = D.PAIRS[pi][:3], D.PAIRS[pi][3:]; F[:, pi, :, FI["surp"]] = sur[:, :, CCY.index(b)] - sur[:, :, CCY.index(q)]; F[:, pi, :, FI["nhigh"]] = nh[:, :, CCY.index(b)] + nh[:, :, CCY.index(q)]
        print("  feats", sym, flush=True)
    for key, src in (("cs1", "m1"), ("cs5", "m5")):
        st = np.full((len(full), 2, len(CCY)), np.nan)
        for ci, ccy in enumerate(CCY):
            cols = []
            for pi, p in enumerate(D.PAIRS):
                if p[:3] == ccy: cols.append(F[:, pi, :, FI[src]])
                elif p[3:] == ccy: cols.append(-F[:, pi, :, FI[src]])
            st[:, :, ci] = np.nanmean(np.stack(cols, 0), 0)
        for pi, p in enumerate(D.PAIRS): F[:, pi, :, FI[key]] = st[:, :, CCY.index(p[:3])] - st[:, :, CCY.index(p[3:])]
    m = np.isin(full, days); F = F[m]; np.savez_compressed(f, F=F); return days, F


def oriented(F, side):
    X = F.copy()
    for s in SIGNED: X[..., FI[s]] *= (1 if side == 0 else -1)
    return X


def walk_forward(F, R, days, ti, ki, cols, leak=False):
    """quarterly refit, expanding window; returns the daily pick R (NaN before SCORE_START) and the daily rank-IC"""
    ci = [FI[c] for c in cols]; Xl, Xs = oriented(F[:, :, ti], 0)[..., ci], oriented(F[:, :, ti], 1)[..., ci]
    yl, ys = R[:, :, ti, ki, 0], R[:, :, ti, ki, 1]
    if leak: Xl = np.concatenate([Xl, yl[..., None]], -1); Xs = np.concatenate([Xs, ys[..., None]], -1)
    out = np.full(len(days), np.nan); sd = pd.to_datetime(days.astype("datetime64[D]")); edges = sorted(set([SCORE_START] + [int(np.datetime64(f"{y}-{m:02d}-01", "D").astype(int)) for y in range(2022, 2027) for m in (3, 6, 9, 12) if int(np.datetime64(f"{y}-{m:02d}-01", "D").astype(int)) > SCORE_START] + [int(days.max()) + 1]))
    for a, b in zip(edges[:-1], edges[1:]):
        tr = days < a; te = (days >= a) & (days < b)
        if te.sum() == 0: continue
        Xt = np.concatenate([Xl[tr].reshape(-1, Xl.shape[-1]), Xs[tr].reshape(-1, Xs.shape[-1])]); yt = np.concatenate([yl[tr].ravel(), ys[tr].ravel()]); ok = np.isfinite(yt)
        mdl = HistGradientBoostingRegressor(**HP).fit(Xt[ok], yt[ok])
        pl = mdl.predict(Xl[te].reshape(-1, Xl.shape[-1])).reshape(te.sum(), -1); ps = mdl.predict(Xs[te].reshape(-1, Xs.shape[-1])).reshape(te.sum(), -1)
        pl = np.where(np.isfinite(yl[te]), pl, -9); ps = np.where(np.isfinite(ys[te]), ps, -9); P = np.stack([pl, ps], -1).reshape(te.sum(), -1); Y = np.stack([yl[te], ys[te]], -1).reshape(te.sum(), -1)
        k = P.argmax(1); r = Y[np.arange(len(k)), k]; r[P.max(1) <= -9] = np.nan; out[np.where(te)[0]] = r
    return out


def cs_cell(F, R, ti, ki):
    S2 = np.zeros((F.shape[0], F.shape[1], 2, 3), np.float32); S2[..., 0] = F[..., FI["cs1"]]
    return D.pick(R, S2, 0, True, ti, ki)


def run_cells(F, R, days, perm=None, leak=False, only_ml=False):
    if perm is not None: R = R[perm]
    dev = (days >= SCORE_START) & (days <= D.d64(D.DEV_HI)); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI)); rows = []
    for ti, ki, fs in itertools.product(range(2), range(2), ("FULL", "PRICE")):
        cols = FEATS if fs == "FULL" else PRICE_ONLY; r = walk_forward(F, R, days, ti, ki, cols, leak); rows.append((f"ML-{fs}-T{D.TS[ti]//3600:02d}{(D.TS[ti]%3600)//60:02d}-k{D.KS[ki]}", r, ti, ki))
    if not only_ml:
        for ti in range(2): rows.append((f"CS1-cont-T{D.TS[ti]//3600:02d}{(D.TS[ti]%3600)//60:02d}-k0.4", cs_cell(F, R, ti, 0), ti, 0))
    res = []
    for nm, r, ti, ki in rows:
        b = D.baseline(R, ti, ki); md, td = D.block_t(r[dev]); mv, tv = D.block_t(r[val]); bd = float(np.nanmean(b[dev])); nv = int(np.isfinite(r[val]).sum())
        res.append(dict(cell=nm, n_dev=int(np.isfinite(r[dev]).sum()), dev_R=md, dev_t=td, dev_base=bd, n_val=nv, val_R=mv, val_t=tv, val_base=float(np.nanmean(b[val])), S1=bool(md > 0 and td >= 2.58 and md > bd and mv > 0 and tv >= 1.65 and nv >= 200)))
    return pd.DataFrame(res), dict((nm, r) for nm, r, _, _ in rows)


def dry_run():
    days, F = build_feats(D.LO, D.VAL_HI, "devval"); print("features", F.shape)
    print("non-NaN share by feature (T10:05 / T16:35):", {f: (round(float(np.isfinite(F[:, :, 0, i]).mean()), 3), round(float(np.isfinite(F[:, :, 1, i]).mean()), 3)) for f, i in FI.items()})
    c = pd.read_csv(CAL, encoding="cp1252", usecols=["actual", "forecast", "impact", "importance", "name", "currency"]); c = c[(c.importance >= 2) & (c.actual.abs() < 1e300) & (c.forecast.abs() < 1e300) & (c.actual != c.forecast)]
    print("impact semantics (importance>=2, actual != forecast): P(impact=1 | actual>forecast) =", round(float((c[c.actual > c.forecast].impact == 1).mean()), 3), "| P(impact=2 | actual<forecast) =", round(float((c[c.actual < c.forecast].impact == 2).mean()), 3), "(an inverted-indicator mix would pull these towards 0.5)")
    print("truncation test (features other than cs1/cs5/nhigh, bars+volume+events strictly before T):")
    rng = np.random.default_rng(3); bad = 0; n = 0; full = D.trading_days("2021-10-01", D.VAL_HI); ev = events()
    for _ in range(40):
        pi = int(rng.integers(len(D.PAIRS))); di = int(rng.integers(40, len(days))); ti = int(rng.integers(2)); cut = int(days[di]) * 86400 + D.TS[ti]
        A = D.load(D.PAIRS[pi]); m = A["t"] < cut; B = {k: v[m] for k, v in A.items()}; tv = pd.read_parquet(TV / f"{D.PAIRS[pi]}.parquet", columns=["time", "tick_volume"]); tv = tv[tv.time < cut]
        atr = D.atr20(B, full); sc = D.scores_for(B, full, atr); g = pair_feats(D.PAIRS[pi], B, tv, full, atr, sc); j = int(np.searchsorted(full, days[di]))
        evc = {k: (v[0][v[0] < cut], v[1][:int((v[0] < cut).sum()) + 1], v[2][v[2] < cut]) for k, v in ev.items()}; sur, nh = cal_feats(evc, full)
        b, q = D.PAIRS[pi][:3], D.PAIRS[pi][3:]; sv = sur[j, ti, CCY.index(b)] - sur[j, ti, CCY.index(q)]
        cmp_cols = [FI[f] for f in FEATS if f not in ("cs1", "cs5", "nhigh", "surp")]; a = g[j, ti, cmp_cols]; bb = F[di, pi, ti, cmp_cols].astype(float)
        n += 1; bad += int(not (np.allclose(np.nan_to_num(a, nan=-99), np.nan_to_num(bb, nan=-99), atol=1e-3, rtol=1e-3) and np.isclose(sv, F[di, pi, ti, FI["surp"]], atol=1e-4)))
    print(f"  {n - bad}/{n} pair-days identical")


def main():
    a = sys.argv[1:]
    if "--dry-run" in a: dry_run(); return
    days, R, RES, S = D.build(D.LO, D.VAL_HI, "devval"); _, F = build_feats(D.LO, D.VAL_HI, "devval")
    if "--calibrate" in a:
        e, _ = run_cells(F, R, days, leak=True, only_ml=True); print("POSITIVE CONTROL (label leaked in as a feature): dev R", e.dev_R.round(2).tolist(), flush=True)
        for seed in (91, 92, 93):
            e, _ = run_cells(F, R, days, perm=np.random.default_rng(seed).permutation(len(days))); print(f"placebo seed {seed}: S1 {int(e.S1.sum())}, best dev t {e.dev_t.max():.2f}, best val t {e.val_t.max():.2f}, dev t>=2.58: {int((e.dev_t >= 2.58).sum())}", flush=True)
        return
    if "--run" in a:
        e, picks = run_cells(F, R, days); pd.set_option("display.width", 200); e.to_csv(D.CACHE / "DAY2KB_cells.csv", index=False); print(e.round(3).to_string(index=False)); print("S1 survivors:", int(e.S1.sum()))
        np.savez_compressed(D.CACHE / "DAY2KB_picks.npz", days=days, **picks); return
    print(__doc__)


if __name__ == "__main__":
    main()
