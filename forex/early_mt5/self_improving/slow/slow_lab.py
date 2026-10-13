"""New-information lab at horizons of 1, 5 and 20 trading days: COT positioning, macro-release surprise proxies, macro regime, lagged cross-asset returns, price (PREREG_SLOW_INFO.md).
   python -m mt5broker.self_improving.slow.slow_lab [--placebo 71] [--jobs 8] [--tag NAME] [--drop cot,surp,cross,macro]"""
import sys
ARGV = sys.argv[1:]

import argparse
import glob
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import xgboost as xgb

from mt5broker.self_improving import platform_v3 as P3
from mt5broker.self_improving.freeform import ff5_data as F5, ff6_data as D6

LEDGERS = Path("D:/finance/si_ledgers"); LEDGERS.mkdir(parents=True, exist_ok=True)
DEC_T0 = 11 * 3600 + 45 * 60                                              # decision bar starts 11:45 server time, ends 12:00
HL = (1, 5, 20); WINS = {"a": D6.WA, "b": D6.WB, "val": D6.VAL}
QS = (0.50, 0.70, 0.80, 0.90, 0.95); N_MIN, CL_MIN, BP_MIN = 100, 20, 3.0; BONF = 0.05 / 12
COT = {"EUR": "099741", "GBP": "096742", "JPY": "097741", "AUD": "232741", "CAD": "090741", "CHF": "092741", "NZD": "112741"}
COT_MKT = {"XAUUSD": "088691", "XAGUSD": "084691", "WTI": "067411", "SP": "13874A", "NSDQ": "20974+", "DOW": "12460+", "NIKKEI": "240743", "BTCUSD": "133741", "ETHUSD": "146021"}
YAH = {"ES": "ES_F", "NQ": "NQ_F", "DIA": "DIA", "EWG": "EWG", "EWJ": "EWJ", "ZN": "ZN_F", "TLT": "TLT", "E6": "6E_F", "J6": "6J_F", "GC": "GC_F", "SI": "SI_F", "CL": "CL_F", "HG": "HG_F", "NG": "NG_F", "BTC": "BTC-USD"}
PRICE = ["z1", "z5", "z20", "z60", "ma20", "ma60", "ma120", "rsi14", "pos60", "vr5"]
COTF = ["cot_nc", "cot_nc_pct", "cot_nc_c1", "cot_nc_c4", "cot_c_pct", "cot_c_c4"]
SURP = ["s_nfp", "s_nfp_d", "s_unr", "s_unr_d", "s_cpi", "s_cpi_d", "s_fomc", "s_fomc_d"]
MACRO = ["vix_rank", "vix_chg5", "curve_chg5", "dxy_chg5", "vix9r", "skew_rank", "cpi_to", "cpi_since", "nfp_to", "nfp_since", "fomc_to", "fomc_since"]
CROSS = [f"x_{k}_{h}" for k in YAH for h in ("r1", "r5")]
TIMEF = ["dow", "dom"]
GROUPS = {"cot": COTF, "surp": SURP, "macro": MACRO, "cross": CROSS}
FEATS = PRICE + COTF + SURP + MACRO + CROSS + TIMEF


def cot_tables():
    d = pd.concat([pd.read_csv(f, low_memory=False) for f in sorted(glob.glob("D:/finance/data_macro/cot/deacot20*/annual.txt"))], ignore_index=True)
    d["code"] = d["CFTC Contract Market Code"].astype(str).str.strip(); d["date"] = pd.to_datetime(d["As of Date in Form YYYY-MM-DD"]); oi = pd.to_numeric(d["Open Interest (All)"], errors="coerce")
    d["nc"] = (pd.to_numeric(d["Noncommercial Positions-Long (All)"], errors="coerce") - pd.to_numeric(d["Noncommercial Positions-Short (All)"], errors="coerce")) / oi
    d["c"] = (pd.to_numeric(d["Commercial Positions-Long (All)"], errors="coerce") - pd.to_numeric(d["Commercial Positions-Short (All)"], errors="coerce")) / oi
    out = {}
    for code in set(COT.values()) | set(COT_MKT.values()):
        s = d[d.code == code].drop_duplicates("date").sort_values("date").set_index("date")[["nc", "c"]].dropna()
        if len(s) < 100: continue
        pct = lambda x: x.rolling(156, min_periods=52).apply(lambda w: (w <= w[-1]).mean(), raw=True)
        t = pd.DataFrame({"nc": s.nc, "nc_pct": pct(s.nc), "nc_c1": s.nc.diff(1), "nc_c4": s.nc.diff(4), "c_pct": pct(s.c), "c_c4": s.c.diff(4)})
        t["avail"] = [F5.server_s((x + pd.Timedelta(days=3)).strftime("%Y-%m-%d"), 15, 30) for x in t.index]          # Tuesday as-of, released Friday 15:30 New York
        out[code] = t
    return out


