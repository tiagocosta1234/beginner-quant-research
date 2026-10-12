"""ICT: liquidity sweeps, fair value gaps and killzones as exact rules over every MT5 broker symbol (PREREG_ICT_SCAN.md).   env ICT=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from pathlib import Path
from mt5broker.ea_research import setup_scan as SC

DATA = Path(__file__).resolve().parents[1] / "data_mt5"; ALL = SC.ALL; SLIPPTS = float(os.environ.get("ICT_SLIP", "0"))                          # points of slippage against us on stop and time exits (market orders)
EPOCH = pd.Timestamp("1970-01-01")


def load(m):
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bl", "bc", "ao"]).sort_values("t").drop_duplicates("t"); d = d[(d.bo > 0) & (d.ao >= d.bo)].reset_index(drop=True)
    ny = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("America/New_York"); ok = ny.notna().values; d = d[ok].reset_index(drop=True); ny = ny[ok].reset_index(drop=True)
    sp = (d.ao - d.bo).values; real = (ny >= pd.Timestamp("2025-10-01", tz="America/New_York")).values; floor = float(np.median(sp[real])) if real.sum() > 1000 else float(np.median(sp)); sp = np.maximum(sp, floor)
    nl = ny.dt.tz_localize(None); nd = (nl.dt.normalize() - EPOCH).dt.days.values; nm = (nl.dt.hour * 60 + nl.dt.minute).values
    bo, bl, bc = d.bo.values, d.bl.values, d.bc.values; D = dict(bo=bo, bl=bl, bc=bc, bh=np.maximum(bo, bc), sp=sp, nd=nd, nm=nm, key=nd * 1440 + nm, ts=nl)
    b15 = D["key"] // 15; idx = pd.Series(np.arange(len(bo))); g = idx.groupby(b15); i0, i1 = g.min().values, g.max().values
    D["m15"] = dict(i0=i0, i1=i1, O=bo[i0], H=pd.Series(D["bh"]).groupby(b15).max().values, L=pd.Series(bl).groupby(b15).min().values, C=bc[i1], nd=nd[i0], nm=nm[i0]); return D


def scan(D, j0, side, entry, tp, sl, jx):
    bo, bl, bh, sp = D["bo"], D["bl"], D["bh"], D["sp"]; risk = abs(entry - sl)
    for j in range(j0, jx + 1):
        if j == jx and j > j0: px = (bo[j] - SLIPPTS) if side > 0 else (bo[j] + sp[j] + SLIPPTS); break
        if side > 0:
            if bl[j] <= sl: px = (bo[j] if bo[j] <= sl else sl) - SLIPPTS; break
            if bh[j] >= tp: px = bo[j] if bo[j] >= tp else tp; break
        else:
            if bh[j] + sp[j] >= sl: px = (bo[j] + sp[j] if bo[j] + sp[j] >= sl else sl) + SLIPPTS; break
            if bl[j] + sp[j] <= tp: px = bo[j] + sp[j] if bo[j] + sp[j] <= tp else tp; break
    else: px = (bo[jx] - SLIPPTS) if side > 0 else (bo[jx] + sp[jx] + SLIPPTS)
    return ((px - entry) if side > 0 else (entry - px)) / risk


def kidx(D, nd, minute): i = np.searchsorted(D["key"], nd * 1440 + minute, side="left"); return i if i < len(D["key"]) else len(D["key"]) - 1


def sweep(D, nd, lo_hi, kz, tp_mult, exit_min):
    hi, lo = lo_hi; M = D["m15"]; a = np.searchsorted(M["nd"], nd, side="left"); b = np.searchsorted(M["nd"], nd, side="right"); sp = D["sp"]
    for k in range(a, b):
        close_min = M["nm"][k] + 15
        if not (kz[0] <= close_min <= kz[1]): continue
        h, l, c = M["H"][k], M["L"][k], M["C"][k]; j = M["i1"][k] + 1
        if j >= len(sp): break
        if h > hi and c < hi: side, entry, stop = -1, D["bo"][j], h
        elif l < lo and c > lo: side, entry, stop = 1, D["bo"][j] + sp[j], l
        else: continue
        risk = abs(entry - stop)
        if risk < 4 * sp[j] or risk <= 0: return None
        tp = entry + tp_mult * risk if side > 0 else entry - tp_mult * risk; return scan(D, j, side, entry, tp, stop, kidx(D, nd, exit_min))
    return None


def fvg(D, nd, windows, valid_bars, exit_after, exit_abs, tp_mult=2.0):
    M = D["m15"]; a = np.searchsorted(M["nd"], nd, side="left"); b = np.searchsorted(M["nd"], nd, side="right"); out = {}; n = len(D["sp"])
    for k in range(a + 2, b):
        w = next((i for i, (lo_, hi_) in enumerate(windows) if lo_ <= M["nm"][k] + 15 <= hi_), None)
        if w is None or w in out: continue
        if M["i0"][k] - M["i1"][k - 2] > 40: continue
        if M["L"][k] > M["H"][k - 2]: side, mid, stop = 1, (M["L"][k] + M["H"][k - 2]) / 2, M["L"][k - 2]
        elif M["H"][k] < M["L"][k - 2]: side, mid, stop = -1, (M["H"][k] + M["L"][k - 2]) / 2, M["H"][k - 2]
        else: continue
        j_start = M["i1"][k] + 1; j_end = M["i1"][min(k + valid_bars, b - 1)]
        if exit_after == 0: j_end = min(j_end, kidx(D, nd, windows[w][1]))        # silver bullet: the order dies at the end of the window
        fill = None
        for j in range(j_start, min(j_end, n - 1) + 1):
            sp = D["sp"][j]
            if side > 0:
                if D["bl"][j] <= stop: break
                if D["bl"][j] + sp <= mid: fill = (j, min(mid, D["bo"][j] + sp)); break
            else:
                if D["bh"][j] + sp >= stop: break
                if D["bh"][j] >= mid: fill = (j, max(mid, D["bo"][j])); break
        if fill is None: continue
        j, entry = fill; risk = abs(entry - stop)
        if risk < 4 * D["sp"][j] or risk <= 0: continue
        tp = entry + tp_mult * risk if side > 0 else entry - tp_mult * risk
        jx = kidx(D, nd, exit_abs) if exit_after == 0 else min(j + exit_after, kidx(D, nd, exit_abs))
        out[w] = scan(D, j, side, entry, tp, stop, max(jx, j))
    return list(out.values())


def symbol_trades(m):
    D = load(m); nd = D["nd"]; days = np.unique(nd); res = {v: {} for v in ("SWEEP_ASIA", "SWEEP_PD", "FVG_KZ", "SB")}
    starts = np.searchsorted(D["key"], days * 1440); ends = np.r_[starts[1:], len(nd)]; dh = {d: (D["bh"][s:e].max(), D["bl"][s:e].min()) for d, s, e in zip(days, starts, ends)}; prev = None
    for d in days:
        ts = EPOCH + pd.Timedelta(days=int(d))
        if ts.dayofweek >= 5: continue
        a0, a1 = np.searchsorted(D["key"], (d - 1) * 1440 + 1200, side="left"), np.searchsorted(D["key"], d * 1440, side="left")
        if a1 - a0 >= 150:
            r = sweep(D, d, (D["bh"][a0:a1].max(), D["bl"][a0:a1].min()), (120, 300), 2.0, 600)
            if r is not None: res["SWEEP_ASIA"][ts] = r
        if prev is not None and (d - prev) <= 4:
            r = sweep(D, d, dh[prev], (525, 660), 2.0, 780)
            if r is not None: res["SWEEP_PD"][ts] = r
        for r in fvg(D, d, [(120, 300), (510, 660)], 8, 180, 960): res["FVG_KZ"][ts + pd.Timedelta(seconds=len(res["FVG_KZ"]))] = r
        for r in fvg(D, d, [(600, 660)], 4, 0, 720): res["SB"][ts + pd.Timedelta(seconds=len(res["SB"]))] = r
        prev = d
    return {k: pd.Series(v, dtype=float).sort_index() for k, v in res.items()}


def st(s, w):
    d = s[(s.index >= w[0]) & (s.index <= pd.Timestamp(w[1]) + pd.Timedelta(days=1))]; n = len(d)
    if n < 3 or d.std(ddof=1) == 0: return dict(n=n, mean=d.mean() if n else np.nan, t=np.nan, p=1.0)
    t = d.mean() / (d.std(ddof=1) / np.sqrt(n)); from scipy import stats; return dict(n=n, mean=d.mean(), t=t, p=stats.t.sf(t, n - 1))


def cls(s):
    if s in ("SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX"): return "indices"
    if s in ("XAUUSD", "XAGUSD"): return "metals"
    if s in ("WTI", "BRENT"): return "energy"
    if s[:3] in ("BTC", "ETH", "LTC", "SOL", "XRP", "ADA", "BNB", "BCH"): return "crypto"
    return "fx"


if __name__ == "__main__":
    mode = os.environ.get("ICT"); rows = []
    for m in ALL:
        try: T = symbol_trades(m)
        except Exception as ex: print("skip", m, repr(ex)); continue
        for v, s in T.items():
            d, va, ho = st(s, SC.DEV), st(s, SC.VAL), st(s, SC.HOLD); rows.append(dict(symbol=m, cls=cls(m), variant=v, dev_n=d["n"], dev_R=d["mean"], dev_t=d["t"], dev_p=d["p"], val_n=va["n"], val_R=va["mean"], hold_n=ho["n"], hold_R=ho["mean"], hold_t=ho["t"]))
        print(m, "done", flush=True)
    R = pd.DataFrame(rows); R["dev_p"] = R.dev_p.fillna(1.0)
    if mode == "dry": print("tests", len(R), R.groupby("variant").dev_n.sum().to_dict())
    if mode == "run":
        el = R[R.dev_n >= 80].copy(); el["bh"] = SC.bh(el.dev_p.values, 0.10); R = R.merge(el[["symbol", "variant", "bh"]], on=["symbol", "variant"], how="left"); R["bh"] = R.bh.fillna(False).astype(bool); R["survivor"] = R.bh & (R.dev_R >= 0.10) & (R.val_n >= 25) & (R.val_R > 0)
        L = [f"tests {len(R)} ({len(el)} with >= 80 DEV trades) | nominally positive in DEV {int((R.dev_R > 0).sum())}, p < 0.05: {int((R.dev_p < 0.05).sum())} (luck about {0.05 * len(el):.0f}) | BH q 0.10 passed DEV: {int(R.bh.sum())} | survivors: {int(R.survivor.sum())}"]
        L.append("\ntop 10 by DEV t:\n" + R.sort_values("dev_t", ascending=False).head(10)[["symbol", "variant", "dev_n", "dev_R", "dev_t", "val_n", "val_R", "hold_n", "hold_R"]].round(3).to_string(index=False))
        def pool(g, w): n = g[f"{w}_n"].fillna(0); return (n * g[f"{w}_R"].fillna(0)).sum() / n.sum() if n.sum() else np.nan
        P = pd.DataFrame([dict(variant=v, cls=c, dev_n=int(g.dev_n.sum()), dev_R=pool(g, "dev"), val_R=pool(g, "val"), hold_R=pool(g, "hold")) for (v, c), g in R.groupby(["variant", "cls"])]); L.append("\npooled mean R by variant and class (DEV / VAL / HOLD):\n" + P.round(3).to_string(index=False))
        sv = R[R.survivor]; L.append("\nSURVIVORS:\n" + sv.round(3).to_string(index=False) if len(sv) else "\nno survivors")
        txt = "\n".join(L); print(txt); R.to_csv(os.path.join(os.path.dirname(__file__), "ICT_SCAN_TESTS.csv"), index=False); open(os.path.join(os.path.dirname(__file__), "ICT_SCAN_RESULT.txt"), "w").write(txt)
