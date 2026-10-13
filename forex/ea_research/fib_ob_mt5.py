"""FO: the trader's Fibonacci 79% + order-block idea on MT5 NSDQ, causal (PREREG_FIB_OB.md).   env FO=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data_mt5"
DEV, VAL, HOLD = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-09-30")
EMBARGO = {945, 1000, 1345, 1400}; EOD = {1545, 145}


def bars(m, sec, minmin):
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bl", "bc", "ao"]).sort_values("t").drop_duplicates("t"); d = d[(d.bo > 0) & (d.ao >= d.bo)]
    d["hi"] = np.maximum(d.bo, d.bc); d["b"] = d.t // sec
    g = d.groupby("b").agg(t0=("t", "first"), o=("bo", "first"), h=("hi", "max"), l=("bl", "min"), c=("bc", "last"), oa=("ao", "first"), n=("t", "size")); g = g[g.n >= minmin].reset_index(drop=True)
    ny = pd.to_datetime(g.t0, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("America/New_York")
    g["hm"] = ny.dt.hour * 100 + ny.dt.minute; g["t0"] = g.t0.astype(np.int64); return g[ny.notna()].reset_index(drop=True)


def prepare(m):
    q, h1 = bars(m, 900, 5), bars(m, 3600, 20); H = h1.h.values; sw_t, sw_v = [], []
    for k in range(2, len(h1) - 2):
        if H[k] > H[k - 1] and H[k] > H[k - 2] and H[k] > H[k + 1] and H[k] > H[k + 2]: sw_t.append(h1.t0.iat[k + 2] + 3600); sw_v.append(H[k])     # known when bar k+2 has closed
    o, c, l, h, t0 = q.o.values, q.c.values, q.l.values, q.h.values, q.t0.values; ob_t, ob_top, ob_bot = [], [], []
    for k in range(len(q) - 1):
        if c[k] < o[k] and c[k + 1] > o[k]: ob_t.append(t0[k + 1] + 900); ob_top.append(h[k]); ob_bot.append(l[k])                                    # known when bar k+1 has closed
    rh = pd.Series(h).rolling(20).max().shift(1).values; rl = pd.Series(l).rolling(20).min().shift(1).values
    return q, np.array(sw_t), np.array(sw_v), np.array(ob_t), np.array(ob_top), np.array(ob_bot), rh, rl


def latest(kt, vals, T):
    i = np.searchsorted(kt, T, side="right") - 1; return vals[i] if i >= 0 else np.nan


def run(m, variant):
    q, sw_t, sw_v, ob_t, ob_top, ob_bot, rh, rl = prepare(m); o, c, l, h, oa, t0, hm = q.o.values, q.c.values, q.l.values, q.h.values, q.oa.values, q.t0.values, q.hm.values; n = len(q); out = []; i = 21; pos = None
    def exit_check(j, st):
        stop, target = st
        if hm[j] in EOD: return c[j], "eod"
        if o[j] <= stop: return o[j], "stop"
        if l[j] <= stop: return stop, "stop"
        if o[j] >= target: return o[j], "target"
        if h[j] >= target: return target, "target"
        return None
    while i < n - 1:
        if pos is not None:
            r = exit_check(i, (pos["stop"], pos["target"]))
            if r: out.append(dict(entry=pd.Timestamp(pos["t"], unit="s"), exit=pd.Timestamp(t0[i], unit="s"), R=(r[0] - pos["entry"]) / (pos["entry"] - pos["stop"]), bp=1e4 * (r[0] / pos["entry"] - 1), rr=(pos["target"] - pos["entry"]) / (pos["entry"] - pos["stop"]), how=r[1])); pos = None
            i += 1; continue
        T = t0[i]
        if np.isnan(rh[i]) or np.isnan(rl[i]): i += 1; continue
        sess = (930 <= hm[i] <= 1600) or hm[i] >= 1900 or hm[i] <= 200
        if sess and hm[i] not in EMBARGO:
            fib = rh[i] - (rh[i] - rl[i]) * 0.79; top, bot = latest(ob_t, ob_top, T), latest(ob_t, ob_bot, T); tgt = latest(sw_t, sw_v, T); stop = rl[i]
            if not np.isnan(top) and not np.isnan(tgt) and bot <= fib <= top and stop < fib < tgt:
                if variant == "FO1" and l[i] + (oa[i] - o[i]) <= fib:
                    fill = min(fib, oa[i])
                    if fill > stop and tgt > fill:
                        if l[i] <= stop: out.append(dict(entry=pd.Timestamp(T, unit="s"), exit=pd.Timestamp(T, unit="s"), R=(stop - fill) / (fill - stop), bp=1e4 * (stop / fill - 1), rr=(tgt - fill) / (fill - stop), how="stop_same_bar"))
                        else: pos = dict(entry=fill, stop=stop, target=tgt, t=T)
                elif variant == "FO2" and l[i] <= fib < c[i] and i + 1 < n:
                    tg2 = latest(sw_t, sw_v, t0[i + 1]); ent = oa[i + 1]
                    if stop < ent < tg2: pos = dict(entry=ent, stop=stop, target=tg2, t=t0[i + 1]); i += 1; continue
        i += 1
    return pd.DataFrame(out)


def win(df, w): return df[(df.entry >= w[0]) & (df.entry <= pd.Timestamp(w[1]) + pd.Timedelta(days=1))]


def summ(df, w, years):
    d = win(df, w)
    if d.empty: return dict(n=0, win=np.nan, rr=np.nan, meanR=np.nan, totR=0.0, pf=np.nan, t=np.nan, usd=0.0, per_year=0.0)
    g = d.groupby(d.entry.dt.normalize()).R.mean(); wn, ls = d.R[d.R > 0].sum(), -d.R[d.R < 0].sum()
    return dict(n=len(d), win=100 * (d.R > 0).mean(), rr=d.rr.mean(), meanR=d.R.mean(), totR=d.R.sum(), pf=wn / ls if ls else np.inf, t=g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan, usd=500 * d.R.sum(), per_year=len(d) / years)


def f(s): return f"trades {s['n']:4d} ({s['per_year']:4.0f}/yr) | win {s['win']:4.0f}% | planned RR {s['rr']:.2f} | mean R {s['meanR']:+.3f} | PF(R) {s['pf']:.2f} | total {s['totR']:+7.1f} R = {s['usd']:+9,.0f} USD at 500/trade | t {s['t']:.2f}" if s["n"] else "no trades"


if __name__ == "__main__":
    mode = os.environ.get("FO"); T = {(v, m): run(m, v) for v in ("FO1", "FO2") for m in ("NSDQ", "SP", "DOW")}
    if mode == "dry":
        for (v, m), df in T.items(): print(v, m, "trades", len(df), "DEV", len(win(df, DEV)), "VAL", len(win(df, VAL)), "HOLD", len(win(df, HOLD)))
    if mode == "run":
        lines = []
        for v in ("FO1", "FO2"):
            df = T[(v, "NSDQ")]; d, va = summ(df, DEV, 3.0), summ(df, VAL, 1.0); acc = bool(d["n"] >= 40 and d["meanR"] >= 0.15 and d["pf"] >= 1.3 and d["t"] >= 1.65 and va["meanR"] > 0)
            lines.append(f"{v} NSDQ ({'limit order at the fib' if v == 'FO1' else 'confirmed close, next open'})\n  DEV  2022-24: {f(d)}\n  VAL  2025   : {f(va)}\n  accepted: {acc}")
            if acc: h = summ(df, HOLD, 0.75); lines.append(f"  HOLD 2026   : {f(h)} | pass: {bool(h['meanR'] > 0)}")
            lines.append("  exits (all years): " + str(df.how.value_counts().to_dict()) + " | by year (trades, mean R): " + str({int(y): (len(x), round(x.R.mean(), 3)) for y, x in df.groupby(df.entry.dt.year)}))
            for m in ("SP", "DOW"): lines.append(f"  descriptive {m}: DEV {f(summ(T[(v, m)], DEV, 3.0))}")
            lines.append("")
        txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "FIB_OB_RESULT.txt"), "w").write(txt)