def cot_for(market, cot):
    """Per-report positioning of a market (a pair uses base minus quote); returns a DataFrame indexed by availability time (server epoch)."""
    if market in COT_MKT:
        t = cot.get(COT_MKT[market]); return None if t is None else t.rename(columns={"nc": "cot_nc", "nc_pct": "cot_nc_pct", "nc_c1": "cot_nc_c1", "nc_c4": "cot_nc_c4", "c_pct": "cot_c_pct", "c_c4": "cot_c_c4"}).set_index("avail")
    if len(market) == 6 and market[:3] in COT | {"USD": ""} and market[3:] in COT | {"USD": ""}:
        base, quote = market[:3], market[3:]; parts = []
        for ccy, sg in ((base, 1.0), (quote, -1.0)):
            if ccy in COT and COT[ccy] in cot: t = cot[COT[ccy]].set_index("avail")[["nc", "nc_pct", "nc_c1", "nc_c4", "c_pct", "c_c4"]] * sg; parts.append(t)
        if not parts: return None
        idx = sorted(set().union(*[set(p.index) for p in parts])); acc = sum(p.reindex(idx).ffill().fillna(0.0) for p in parts)
        return acc.rename(columns={"nc": "cot_nc", "nc_pct": "cot_nc_pct", "nc_c1": "cot_nc_c1", "nc_c4": "cot_nc_c4", "c_pct": "cot_c_pct", "c_c4": "cot_c_c4"})
    return None


def asof_vals(index_sec, table, cols, dsec):
    if table is None: return {c: np.full(len(dsec), np.nan) for c in cols}
    ix = np.asarray(table.index, dtype=np.int64); j = np.searchsorted(ix, dsec, side="right") - 1
    return {c: np.where(j >= 0, table[c].values[np.maximum(j, 0)], np.nan) for c in cols}


def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)


def surprise_tables():
    s = pd.read_csv("D:/finance/data_macro/alfred/surprises.csv"); out = {}
    for kind, nm, hh, mm in (("NFP", "s_nfp", 8, 30), ("UNRATE", "s_unr", 8, 30), ("CPI", "s_cpi", 8, 30), ("FOMC", "s_fomc", 14, 0)):
        k = s[s.kind == kind].sort_values("release_date"); out[nm] = pd.DataFrame({"v": k.value.values, "t": [F5.server_s(d, hh, mm) for d in k.release_date]}).set_index("t")
    return out


def yahoo():
    out = {}
    for k, f in YAH.items():
        d = pd.read_csv(f"D:/finance/data_macro/yahoo/{f}.csv"); d.index = pd.to_datetime(d.Date); c = pd.to_numeric(d.Close, errors="coerce").dropna()
        out[k] = pd.DataFrame({"r1": c.pct_change(1), "r5": c.pct_change(5)})
    return out


