"""Free-form trader data: hourly bars, ~26 causal features, forward net returns, stacked per class (PREREG_FREEFORM.md).
   python -m forex.self_improving.freeform.ff_data     (builds caches, prints sizes)"""
from __future__ import annotations

import pickle
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from forex.self_improving import platform_v3 as P3

DATA = P3.DATA
CACHE = Path("data/scratch/si_cache")
HS = (1, 2, 4, 8, 24, 48, 96)                     # holding horizons, in hourly bars
LEVELS = (0.03, 0.10, 0.25, 0.50, 0.75, 0.90, 0.97)
HOUR_LV = (0, 3, 6, 9, 12, 15, 18, 21); DOW_LV = (0, 1, 2, 3, 4)
WA = ("2022-01-01", "2023-06-30"); WB = ("2023-07-01", "2024-12-31"); VAL = ("2025-01-01", "2025-12-31")
FEATS = ["z1", "z2", "z4", "z8", "z24", "z72", "z120", "rsi4", "rsi14", "ma24", "ma120", "ma480", "vr24", "vr120", "sprel", "pos24", "pos120", "run", "hour", "dow", "cs24", "cs120"]
FI = {f: i for i, f in enumerate(FEATS)}


def ts(s): return int(pd.Timestamp(s).value // 10**9)               # server-local naive epoch, like the data's t


def hourly(m):
    f = CACHE / f"h_{m}.pkl"
    if f.exists(): return pickle.load(open(f, "rb"))
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bl", "bc", "ao"]).sort_values("t").drop_duplicates("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo)]; d["k"] = d.t // 3600
    g = d.groupby("k").agg(bo=("bo", "first"), ao=("ao", "first"), bc=("bc", "last"), bl=("bl", "min"), n=("t", "count")); g = g[g.n >= 20]
    g["t0"] = g.index.values * 3600; g = g.reset_index(drop=True); pickle.dump(g, open(f, "wb")); return g


def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)


