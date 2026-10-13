"""v6 data (PREREG_V6_M1.md): M1 bid/ask OHLC of 46 symbols aggregated into 15-minute decision bars with M1-derived statistics, ~87 causal features
(price scales, micro-structure, time, daily levels, round numbers, candle / swing / FVG / order-block patterns on 15m and 60m, macro calendar, daily macro, crypto, cross-section).
   python -m mt5broker.self_improving.freeform.ff6_data     (builds caches, prints sizes)"""
from __future__ import annotations

import pickle
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.self_improving import platform_v3 as P3
from mt5broker.self_improving.freeform import ff5_data as F5

DATA = P3.DATA
CACHE = Path("D:/finance/scratch/si_cache"); MACRO = Path("D:/finance/data_macro")
BAR = 900
HS = (1, 2, 4, 8, 16, 32, 96, 192)                              # holding horizons in 15-minute bars (15 min .. 2 days)
LEVELS = F5.LEVELS; HOUR_LV = F5.HOUR_LV; DOW_LV = F5.DOW_LV; QMIN_LV = (0, 1, 2, 3)
CATLV = {"hour": HOUR_LV, "dow": DOW_LV, "qmin": QMIN_LV}
WA, WB, VAL = F5.WA, F5.WB, F5.VAL
PRICE = ["z1", "z2", "z4", "z8", "z16", "z32", "z96", "rsi14", "rsi60", "ma16", "ma96", "ma480", "vr16", "vr96", "pk96", "pos16", "pos96", "pos480"]
TIME = ["hour", "qmin", "dow"]
LEVELF = ["pdh_d", "pdl_d", "pdc_d", "dh_d", "dl_d"]
MICRO = ["sprel", "splrel", "actshare", "actrel", "mrng", "eff", "upshare", "r5z", "rvrat"]
RN = ["rn_dist", "rn_frac"]
PAT = [f"{n}{t}" for t in (15, 60) for n in ("b", "uw", "lw", "rz", "eng", "ins", "run")]
SWING = ["dsh15", "dsl15", "tr15", "dsh60", "dsl60", "tr60"]
FVG = ["fu15", "fua15", "fd15", "fda15", "fu60", "fua60", "fd60", "fda60"]
OB = ["obu15", "obd15"]
EVENT = F5.EVENT
DAILY = ["vix_rank", "vix_chg5", "curve_chg5", "dxy_chg5", "vix9r", "skew_rank"]
CRYPTO = ["fng", "fng_chg3", "stab_chg7", "fund_btc"]
CS = ["cs16", "cs96"]
FEATS = PRICE + TIME + LEVELF + MICRO + RN + PAT + SWING + FVG + OB + EVENT + DAILY + CRYPTO + CS
FI = {f: i for i, f in enumerate(FEATS)}
ts, events = F5.ts, F5.events


def daily_macro():
    base = F5.daily_macro()
    def rd(p, c, f="%m/%d/%Y"): s = pd.read_csv(p); s.index = pd.to_datetime(s["date"], format=f); return pd.to_numeric(s[c], errors="coerce").dropna()
    vix = pd.read_csv(MACRO / "VIXCLS.csv"); vix.index = pd.to_datetime(vix.observation_date); vix = pd.to_numeric(vix.VIXCLS, errors="coerce").dropna()
    v9 = rd(MACRO / "cboe/VIX9D.csv", "close"); sk = rd(MACRO / "cboe/SKEW.csv", "skew")
    fng = rd(MACRO / "alt/fng.csv", "fng", "%Y-%m-%d"); st = rd(MACRO / "alt/stablecoins.csv", "stable_usd", "%Y-%m-%d")
    fu = pd.read_csv(MACRO / "alt/funding_BTCUSDT.csv"); fu.index = pd.to_datetime(fu.time).dt.normalize(); fu = fu.rate.groupby(level=0).sum()
    idx = base.index.union(v9.index).union(sk.index).union(fng.index).union(st.index).union(fu.index).sort_values(); out = base.reindex(idx).ffill()
    out["vix9r"] = (v9.reindex(idx).ffill() / vix.reindex(idx).ffill())
    out["skew_rank"] = sk.reindex(idx).ffill().rolling(250, min_periods=100).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    f = fng.reindex(idx).ffill(); out["fng"] = f; out["fng_chg3"] = f.diff(3); out["stab_chg7"] = st.reindex(idx).ffill().pct_change(7); out["fund_btc"] = fu.reindex(idx).fillna(0.0).rolling(3, min_periods=1).sum()
    return out