def market_rows(m, h, carry, ctx):
    wd = ((h.t0 // 86400) + 3) % 7; dec = np.nonzero(((h.t0 % 86400) == DEC_T0).values & (wd < 5).values)[0]; dec = dec[dec + 1 < len(h)]
    if len(dec) < 300: return None
    bo, bc, ao, ac, t0 = h.bo.values, h.bc.values, h.ao.values, h.ac.values, h.t0.values; c = pd.Series(bc[dec]); r = np.log(c).diff(); sd = r.rolling(60, min_periods=30).std()
    X = pd.DataFrame(index=np.arange(len(dec)))
    for k in (1, 5, 20, 60): X[f"z{k}"] = (np.log(c / c.shift(k)) / (sd * np.sqrt(k))).values
    for k in (20, 60, 120): X[f"ma{k}"] = ((c / c.rolling(k).mean() - 1) / (sd * np.sqrt(k))).values
    X["rsi14"] = rsi(c, 14).values; lo, hi = c.rolling(60).min(), c.rolling(60).max(); X["pos60"] = ((c - lo) / (hi - lo)).values; X["vr5"] = (r.rolling(5).std() / r.rolling(60).std()).values
    dsec = (t0[dec] + 900).astype(np.int64)                                              # decision instant = the bar close, server epoch
    ct = cot_for(m, ctx["cot"]);
    for k, v in asof_vals(None, ct, COTF, dsec).items(): X[k] = v
    for nm, t in ctx["surp"].items():
        ix = np.asarray(t.index, dtype=np.int64); j = np.searchsorted(ix, dsec, side="right") - 1; X[nm] = np.where(j >= 0, t.v.values[np.maximum(j, 0)], np.nan); X[nm + "_d"] = np.where(j >= 0, np.minimum((dsec - ix[np.maximum(j, 0)]) / 86400.0, 45.0), 45.0)
    dts = pd.to_datetime(dsec, unit="s").normalize(); lag = ctx["dm"].reindex(ctx["dm"].index.union(dts - pd.Timedelta(days=2)).sort_values()).ffill().reindex(dts - pd.Timedelta(days=2))
    for f in ("vix_rank", "vix_chg5", "curve_chg5", "dxy_chg5", "vix9r", "skew_rank"): X[f] = lag[f].values
    for kk, nm in (("CPI", "cpi"), ("NFP", "nfp"), ("FOMC", "fomc")):
        E = ctx["ev"][kk]; i = np.searchsorted(E, dsec, side="left"); j = np.searchsorted(E, dsec, side="right") - 1
        X[f"{nm}_to"] = np.minimum(np.where(i < len(E), (E[np.minimum(i, len(E) - 1)] - dsec) / 86400.0, 30.0), 30.0); X[f"{nm}_since"] = np.minimum(np.where(j >= 0, (dsec - E[np.maximum(j, 0)]) / 86400.0, 30.0), 30.0)
    prev = dts - pd.Timedelta(days=1)
    for k, t in ctx["yah"].items():
        a = t.reindex(t.index.union(prev).sort_values()).ffill().reindex(prev); X[f"x_{k}_r1"] = a.r1.values; X[f"x_{k}_r5"] = a.r5.values
    X["dow"] = dts.dayofweek.values; X["dom"] = dts.day.values
    L = np.full((len(dec), 3), np.nan); S = L.copy(); G = L.copy(); XT = np.full((len(dec), 3), np.nan)
    for j, H in enumerate(HL):
        n = len(dec) - H
        if n <= 0: continue
        e = dec[:n] + 1; x = dec[H:]                                                      # entry: next bar open; exit: close of the decision bar H decisions later
        cost = carry * 1e-4 * (t0[x] + 900 - t0[e]) / 86400.0
        L[:n, j] = bc[x] / ao[e] - 1 - cost; S[:n, j] = bo[e] / ac[x] - 1 - cost; G[:n, j] = bc[x] / bo[e] - 1; XT[:n, j] = t0[x] + 900
    return X[FEATS].values.astype(np.float32), L, S, G, XT, dsec


def build_class(cls, placebo, ctx):
    carry = P3.CLASSES[cls]["carry"]; hs = {}
    for m in P3.CLASSES[cls]["members"]:
        h = D6.bars15(m)
        if len(h) > 40000: hs[m] = h
    if placebo is not None: hs = None
    parts = {w: [] for w in WINS}
    for mi, m in enumerate(P3.CLASSES[cls]["members"]):
        h = D6.bars15(m)
        if len(h) <= 40000: continue
        res = market_rows(m, h, carry, ctx)
        if res is None: continue
        X, L, S, G, XT, dsec = res
        for w, (a0, b0) in WINS.items():
            a, b = F5.ts(a0), F5.ts(b0) + 86400; r = (dsec >= a) & (dsec < b); idx = np.nonzero(r)[0]
            if len(idx) == 0: continue
            Lw, Sw, Gw = L[idx].copy(), S[idx].copy(), G[idx].copy(); bad = XT[idx] > b; Lw[bad] = np.nan; Sw[bad] = np.nan; Gw[bad] = np.nan
            sdv = pd.Series(np.log(h.bc.values[np.nonzero(((h.t0 % 86400) == DEC_T0).values)[0]])).diff().rolling(60, min_periods=30).std().values
            parts[w].append(dict(X=X[idx], L=Lw, S=Sw, G=Gw, pos=np.arange(len(idx)), week=(dsec[idx] // (7 * 86400)).astype(np.int32), mkt=np.full(len(idx), mi, np.int16), day=(dsec[idx] // 86400).astype(np.int32)))
    data = {w: {k: np.concatenate([p[k] for p in P]) for k in P[0]} for w, P in parts.items()}
    if placebo is not None:                                                            # labels circularly shifted by a common fraction of the timeline; features untouched
        frac = 0.15 + 0.7 * np.random.default_rng(placebo).random()
        for w in data:
            d = data[w]
            for mi in np.unique(d["mkt"]):
                ix = np.nonzero(d["mkt"] == mi)[0]; k = int(len(ix) * frac)
                for key in ("L", "S", "G"): d[key][ix] = np.roll(d[key][ix], k, axis=0)
    return data


def cluster(ex, week):
    n = len(ex)
    if n < 30: return n, 0, np.nan, 1.0
    m = ex.mean(); wk = week - week.min(); cnt = np.bincount(wk); res = np.bincount(wk, weights=ex - m); cl = int((cnt > 0).sum())
    if cl < 5: return n, cl, np.nan, 1.0
    se = np.sqrt((res ** 2).sum() * cl / (cl - 1)) / n
    if se == 0: return n, cl, np.nan, 1.0
    z = m / se; return n, cl, float(z), float(stats.t.sf(z, cl - 1))


def pick(d, pred, hj, tau):
    H = HL[hj]; grid = (d["pos"] % H == 0) & np.isfinite(d["G"][:, hj]); side = np.sign(pred); sel = grid & (np.abs(pred) >= tau) & (side != 0)
    net = np.where(side > 0, d["L"][:, hj], d["S"][:, hj]); g = d["G"][:, hj]; gs = np.where(side > 0, g, 1.0 / (1.0 + g) - 1.0); return sel, side, net, gs, grid


def run_cell(data, hj, jobs, cols):
    A, B, V = data["a"], data["b"], data["val"]; Xs = lambda d: d["X"][:, cols]; sc = np.nanstd(A["G"][:, hj]); y = lambda d: np.clip(d["G"][:, hj] / sc, -8, 8)
    ia, ib = np.isfinite(y(A)), np.isfinite(y(B))
    m = xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.7, colsample_bytree=0.5, min_child_weight=40, reg_lambda=10.0, tree_method="hist", max_bin=64, n_jobs=jobs, early_stopping_rounds=30, eval_metric="rmse")
    m.fit(Xs(A)[ia], y(A)[ia], eval_set=[(Xs(B)[ib], y(B)[ib])], verbose=False); pb, pv = m.predict(Xs(B)), m.predict(Xs(V)); best = None
    for q in QS:
        selg = (B["pos"] % HL[hj] == 0) & ib; tau = float(np.quantile(np.abs(pb[selg]), q)); sel, side, net, gs, grid = pick(B, pb, hj, tau)
        if sel.sum() >= N_MIN:
            mn = float(np.nanmean(net[sel]))
            if best is None or mn > best[1]: best = (tau, mn, q)
    if best is None: best = (float(np.quantile(np.abs(pb[(B["pos"] % HL[hj] == 0) & ib]), 0.5)), np.nan, 0.5)
    tau, bmean, q = best; res = dict(tau_q=q, trees=int(m.best_iteration + 1), B_net_bp=1e4 * bmean if np.isfinite(bmean) else np.nan)
    for nm, d, p in (("B", B, pb), ("VAL", V, pv)):
        ok = np.isfinite(y(d)); res[f"{nm}_ic"] = float(stats.spearmanr(p[ok], y(d)[ok])[0])
        sel, side, net, gs, grid = pick(d, p, hj, tau)
        if sel.sum() == 0: res.update({f"{nm}_n": 0, f"{nm}_cl": 0, f"{nm}_net_bp": np.nan, f"{nm}_z": np.nan, f"{nm}_p": 1.0}); continue
        base = {}
        for s_ in (1, -1):
            g = d["G"][:, hj]; gg = g if s_ > 0 else 1.0 / (1.0 + g) - 1.0; okb = grid & np.isfinite(gg); nm_ = int(d["mkt"].max()) + 1
            base[s_] = np.bincount(d["mkt"][okb], weights=gg[okb], minlength=nm_) / np.maximum(np.bincount(d["mkt"][okb], minlength=nm_), 1)
        mk = d["mkt"][sel]; sd_ = side[sel]; ex = gs[sel] - np.where(sd_ > 0, base[1][mk], base[-1][mk]); n, cl, z, p_ = cluster(ex, d["week"][sel])
        res.update({f"{nm}_n": int(n), f"{nm}_cl": int(cl), f"{nm}_net_bp": 1e4 * float(np.nanmean(net[sel])), f"{nm}_z": z, f"{nm}_p": p_})
    res["pass_"] = bool(res["VAL_n"] >= N_MIN and res["VAL_cl"] >= CL_MIN and res["VAL_net_bp"] >= BP_MIN and res["VAL_p"] < BONF); return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--placebo", type=int, default=None); ap.add_argument("--jobs", type=int, default=8); ap.add_argument("--tag", default=None); ap.add_argument("--drop", default=""); ap.add_argument("--classes", default="fx,idx,cmd,crypto"); a = ap.parse_args(ARGV)
    try:
        import ctypes; ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception: pass
    drop = set(sum((GROUPS[g] for g in a.drop.split(",") if g), [])); cols = [i for i, f in enumerate(FEATS) if f not in drop]; name = a.tag or (f"placebo{a.placebo}" if a.placebo is not None else "real")
    ctx = dict(cot=cot_tables(), surp=surprise_tables(), dm=D6.daily_macro(), ev=F5.events(), yah=yahoo()); rows = []; t00 = time.time()
    for cls in a.classes.split(","):
        data = build_class(cls, a.placebo, ctx); print(f"[{cls}] rows " + " ".join(f"{w}={len(data[w]['pos']):,}" for w in data) + f" | finite cot {np.isfinite(data['a']['X'][:, FEATS.index('cot_nc_pct')]).mean():.2f} surp {np.isfinite(data['a']['X'][:, FEATS.index('s_nfp')]).mean():.2f}", flush=True)
        for hj, H in enumerate(HL):
            r = run_cell(data, hj, a.jobs, cols); r.update(cls=cls, H=H); rows.append(r)
            print(f"[{cls} H={H}d] IC B {r['B_ic']:+.4f} VAL {r['VAL_ic']:+.4f} | trees {r['trees']} | B net {r['B_net_bp']:+.1f}bp | VAL n={r['VAL_n']} cl={r['VAL_cl']} net {r['VAL_net_bp']:+.1f}bp z={r['VAL_z']:.2f} p={r['VAL_p']:.3f} | pass={r['pass_']}", flush=True)
    out = pd.DataFrame(rows); out.to_csv(LEDGERS / f"SLOW_{name}.csv", index=False)
    print(f"DONE {name}: cells passing {int(out.pass_.sum())} of {len(out)} | max VAL IC {out.VAL_ic.max():+.4f} | max VAL net {out.VAL_net_bp.max():+.1f} bp | max VAL z {out.VAL_z.max():.2f} | {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    main()