def market_features(h):
    c = h.bc; lr = np.log(c).diff(); sd1 = lr.rolling(240, min_periods=120).std(); out = pd.DataFrame(index=h.index)
    for k in (1, 2, 4, 8, 24, 72, 120): out[f"z{k}"] = np.log(c / c.shift(k)) / (sd1 * np.sqrt(k))
    out["rsi4"], out["rsi14"] = rsi(c, 4), rsi(c, 14)
    for k in (24, 120, 480): out[f"ma{k}"] = (c / c.rolling(k).mean() - 1) / (sd1 * np.sqrt(k))
    out["vr24"] = lr.rolling(24).std() / sd1; out["vr120"] = lr.rolling(120).std() / sd1
    sp = (h.ao - h.bo) / h.bo; out["sprel"] = sp / sp.rolling(480, min_periods=120).median()
    for k in (24, 120): lo, hi = c.rolling(k).min(), c.rolling(k).max(); out[f"pos{k}"] = (c - lo) / (hi - lo)
    up = (lr > 0).astype(int).replace(0, -1); grp = (up != up.shift()).cumsum(); out["run"] = up.groupby(grp).cumsum()
    out["hour"] = (h.t0 // 3600) % 24; out["dow"] = ((h.t0 // 86400) + 3) % 7                     # 1970-01-01 was a Thursday
    return out


def fwd(h, carry):
    """Net forward returns for HS: enter next bar's open (ask long / bid short), exit bid close (long) / ask close ~ bc + that bar's spread (short)."""
    n = len(h); t0 = h.t0.values; ao, bo, bc = h.ao.values, h.bo.values, h.bc.values; sp = ao - bo; L = np.full((n, len(HS)), np.nan, np.float32); S = L.copy(); X = np.full((n, len(HS)), np.nan); G = L.copy()
    mid_o, mid_c = bo, bc                  # gross = bid-to-bid (no spread at either end: an exit-bar spread must not leak into the gross return)
    for j, H in enumerate(HS):
        if n <= H + 1: continue
        i = np.arange(0, n - H - 1); e, x = i + 1, i + H
        cost = carry * 1e-4 * (t0[x] - t0[e] + 3600) / 86400.0
        L[i, j] = bc[x] / ao[e] - 1 - cost; S[i, j] = bo[e] / (bc[x] + sp[x]) - 1 - cost; X[i, j] = t0[x] + 3600; G[i, j] = mid_c[x] / mid_o[e] - 1
    return L, S, X, G


class Win:
    """Rows of one window for one class: X features, Yl/Ys net forward returns (NaN where unusable), week id, market id, per-market segments."""
    def __init__(self, X, Yl, Ys, week, mkt, Yg, seg): self.X, self.Yl, self.Ys, self.week, self.mkt, self.Yg, self.seg = X, Yl, Ys, week, mkt, Yg, seg


class Stack:
    def __init__(self, cls, placebo=None):
        info = P3.CLASSES[cls]; carry = info["carry"]; hs = {}
        for m in info["members"]:
            h = hourly(m)
            if len(h) > 12000: hs[m] = h
        if placebo is not None: hs = self.shuffle(hs, placebo)
        feats = {m: market_features(h) for m, h in hs.items()}
        grids = {m: pd.Series(np.arange(len(h)), index=h.t0.values) for m, h in hs.items()}
        for k in (24, 120):                                                       # cross-sectional rank among the class's markets at the same hour
            W = pd.DataFrame({m: pd.Series(feats[m][f"z{k}"].values, index=hs[m].t0.values) for m in hs}); R = W.rank(axis=1, pct=True); R[W.notna().sum(axis=1) < 3] = np.nan
            for m in hs: feats[m][f"cs{k}"] = R[m].reindex(hs[m].t0.values).values
        self.cls, self.markets = cls, list(hs); W = {"a": WA, "b": WB, "val": VAL}; parts = {w: [] for w in W}
        for mi, m in enumerate(hs):
            h = hs[m]; Fm = feats[m][FEATS].values.astype(np.float32); L, S, X, Gr = fwd(h, carry); t0 = h.t0.values
            for w, (a0, b0) in W.items():
                a, b = ts(a0), ts(b0) + 86400; r = (t0 >= a) & (t0 < b); Lw, Sw, Gw = L[r].copy(), S[r].copy(), Gr[r].copy(); bad = X[r] > b; Lw[bad] = np.nan; Sw[bad] = np.nan; Gw[bad] = np.nan
                parts[w].append((Fm[r], Lw, Sw, (t0[r] // (7 * 86400)).astype(np.int32), np.full(r.sum(), mi, np.int16), Gw))
        for w in parts:
            P = parts[w]; seg = np.cumsum([0] + [len(p[0]) for p in P]); setattr(self, w, Win(*[np.concatenate([p[i] for p in P]) for i in range(6)], seg))
        self.q = {}                                                               # per-feature threshold tables from window A only
        for f in FEATS:
            if f == "hour": self.q[f] = [float(x) for x in HOUR_LV]
            elif f == "dow": self.q[f] = [float(x) for x in DOW_LV]
            else:
                v = self.a.X[:, FI[f]]; v = v[np.isfinite(v)]; self.q[f] = [float(x) for x in np.quantile(v, LEVELS)] if len(v) else [0.0] * len(LEVELS)

    @staticmethod
    def shuffle(hs, seed):
        """Placebo: whole bars (gap, open-to-close, open-to-low) shuffled by ONE common permutation of the class calendar; spreads (relative) stay at their timestamps."""
        master = np.array(sorted(set().union(*[set(h.t0.values) for h in hs.values()]))); pos = {t: k for k, t in enumerate(master)}; n = len(master)
        perm = np.random.default_rng(seed * 7919 + zlib.crc32(str(len(hs)).encode()) % 1000).permutation(n); out = {}
        for m, h in hs.items():
            idx = np.array([pos[t] for t in h.t0.values]); bo, bc, bl, ao = h.bo.values, h.bc.values, h.bl.values, h.ao.values
            gap = np.zeros(len(h)); gap[1:] = np.log(bo[1:] / bc[:-1]); intra = np.log(bc / bo); low = np.minimum(np.log(bl / bo), np.minimum(intra, 0.0)); spr = (ao - bo) / bo
            G, I, Lw = np.zeros(n), np.zeros(n), np.zeros(n); G[idx], I[idx], Lw[idx] = gap, intra, low
            G2, I2, L2 = G[perm][idx], I[perm][idx], Lw[perm][idx]; G2[0] = 0.0
            logc = np.log(bc[0]) + np.cumsum(G2 + I2); logo = logc - I2; o = np.exp(logo); ns = h.copy()
            ns["bo"], ns["bc"], ns["bl"], ns["ao"] = o, np.exp(logc), o * np.exp(L2), o * (1 + spr); out[m] = ns
        return out


if __name__ == "__main__":
    for cls in P3.CLASSES:
        s = Stack(cls); print(f"{cls}: {len(s.markets)} markets | A rows {len(s.a.X):,} B rows {len(s.b.X):,} VAL rows {len(s.val.X):,}")