def bars15(m):
    f = CACHE / f"b15_{m}.pkl"
    if f.exists(): return pickle.load(open(f, "rb"))
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "sp", "ao", "ah", "al", "ac"]).sort_values("t").drop_duplicates("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo) & (d.bh >= d.bl)].reset_index(drop=True); lc = np.log(d.bc)
    d["k"] = d.t // BAR; d["sq"] = lc.diff().fillna(0.0) ** 2; d["pkv"] = np.log(d.bh / d.bl) ** 2 / (4 * np.log(2)); d["mv"] = (d.bh > d.bl).astype(np.int8); d["up"] = (d.bc > d.bo).astype(np.int8)
    d["r5"] = (lc - lc.shift(5)).fillna(0.0); d["mr"] = np.log(d.bh / d.bl)
    g = d.groupby("k").agg(bo=("bo", "first"), bh=("bh", "max"), bl=("bl", "min"), bc=("bc", "last"), ao=("ao", "first"), ah=("ah", "max"), al=("al", "min"), ac=("ac", "last"),
                           rv=("sq", "sum"), pkv=("pkv", "sum"), act=("mv", "sum"), up=("up", "sum"), spm=("sp", "mean"), spmax=("sp", "max"), spl=("sp", "last"), r5=("r5", "last"), mrng=("mr", "max"), n=("t", "count"))
    g = g[g.n >= 5]; g["t0"] = g.index.values * BAR; g = g.reset_index(drop=True); pickle.dump(g, open(f, "wb")); return g


def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)


def htf(h, size):
    k = h.t0 // size; g = h.groupby(k).agg(o=("bo", "first"), h=("bh", "max"), l=("bl", "min"), c=("bc", "last")); g["end"] = (g.index.values + 1) * size; return g.reset_index(drop=True)


def asof(vals, end, D):
    j = np.searchsorted(end, D, side="right") - 1; out = np.where(j >= 0, np.asarray(vals, dtype=np.float64)[np.maximum(j, 0)], np.nan); return out


def patterns(o, h, l, c, unit):
    """Candle, swing, FVG and order-block features of a bar series, each value known at the END of its bar. unit = price x bar volatility (distance scale)."""
    rng = (h - l).replace(0, np.nan); body = (c - o).abs(); po, pc, ph, pl = o.shift(1), c.shift(1), h.shift(1), l.shift(1)
    out = {"b": body / rng, "uw": (h - np.maximum(o, c)) / rng, "lw": (np.minimum(o, c) - l) / rng, "rz": rng / rng.rolling(96, min_periods=48).median()}
    out["eng"] = np.where((c > o) & (pc < po) & (c >= po) & (o <= pc), 1.0, np.where((c < o) & (pc > po) & (c <= po) & (o >= pc), -1.0, 0.0))
    out["ins"] = ((h < ph) & (l > pl)).astype(float)
    up = (c > o).astype(int).replace(0, -1); grp = (up != up.shift()).cumsum(); out["run"] = up.groupby(grp).cumsum().clip(-8, 8)
    sh = h.rolling(7).max(); sl = l.rolling(7).min(); is_sh = (h.shift(3) == sh) & sh.notna(); is_sl = (l.shift(3) == sl) & sl.notna()
    shv = h.shift(3).where(is_sh); slv = l.shift(3).where(is_sl); lsh, lsl = shv.ffill(), slv.ffill()
    psh = shv.dropna().shift(1).reindex(shv.index).ffill(); psl = slv.dropna().shift(1).reindex(slv.index).ffill()
    out["dsh"] = (c - lsh) / unit; out["dsl"] = (c - lsl) / unit; out["tr"] = np.sign(lsh - psh).fillna(0) + np.sign(lsl - psl).fillna(0)
    fb = (l > h.shift(2)); seg = fb.cumsum(); lo_b = h.shift(2).where(fb).ffill(); runmin = l.groupby(seg).cummin(); age = seg.groupby(seg).cumcount()
    ok = (runmin > lo_b) & (age <= 96) & (seg > 0); out["fu"] = ((c - lo_b) / unit).where(ok); out["fua"] = age.where(ok).astype(float)
    fs = (h < l.shift(2)); seg2 = fs.cumsum(); hi_b = l.shift(2).where(fs).ffill(); runmax = h.groupby(seg2).cummax(); age2 = seg2.groupby(seg2).cumcount()
    ok2 = (runmax < hi_b) & (age2 <= 96) & (seg2 > 0); out["fd"] = ((hi_b - c) / unit).where(ok2); out["fda"] = age2.where(ok2).astype(float)
    disp = (out["rz"] > 1.5) & (out["b"] > 0.6); bull = disp & (c > o) & (pc < po); bear = disp & (c < o) & (pc > po)
    ou = ph.where(bull).ffill(); od = pl.where(bear).ffill(); ag_u = (bull.cumsum()).groupby(bull.cumsum()).cumcount(); ag_d = (bear.cumsum()).groupby(bear.cumsum()).cumcount()
    out["obu"] = ((c - ou) / unit).where(ag_u <= 192); out["obd"] = ((od - c) / unit).where(ag_d <= 192)
    return out


