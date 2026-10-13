"""v5 data (PREREG_V5_PROP.md): hourly OHLC bars of both sides, ~41 causal features (price, intrabar structure, macro event calendar, daily macro regime), forward returns, stacked per class.
   python -m mt5broker.self_improving.freeform.ff5_data     (builds caches, prints sizes)"""
from __future__ import annotations

import pickle
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.self_improving import platform_v3 as P3

DATA = P3.DATA
CACHE = Path("D:/finance/scratch/si_cache")
MACRO = Path("D:/finance/data_macro")
HS = (1, 2, 4, 8, 24, 48, 96)
LEVELS = (0.03, 0.10, 0.25, 0.50, 0.75, 0.90, 0.97)
HOUR_LV = (0, 3, 6, 9, 12, 15, 18, 21); DOW_LV = (0, 1, 2, 3, 4)
WA = ("2022-01-01", "2023-06-30"); WB = ("2023-07-01", "2024-12-31"); VAL = ("2025-01-01", "2025-12-31")
OLD = ["z1", "z2", "z4", "z8", "z24", "z72", "z120", "rsi4", "rsi14", "ma24", "ma120", "ma480", "vr24", "vr120", "sprel", "pos24", "pos120", "run", "hour", "dow", "cs24", "cs120"]
INTRA = ["rng1", "clv", "upsh", "lowsh", "pk24", "spvar", "actrel"]
EVENT = ["cpi_to", "cpi_since", "nfp_to", "nfp_since", "fomc_to", "fomc_since", "any_to", "any_since"]
DAILY = ["vix_rank", "vix_chg5", "curve_chg5", "dxy_chg5"]
FEATS = OLD + INTRA + EVENT + DAILY
FI = {f: i for i, f in enumerate(FEATS)}
EVENT_TIME = {"NFP": (8, 30), "CPI": (8, 30), "FOMC": (14, 0)}              # New York wall time


def ts(s): return int(pd.Timestamp(s).value // 10**9)               # server-local naive epoch, like the data's t


def server_s(day, hh, mm):
    t = pd.Timestamp(f"{day} {hh:02d}:{mm:02d}").tz_localize("America/New_York").tz_convert("Europe/Athens").tz_localize(None)
    return int((t - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1))


def events():
    cal = pd.read_csv(MACRO / "event_calendar.csv"); out = {}
    for k, (hh, mm) in EVENT_TIME.items(): out[k] = np.array(sorted(server_s(d, hh, mm) for d in cal[cal.kind == k].date))
    out["ANY"] = np.array(sorted(np.concatenate([out[k] for k in EVENT_TIME]))); return out


def daily_macro():
    def rd(p, c): s = pd.read_csv(p); s.index = pd.to_datetime(s.observation_date); return pd.to_numeric(s[c], errors="coerce").dropna()
    vix, d10, d2, dxy = rd(MACRO / "VIXCLS.csv", "VIXCLS"), rd(MACRO / "DGS10.csv", "DGS10"), rd(MACRO / "DGS2.csv", "DGS2"), rd(MACRO / "alt/DTWEXBGS.csv", "DTWEXBGS")
    df = pd.DataFrame({"vix": vix}).join(pd.DataFrame({"d10": d10, "d2": d2, "dxy": dxy}), how="outer").sort_index().ffill()
    out = pd.DataFrame(index=df.index)
    out["vix_rank"] = df.vix.rolling(250, min_periods=100).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    out["vix_chg5"] = df.vix.pct_change(5); out["curve_chg5"] = (df.d10 - df.d2).diff(5); out["dxy_chg5"] = df.dxy.pct_change(5); return out


def hourly_full(m):
    f = CACHE / f"hf_{m}.pkl"
    if f.exists(): return pickle.load(open(f, "rb"))
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "sp", "ao", "ah", "al", "ac"]).sort_values("t").drop_duplicates("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo)]; d["k"] = d.t // 3600; d["mv"] = (d.bh > d.bl).astype(np.int8)
    g = d.groupby("k").agg(bo=("bo", "first"), bh=("bh", "max"), bl=("bl", "min"), bc=("bc", "last"), ao=("ao", "first"), ah=("ah", "max"), al=("al", "min"), ac=("ac", "last"),
                           spmax=("sp", "max"), spmean=("sp", "mean"), act=("mv", "sum"), n=("t", "count"))
    g = g[g.n >= 20]; g["t0"] = g.index.values * 3600; g = g.reset_index(drop=True); pickle.dump(g, open(f, "wb")); return g


def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)


