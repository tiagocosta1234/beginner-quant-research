"""SC: systematic setup scan over every MT5 broker symbol (PREREG_SETUP_SCAN.md).   env SC=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from scipy import stats
from pathlib import Path
from forex.ea_research import more_eas as ME, fincept_mt5_verify as V

DATA = Path(__file__).resolve().parents[1] / "data_mt5"
ALL = sorted(p.name.split("_M1_rates")[0] for p in DATA.glob("*_M1_rates.parquet")); DEV, VAL, HOLD = ME.DEV, ME.VAL, ME.HOLD


def daily(m):
    d = ME.load(m); b, a = ME.at(d, "hm", 1559, "bo", "date"), ME.at(d, "hm", 1559, "ao", "date"); i = b.index.intersection(a.index).sort_values(); return b[i], a[i]


def ret(side, bi, ai, bj, aj): return (bj / ai - 1) if side > 0 else (bi / aj - 1)


def walk(b, a, side, i, exit_fn, maxd):
    j = i + 1
    while j < len(b) - 1 and not exit_fn(j) and j - i < maxd: j += 1
    return j


def variant_trades(m, b, a):
    out = {}; n = len(b); c = b; r2 = V.rsi(c); s200, s5, s20 = c.rolling(200).mean(), c.rolling(5).mean(), c.rolling(20).mean(); sd20 = c.rolling(20).std(); hi20, lo20 = c.shift(1).rolling(20).max(), c.shift(1).rolling(20).min()
    lo10, hi10 = c.shift(1).rolling(10).min(), c.shift(1).rolling(10).max(); r20 = c / c.shift(20) - 1
    def add(name, side, i, j): out.setdefault((name, side), []).append((b.index[i], ret(side, b.iat[i], a.iat[i], b.iat[j], a.iat[j])))
    for name, filt in (("RSI2F", True), ("RSI2", False)):
        for side in (1, -1):
            i = 200 if filt else 20
            while i < n - 1:
                sig = (r2.iat[i] < 10 and (c.iat[i] > s200.iat[i] or not filt)) if side > 0 else (r2.iat[i] > 90 and (c.iat[i] < s200.iat[i] or not filt))
                if sig:
                    ex = (lambda j: c.iat[j] > s5.iat[j] or r2.iat[j] > 70) if side > 0 else (lambda j: c.iat[j] < s5.iat[j] or r2.iat[j] < 30); j = walk(b, a, side, i, ex, 5); add(name, side, i, j); i = j + 1
                else: i += 1
    for side in (1, -1):
        i = 21
        while i < n - 1:
            sig = c.iat[i] > hi20.iat[i] if side > 0 else c.iat[i] < lo20.iat[i]
            if sig:
                ex = (lambda j: c.iat[j] < lo10.iat[j]) if side > 0 else (lambda j: c.iat[j] > hi10.iat[j]); j = walk(b, a, side, i, ex, 60); add("DON", side, i, j); i = j + 1
            else: i += 1
        i = 4
        while i < n - 1:
            sig = (c.iat[i] < c.iat[i - 1] < c.iat[i - 2] < c.iat[i - 3]) if side > 0 else (c.iat[i] > c.iat[i - 1] > c.iat[i - 2] > c.iat[i - 3])
            if sig: j = min(i + 3, n - 1); add("STK", side, i, j); i = j + 1
            else: i += 1
        i = 21
        while i < n - 1:
            sig = c.iat[i] < s20.iat[i] - 2 * sd20.iat[i] if side > 0 else c.iat[i] > s20.iat[i] + 2 * sd20.iat[i]
            if sig:
                ex = (lambda j: c.iat[j] > s20.iat[j]) if side > 0 else (lambda j: c.iat[j] < s20.iat[j]); j = walk(b, a, side, i, ex, 10); add("BB", side, i, j); i = j + 1
            else: i += 1
        i = 21
        while i < n - 6:
            if b.index[i].dayofweek == 4 and np.isfinite(r20.iat[i]) and np.sign(r20.iat[i]) == side: j = i + 5; add("MOM", side, i, j); i = j + 1
            else: i += 1
    return {k: pd.Series(dict(v)) if len(set(x[0] for x in v)) == len(v) else pd.Series([x[1] for x in v], index=[x[0] for x in v]) for k, v in out.items()}


def st(s, w):
    d = s[(s.index >= w[0]) & (s.index <= pd.Timestamp(w[1]) + pd.Timedelta(days=1))] * 1e4; n = len(d)
    return dict(n=n, mean=d.mean() if n else np.nan, t=d.mean() / (d.std(ddof=1) / np.sqrt(n)) if n > 2 and d.std(ddof=1) > 0 else np.nan, p=stats.t.sf(d.mean() / (d.std(ddof=1) / np.sqrt(n)), n - 1) if n > 2 and d.std(ddof=1) > 0 else 1.0)


def bh(p, q):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p); thr = q * (np.arange(1, n + 1) / n); ok = p[o] <= thr; k = np.nonzero(ok)[0].max() + 1 if ok.any() else 0; keep = np.zeros(n, bool); keep[o[:k]] = True; return keep


if __name__ == "__main__":
    mode = os.environ.get("SC"); rows = []
    for m in ALL:
        try: b, a = daily(m)
        except Exception as ex: print("skip", m, ex); continue
        if len(b) < 300: continue
        for (name, side), s in variant_trades(m, b, a).items():
            d, v, h = st(s, DEV), st(s, VAL), st(s, HOLD); rows.append(dict(symbol=m, variant=name, side="long" if side > 0 else "short", dev_n=d["n"], dev_mean=d["mean"], dev_t=d["t"], dev_p=d["p"], val_n=v["n"], val_mean=v["mean"], val_t=v["t"], hold_n=h["n"], hold_mean=h["mean"], hold_t=h["t"]))
    R = pd.DataFrame(rows); R["dev_p"] = R.dev_p.fillna(1.0)
    if mode == "dry": print("tests", len(R), "symbols", R.symbol.nunique(), "variants", R.variant.nunique()); print(R.groupby("variant").dev_n.sum().to_dict())
    if mode == "run":
        elig = R[(R.dev_n >= 30)].copy(); elig["bh"] = bh(elig.dev_p.values, 0.10); R = R.merge(elig[["symbol", "variant", "side", "bh"]], on=["symbol", "variant", "side"], how="left"); R["bh"] = R.bh.fillna(False).astype(bool)
        R["survivor"] = R.bh & (R.dev_mean >= 15) & (R.val_n >= 8) & (R.val_mean > 0); lines = [f"tests {len(R)} ({len(elig)} with >= 30 DEV trades) | nominally positive in DEV (mean > 0): {int((R.dev_mean > 0).sum())}, with one-sided p < 0.05: {int((R.dev_p < 0.05).sum())} (luck alone: about {0.05 * len(elig):.0f}) | positive in VAL: {int((R.val_mean > 0).sum())} of {int(R.val_n.gt(0).sum())}"]
        lines.append(f"Benjamini-Hochberg q = 0.10 passed DEV: {int(R.bh.sum())} | survivors (also DEV mean >= +15 bp and VAL > 0 with >= 8 trades): {int(R.survivor.sum())}")
        top = R.sort_values("dev_t", ascending=False).head(12); lines.append("\ntop 12 by DEV t:\n" + top[["symbol", "variant", "side", "dev_n", "dev_mean", "dev_t", "val_n", "val_mean", "hold_n", "hold_mean"]].round(1).to_string(index=False))
        sv = R[R.survivor]
        if len(sv): lines.append("\nSURVIVORS (HOLD-OUT now looked at once):\n" + sv[["symbol", "variant", "side", "dev_n", "dev_mean", "dev_t", "val_n", "val_mean", "hold_n", "hold_mean", "hold_t"]].round(1).to_string(index=False))
        else: lines.append("\nno survivors")
        txt = "\n".join(lines); print(txt); R.to_csv(os.path.join(os.path.dirname(__file__), "SETUP_SCAN_TESTS.csv"), index=False); open(os.path.join(os.path.dirname(__file__), "SETUP_SCAN_RESULT.txt"), "w").write(txt)
