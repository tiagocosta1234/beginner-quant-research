"""DAY2K-J: rank every MT5 broker symbol, go long the one most likely to go up. PREREG_DAY2K_J.md. Run from the repo root.
  python -m forex.self_improving.day2k.day2kj --dry-run | --calibrate | --run"""
import sys
import numpy as np, pandas as pd
from forex.self_improving.day2k import day2k as D, day2kb as B, day2kh as H

NAMES = H.NAMES; N = len(NAMES); T_IDX = {"H1": 0, "H2": 1, "H3": 0}


def build_returns(days):
    """net[d, m, h] in ATR units for buying at the T+60 ask open and selling at the bid open of the 21:55 bar (same day for H1/H2, 5th trading day for H3)"""
    full = D.trading_days("2021-10-01", D.VAL_HI); out = np.full((len(days), N, 3), np.nan)
    for mi, sym in enumerate(NAMES):
        A = D.load(sym); t = A["t"]; atr = D.atr20(A, full)[np.isin(full, days)]
        def at(ep):
            i = np.searchsorted(t, ep); ii = np.clip(i, 0, len(t) - 1); return np.where((i < len(t)) & (t[ii] == ep), ii, -1)
        x = at(days * 86400 + D.EXIT)
        for h, (ti, lag) in enumerate(((0, 0), (1, 0), (0, 4))):
            e = at(days * 86400 + D.TS[ti] + 60); xl = np.full(len(days), -1)
            xl[: len(days) - lag] = x[lag:] if lag else x
            ok = (e >= 0) & (xl >= 0); out[:, mi, h] = np.where(ok, (A["bo"][np.clip(xl, 0, len(t) - 1)] - A["ao"][np.clip(e, 0, len(t) - 1)]) / atr, np.nan)
    return out


def scores(days, S, FC, usd, keep, Fg):
    """score arrays [day, market] per ranker and horizon (P(up) models come from DAY2K-H walk-forward)"""
    sc = {}
    for h in ("H1", "H2", "H3"):
        ti = T_IDX[h]
        sc[("trend20", h)] = FC[:, :, ti, B.FI["m20"]].astype(float)
        m5 = FC[:, :, ti, B.FI["m5"]].astype(float); sc[("rev5", h)] = -m5
        sc[("trend60", h)] = None; sc[("trend120", h)] = None
    return sc


def trend_scores(days):
    full = D.trading_days("2021-01-01", D.VAL_HI); out = {}
    for L in (60, 120):
        for ti in range(2):
            m = np.full((len(days), N), np.nan)
            for mi, sym in enumerate(NAMES):
                A = D.load(sym); atr = D.atr20(A, full); pT = D.price_at(A, full * 86400 + D.TS[ti] - 60); s = np.full(len(full), np.nan); s[L:] = (pT[L:] - pT[:-L]) / atr[L:]; m[:, mi] = s[np.isin(full, days)]
            out[(L, ti)] = m
    return out


def pup_scores(days, S, FC, usd, keep):
    out = {}
    for ti in range(2):
        Xp = H.pooled_X(FC, S, usd, ti, keep); nd, nm, nf = Xp.shape; Xpf = Xp.reshape(-1, nf); retp = H.targets(days)[:, keep, ti].reshape(-1); yp = np.where(np.isfinite(retp), (retp > 0).astype(float), np.nan); dayrow = np.repeat(np.arange(nd), nm)
        for kind in ("LOGIT", "HGB"):
            p = H.wf_prob(Xpf, yp, days[dayrow], kind).reshape(nd, nm); full = np.full((nd, N), np.nan); full[:, np.where(keep)[0]] = p; out[(kind, ti)] = full
    return out


def top_pick(score, keep, rng=None, shuffle_within=False):
    s = score.copy(); s[:, ~keep] = np.nan
    if shuffle_within:
        for d in range(len(s)):
            v = np.where(np.isfinite(s[d]))[0]
            if len(v): s[d, v] = rng.permutation(s[d, v])
    a = np.where(np.isfinite(s), s, -np.inf); return a.argmax(1), np.isfinite(a.max(1))


def blockt(x, b):
    x = x[np.isfinite(x)]; n = len(x) // b
    if n < 8: return np.nan, np.nan
    m = x[:n * b].reshape(n, b).mean(1); return float(x.mean()), float(m.mean() / (m.std(ddof=1) / np.sqrt(n)))