def market_features(h, ev, dm, is_crypto):
    c = h.bc; lr = np.log(c).diff(); sd = lr.rolling(384, min_periods=192).std(); out = pd.DataFrame(index=h.index); D = (h.t0.values + BAR).astype(np.int64)
    for k in (1, 2, 4, 8, 16, 32, 96): out[f"z{k}"] = np.log(c / c.shift(k)) / (sd * np.sqrt(k))
    out["rsi14"] = rsi(c, 14); b60 = htf(h, 3600); sd60 = np.log(b60.c).diff().rolling(96, min_periods=48).std(); out["rsi60"] = asof(rsi(b60.c, 14).values, b60.end.values, D)
    for k in (16, 96, 480): out[f"ma{k}"] = (c / c.rolling(k).mean() - 1) / (sd * np.sqrt(k))
    out["vr16"] = lr.rolling(16).std() / sd; out["vr96"] = lr.rolling(96).std() / sd; out["pk96"] = np.sqrt(h.pkv.rolling(96).mean()) / sd
    for k in (16, 96, 480): lo, hi = c.rolling(k).min(), c.rolling(k).max(); out[f"pos{k}"] = (c - lo) / (hi - lo)
    out["hour"] = (h.t0 // 3600) % 24; out["qmin"] = (h.t0 % 3600) // BAR; out["dow"] = ((h.t0 // 86400) + 3) % 7
    day = h.t0 // 86400; dg = h.groupby(day).agg(hi=("bh", "max"), lo=("bl", "min"), cl=("bc", "last")); pv = dg.shift(1); ddu = c * sd * np.sqrt(96)
    out["pdh_d"] = (c - day.map(pv.hi)) / ddu; out["pdl_d"] = (c - day.map(pv.lo)) / ddu; out["pdc_d"] = (c - day.map(pv.cl)) / ddu
    out["dh_d"] = (c - h.bh.groupby(day).cummax()) / ddu; out["dl_d"] = (c - h.bl.groupby(day).cummin()) / ddu
    nm = h.n.replace(0, np.nan); out["sprel"] = h.spm / h.spm.rolling(96, min_periods=48).median(); out["splrel"] = h.spl / h.spm.replace(0, np.nan)
    af = h.act / nm; out["actshare"] = af; out["actrel"] = af / af.rolling(96, min_periods=48).median(); out["mrng"] = h.mrng / h.mrng.rolling(96, min_periods=48).median()
    out["eff"] = lr.abs() / np.sqrt(h.rv.replace(0, np.nan)); out["upshare"] = h.up / nm; out["r5z"] = h.r5 / (sd * np.sqrt(5 / 15)); out["rvrat"] = h.rv / h.rv.rolling(96, min_periods=48).mean()
    step = 10.0 ** (np.floor(np.log10(c)) - 3) * 5; fr = (c / step) % 1; out["rn_frac"] = fr; out["rn_dist"] = np.minimum(fr, 1 - fr) * step / (c * sd)
    p15 = patterns(h.bo, h.bh, h.bl, h.bc, c * sd)
    for n in ("b", "uw", "lw", "rz", "eng", "ins", "run"): out[f"{n}15"] = np.asarray(p15[n], dtype=np.float64)
    out["dsh15"], out["dsl15"], out["tr15"] = p15["dsh"], p15["dsl"], p15["tr"]; out["fu15"], out["fua15"], out["fd15"], out["fda15"] = p15["fu"], p15["fua"], p15["fd"], p15["fda"]; out["obu15"], out["obd15"] = p15["obu"], p15["obd"]
    p60 = patterns(b60.o, b60.h, b60.l, b60.c, b60.c * sd60); e60 = b60.end.values
    for n in ("b", "uw", "lw", "rz", "eng", "ins", "run"): out[f"{n}60"] = asof(p60[n], e60, D)
    out["dsh60"], out["dsl60"], out["tr60"] = asof(p60["dsh"], e60, D), asof(p60["dsl"], e60, D), asof(p60["tr"], e60, D)
    out["fu60"], out["fua60"], out["fd60"], out["fda60"] = asof(p60["fu"], e60, D), asof(p60["fua"], e60, D), asof(p60["fd"], e60, D), asof(p60["fda"], e60, D)
    for k, nmn in (("CPI", "cpi"), ("NFP", "nfp"), ("FOMC", "fomc"), ("ANY", "any")):
        E = ev[k]; i = np.searchsorted(E, D, side="left"); j = np.searchsorted(E, D, side="right") - 1
        out[f"{nmn}_to"] = np.minimum(np.where(i < len(E), (E[np.minimum(i, len(E) - 1)] - D) / 3600.0, 72.0), 72.0); out[f"{nmn}_since"] = np.minimum(np.where(j >= 0, (D - E[np.maximum(j, 0)]) / 3600.0, 72.0), 72.0)
    dates = pd.to_datetime(pd.Series(D // 86400, dtype="int64") * 86400, unit="s").dt.normalize() - pd.Timedelta(days=1)
    lag = dm.reindex(dm.index.union(pd.DatetimeIndex(sorted(set(dates)))).sort_values()).ffill().reindex(pd.DatetimeIndex(dates.values))
    for f in DAILY: out[f] = lag[f].values
    for f in CRYPTO: out[f] = lag[f].values if is_crypto else np.nan
    out["sd"] = sd; return out


def fwd(h, carry):
    n = len(h); t0 = h.t0.values; ao, bo, bc, ac = h.ao.values, h.bo.values, h.bc.values, h.ac.values; L = np.full((n, len(HS)), np.nan, np.float32); S = L.copy(); X = np.full((n, len(HS)), np.nan); G = L.copy()
    for j, H in enumerate(HS):
        if n <= H + 1: continue
        i = np.arange(0, n - H - 1); e, x = i + 1, i + H
        cost = carry * 1e-4 * (t0[x] - t0[e] + BAR) / 86400.0
        L[i, j] = bc[x] / ao[e] - 1 - cost; S[i, j] = bo[e] / ac[x] - 1 - cost; X[i, j] = t0[x] + BAR; G[i, j] = bc[x] / bo[e] - 1
    return L, S, X, G


Win = F5.Win


class Stack:
    def __init__(self, cls, placebo=None):
        info = P3.CLASSES[cls]; carry = info["carry"]; hs = {}; ev = events(); dm = daily_macro()
        for m in info["members"]:
            h = bars15(m)
            if len(h) > 40000: hs[m] = h
        if placebo is not None: hs = self.shuffle(hs, placebo)
        feats = {m: market_features(h, ev, dm, cls == "crypto") for m, h in hs.items()}
        for k, nm in ((16, "cs16"), (96, "cs96")):
            W = pd.DataFrame({m: pd.Series(feats[m][f"z{k}"].values, index=hs[m].t0.values) for m in hs}); R = W.rank(axis=1, pct=True); R[W.notna().sum(axis=1) < 3] = np.nan
            for m in hs: feats[m][nm] = R[m].reindex(hs[m].t0.values).values
        self.cls, self.markets, self.frames = cls, list(hs), hs; W = {"a": WA, "b": WB, "val": VAL}; parts = {w: [] for w in W}
        for mi, m in enumerate(hs):
            h = hs[m]; Fm = feats[m][FEATS].values.astype(np.float32); sd1 = feats[m]["sd"].values.astype(np.float32); L, S, X, Gr = fwd(h, carry); t0 = h.t0.values
            for w, (a0, b0) in W.items():
                a, b = ts(a0), ts(b0) + 86400; r = (t0 >= a) & (t0 < b); Lw, Sw, Gw = L[r].copy(), S[r].copy(), Gr[r].copy(); bad = X[r] > b; Lw[bad] = np.nan; Sw[bad] = np.nan; Gw[bad] = np.nan
                parts[w].append((Fm[r], Lw, Sw, (t0[r] // (7 * 86400)).astype(np.int32), np.full(r.sum(), mi, np.int16), Gw, t0[r].astype(np.int64), sd1[r]))
        for w in parts:
            P = parts[w]; seg = np.cumsum([0] + [len(p[0]) for p in P]); setattr(self, w, Win(*[np.concatenate([p[i] for p in P]) for i in range(8)], seg))
        self.q = {}
        for f in FEATS:
            if f in CATLV: self.q[f] = [float(x) for x in CATLV[f]]
            else:
                v = self.a.X[:, FI[f]]; v = v[np.isfinite(v)]; self.q[f] = [float(x) for x in np.quantile(v, LEVELS)] if len(v) else [0.0] * len(LEVELS)

    @staticmethod
    def shuffle(hs, seed):
        """Placebo: whole 15-minute bars (gap, close, high, low relative to the open, and the M1-derived return statistics of the bar) moved by ONE common permutation of the class calendar;
        bid-ask offsets, spread statistics and minute counts stay with the timestamp. Patterns are recomputed on the shuffled bars."""
        master = np.array(sorted(set().union(*[set(h.t0.values) for h in hs.values()]))); pos = {t: k for k, t in enumerate(master)}; n = len(master)
        perm = np.random.default_rng(seed * 7919 + zlib.crc32(str(len(hs)).encode()) % 1000).permutation(n); out = {}
        mv = ("rv", "pkv", "act", "up", "r5", "mrng")
        for m, h in hs.items():
            idx = np.array([pos[t] for t in h.t0.values]); bo, bc, bh, bl = h.bo.values, h.bc.values, h.bh.values, h.bl.values
            gap = np.zeros(len(h)); gap[1:] = np.log(bo[1:] / bc[:-1]); comp = {"G": gap, "C": np.log(bc / bo), "H": np.log(bh / bo), "L": np.log(bl / bo)}
            for k in mv: comp[k] = h[k].values.astype(np.float64)
            sh = {}
            for k, v in comp.items(): a = np.zeros(n); a[idx] = v; sh[k] = a[perm][idx]
            sh["G"][0] = 0.0; logc = np.log(bc[0]) + np.cumsum(sh["G"] + sh["C"]); o = np.exp(logc - sh["C"]); ns = h.copy()
            ns["bo"], ns["bc"], ns["bh"], ns["bl"] = o, np.exp(logc), o * np.exp(sh["H"]), o * np.exp(sh["L"])
            for k in mv: ns[k] = sh[k]
            for a_, b_ in (("ao", "bo"), ("ah", "bh"), ("al", "bl"), ("ac", "bc")): ns[a_] = ns[b_] * (h[a_].values / h[b_].values)
            out[m] = ns
        return out


if __name__ == "__main__":
    import time
    for cls in P3.CLASSES:
        t0 = time.time(); s = Stack(cls); X = s.a.X
        print(f"{cls}: {len(s.markets)} markets | A rows {len(s.a.X):,} B {len(s.b.X):,} VAL {len(s.val.X):,} | features {len(FEATS)} | finite share: " + " ".join(f"{f}={np.isfinite(X[:, FI[f]]).mean():.2f}" for f in ("z96", "rsi60", "pdh_d", "dsh60", "fu15", "fd60", "obu15", "vix9r", "fng", "cs96")) + f" | {time.time()-t0:.0f}s", flush=True)