def market_features(h, ev, dm):
    c = h.bc; lr = np.log(c).diff(); sd1 = lr.rolling(240, min_periods=120).std(); out = pd.DataFrame(index=h.index)
    for k in (1, 2, 4, 8, 24, 72, 120): out[f"z{k}"] = np.log(c / c.shift(k)) / (sd1 * np.sqrt(k))
    out["rsi4"], out["rsi14"] = rsi(c, 4), rsi(c, 14)
    for k in (24, 120, 480): out[f"ma{k}"] = (c / c.rolling(k).mean() - 1) / (sd1 * np.sqrt(k))
    out["vr24"] = lr.rolling(24).std() / sd1; out["vr120"] = lr.rolling(120).std() / sd1
    sp = (h.ao - h.bo) / h.bo; out["sprel"] = sp / sp.rolling(480, min_periods=120).median()
    for k in (24, 120): lo, hi = c.rolling(k).min(), c.rolling(k).max(); out[f"pos{k}"] = (c - lo) / (hi - lo)
    up = (lr > 0).astype(int).replace(0, -1); grp = (up != up.shift()).cumsum(); out["run"] = up.groupby(grp).cumsum()
    out["hour"] = (h.t0 // 3600) % 24; out["dow"] = ((h.t0 // 86400) + 3) % 7
    rng = (h.bh - h.bl).replace(0, np.nan); lrg = np.log(h.bh / h.bl)
    out["rng1"] = lrg / sd1; out["clv"] = (h.bc - h.bl) / rng
    out["upsh"] = (h.bh - np.maximum(h.bo, h.bc)) / rng; out["lowsh"] = (np.minimum(h.bo, h.bc) - h.bl) / rng
    out["pk24"] = np.sqrt((lrg ** 2).rolling(24).mean() / (4 * np.log(2))) / sd1
    out["spvar"] = (h.spmax / h.spmean.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    af = h.act / h.n; out["actrel"] = af / af.rolling(240, min_periods=60).median()
    tc = (h.t0.values + 3600).astype(np.int64)                               # the signal is read at the bar close
    for k, nm in (("CPI", "cpi"), ("NFP", "nfp"), ("FOMC", "fomc"), ("ANY", "any")):
        E = ev[k]; i = np.searchsorted(E, tc, side="left"); j = np.searchsorted(E, tc, side="right") - 1
        nxt = np.where(i < len(E), (E[np.minimum(i, len(E) - 1)] - tc) / 3600.0, 72.0); prv = np.where(j >= 0, (tc - E[np.maximum(j, 0)]) / 3600.0, 72.0)
        out[f"{nm}_to"] = np.minimum(nxt, 72.0); out[f"{nm}_since"] = np.minimum(prv, 72.0)
    dates = pd.to_datetime(pd.Series(tc // 86400, dtype="int64") * 86400, unit="s").dt.normalize() - pd.Timedelta(days=1)       # one-day lag: yesterday's value
    lag = dm.reindex(dm.index.union(pd.DatetimeIndex(sorted(set(dates)))).sort_values()).ffill().reindex(pd.DatetimeIndex(dates.values))
    for f in DAILY: out[f] = lag[f].values
    out["sd1"] = sd1; return out


def fwd(h, carry):
    n = len(h); t0 = h.t0.values; ao, bo, bc = h.ao.values, h.bo.values, h.bc.values; sp = ao - bo; L = np.full((n, len(HS)), np.nan, np.float32); S = L.copy(); X = np.full((n, len(HS)), np.nan); G = L.copy()
    for j, H in enumerate(HS):
        if n <= H + 1: continue
        i = np.arange(0, n - H - 1); e, x = i + 1, i + H
        cost = carry * 1e-4 * (t0[x] - t0[e] + 3600) / 86400.0
        L[i, j] = bc[x] / ao[e] - 1 - cost; S[i, j] = bo[e] / (bc[x] + sp[x]) - 1 - cost; X[i, j] = t0[x] + 3600; G[i, j] = bc[x] / bo[e] - 1      # gross = bid-to-bid
    return L, S, X, G


class Win:
    def __init__(self, X, Yl, Ys, week, mkt, Yg, t0, sd1, seg): self.X, self.Yl, self.Ys, self.week, self.mkt, self.Yg, self.t0, self.sd1, self.seg = X, Yl, Ys, week, mkt, Yg, t0, sd1, seg


class Stack:
    def __init__(self, cls, placebo=None):
        info = P3.CLASSES[cls]; carry = info["carry"]; hs = {}; ev = events(); dm = daily_macro()
        for m in info["members"]:
            h = hourly_full(m)
            if len(h) > 12000: hs[m] = h
        if placebo is not None: hs = self.shuffle(hs, placebo)
        feats = {m: market_features(h, ev, dm) for m, h in hs.items()}
        for k in (24, 120):
            W = pd.DataFrame({m: pd.Series(feats[m][f"z{k}"].values, index=hs[m].t0.values) for m in hs}); R = W.rank(axis=1, pct=True); R[W.notna().sum(axis=1) < 3] = np.nan
            for m in hs: feats[m][f"cs{k}"] = R[m].reindex(hs[m].t0.values).values
        self.cls, self.markets, self.frames = cls, list(hs), hs; W = {"a": WA, "b": WB, "val": VAL}; parts = {w: [] for w in W}
        for mi, m in enumerate(hs):
            h = hs[m]; Fm = feats[m][FEATS].values.astype(np.float32); sd1 = feats[m]["sd1"].values.astype(np.float32); L, S, X, Gr = fwd(h, carry); t0 = h.t0.values
            for w, (a0, b0) in W.items():
                a, b = ts(a0), ts(b0) + 86400; r = (t0 >= a) & (t0 < b); Lw, Sw, Gw = L[r].copy(), S[r].copy(), Gr[r].copy(); bad = X[r] > b; Lw[bad] = np.nan; Sw[bad] = np.nan; Gw[bad] = np.nan
                parts[w].append((Fm[r], Lw, Sw, (t0[r] // (7 * 86400)).astype(np.int32), np.full(r.sum(), mi, np.int16), Gw, t0[r].astype(np.int64), sd1[r]))
        for w in parts:
            P = parts[w]; seg = np.cumsum([0] + [len(p[0]) for p in P]); setattr(self, w, Win(*[np.concatenate([p[i] for p in P]) for i in range(8)], seg))
        self.q = {}
        for f in FEATS:
            if f == "hour": self.q[f] = [float(x) for x in HOUR_LV]
            elif f == "dow": self.q[f] = [float(x) for x in DOW_LV]
            else:
                v = self.a.X[:, FI[f]]; v = v[np.isfinite(v)]; self.q[f] = [float(x) for x in np.quantile(v, LEVELS)] if len(v) else [0.0] * len(LEVELS)

    @staticmethod
    def shuffle(hs, seed):
        """Placebo: whole bars (gap, close, high, low relative to the open) shuffled by ONE common permutation of the class calendar; bid-ask offsets, spread statistics, activity and counts stay with the timestamp.
        The event calendar and the daily macro series are NOT shuffled (they are decoupled from the shuffled returns)."""
        master = np.array(sorted(set().union(*[set(h.t0.values) for h in hs.values()]))); pos = {t: k for k, t in enumerate(master)}; n = len(master)
        perm = np.random.default_rng(seed * 7919 + zlib.crc32(str(len(hs)).encode()) % 1000).permutation(n); out = {}
        for m, h in hs.items():
            idx = np.array([pos[t] for t in h.t0.values]); bo, bc, bh, bl = h.bo.values, h.bc.values, h.bh.values, h.bl.values
            gap = np.zeros(len(h)); gap[1:] = np.log(bo[1:] / bc[:-1]); rc = np.log(bc / bo); rh = np.log(bh / bo); rl = np.log(bl / bo)
            G, C, Hh, Ll = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n); G[idx], C[idx], Hh[idx], Ll[idx] = gap, rc, rh, rl
            G2, C2, H2, L2 = G[perm][idx], C[perm][idx], Hh[perm][idx], Ll[perm][idx]; G2[0] = 0.0
            logc = np.log(bc[0]) + np.cumsum(G2 + C2); o = np.exp(logc - C2); ns = h.copy()
            ns["bo"], ns["bc"], ns["bh"], ns["bl"] = o, np.exp(logc), o * np.exp(H2), o * np.exp(L2)
            for a, b in (("ao", "bo"), ("ah", "bh"), ("al", "bl"), ("ac", "bc")): ns[a] = ns[b] * (h[a].values / h[b].values)
            out[m] = ns
        return out


if __name__ == "__main__":
    for cls in P3.CLASSES:
        s = Stack(cls); X = s.a.X; print(f"{cls}: {len(s.markets)} markets | A rows {len(s.a.X):,} B {len(s.b.X):,} VAL {len(s.val.X):,} | features {len(FEATS)} | share finite per new feature: "
              + " ".join(f"{f}={np.isfinite(X[:, FI[f]]).mean():.2f}" for f in ("rng1", "actrel", "cpi_to", "vix_rank", "curve_chg5", "dxy_chg5")))