def main():
    a = sys.argv[1:]; days, S, FC, yret, Fg, usd, mac, keep, gi = H.load_all(); net = build_returns(days); mkts = np.where(keep)[0]; pd.set_option("display.width", 220)
    dev = (days >= B.SCORE_START) & (days <= D.d64(D.DEV_HI)); val = (days >= D.d64(D.VAL_LO)) & (days <= D.d64(D.VAL_HI))
    if "--dry-run" in a:
        print("rows with a return (H1/H2/H3) over kept markets:", [int(np.isfinite(net[:, keep, h]).sum()) for h in range(3)], "| mean net buy-everything per trade in ATR:", [round(float(np.nanmean(net[:, keep, h])), 4) for h in range(3)])
        print("mean spread cost in ATR (spr feature, kept):", round(float(np.nanmean(FC[:, keep, 0, B.FI['spr']])), 4)); return
    tr = trend_scores(days); pu = pup_scores(days, S, FC, usd, keep) if True else {}
    rankers = {}
    for h, ti in (("H1", 0), ("H2", 1), ("H3", 0)):
        rankers[("LOGIT", h)] = pu[("LOGIT", ti)]; rankers[("HGB", h)] = pu[("HGB", ti)]; rankers[("trend20", h)] = FC[:, :, ti, B.FI["m20"]].astype(float); rankers[("trend60", h)] = tr[(60, ti)]; rankers[("trend120", h)] = tr[(120, ti)]; rankers[("rev5", h)] = -FC[:, :, ti, B.FI["m5"]].astype(float)
    def run(world, seed=None):
        rng = np.random.default_rng(seed) if seed else None; rows = []
        for (rk, h), sc in rankers.items():
            hi = {"H1": 0, "H2": 1, "H3": 2}[h]; r = net[:, :, hi]; allm = np.nanmean(np.where(keep[None, :], r, np.nan), axis=1); b = 10 if h == "H3" else 5
            pk, okp = top_pick(sc, keep, rng, shuffle_within=(world == "placebo")); di = np.arange(len(days)); x = np.where(okp, r[di, pk], np.nan)
            if world == "oracle": x = np.nanmax(np.where(keep[None, :], r, np.nan), axis=1)
            d_ = x - allm; row = dict(rk=rk, h=h)
            for lab, m in (("dev", dev), ("val", val)):
                mn, tn = blockt(x[m], b); md, td = blockt(d_[m], b); row.update({f"net_{lab}": mn, f"t_{lab}": tn, f"diff_{lab}": md, f"dt_{lab}": td, f"win_{lab}": float(np.mean(x[m][np.isfinite(x[m])] > 0)), f"all_{lab}": float(np.nanmean(allm[m])), f"n_{lab}": int(np.isfinite(x[m]).sum())})
            row["S1"] = bool(row["net_dev"] > 0 and row["t_dev"] >= 2.91 and row["dt_dev"] >= 2.0 and row["net_val"] > 0 and row["t_val"] >= 1.65 and row["diff_val"] > 0); rows.append(row)
        return pd.DataFrame(rows)
    if "--calibrate" in a:
        o = run("oracle"); print("POSITIVE CONTROL (best realised market) mean dev net ATR: min %.2f median %.2f" % (o.net_dev.min(), o.net_dev.median()))
        for s in (181, 182, 183): q = run("placebo", s); print(f"placebo {s}: S1 {int(q.S1.sum())} | cells with dev t >= 2.91: {int((q.t_dev >= 2.91).sum())} | best dev t {q.t_dev.max():.2f}")
        return
    if "--run" in a:
        q = run("real"); q.to_csv(D.CACHE / "DAY2KJ_cells.csv", index=False); print(q.round(3).to_string(index=False)); print("S1 survivors:", int(q.S1.sum()))
        for rk, h in (("HGB", "H1"), ("trend60", "H1"), ("HGB", "H3")):
            sc = rankers[(rk, h)]; pk, ok_ = top_pick(sc, keep); names = pd.Series([NAMES[m] for m in pk[ok_ & dev]]); cls = pd.Series([__import__("forex.self_improving.day2k.day2kc", fromlist=["x"]).CLASS[NAMES[m]] for m in pk[ok_ & dev]])
            print(f"  {rk}-{h} most picked: {names.value_counts().head(5).to_dict()} | classes {cls.value_counts(normalize=True).round(2).to_dict()}")
        # today's pick for information (not a recommendation)
        return
    print(__doc__)


if __name__ == "__main__":
    main()
