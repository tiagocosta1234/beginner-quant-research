"""FM: the Fibonacci 79% + order-block idea inverted (short), 2026 (PREREG_FIB_OB_MIRROR.md).   env FM=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from forex.ea_research import fib_ob_mt5 as F

EMB, EOD, HOLD, ALLB = F.EMBARGO, F.EOD, F.HOLD, ("2022-01-01", "2025-12-31")


def run(m, variant):
    q, sw_t, sw_v, ob_t, ob_top, ob_bot, rh, rl = F.prepare(m); o, c, l, h, oa, t0, hm = q.o.values, q.c.values, q.l.values, q.h.values, q.oa.values, q.t0.values, q.hm.values; sp = oa - o; n = len(q); out = []; i = 21; pos = None
    def record(j, px, how):
        out.append(dict(entry=pd.Timestamp(pos["t"], unit="s"), exit=pd.Timestamp(t0[j], unit="s"), bp=1e4 * (pos["entry"] - px) / pos["entry"], R=(pos["entry"] - px) / (pos["stop"] - pos["entry"]), rr=(pos["entry"] - pos["target"]) / (pos["stop"] - pos["entry"]), how=how))
    while i < n - 1:
        if pos is not None:
            ask_o, ask_h, ask_l, ask_c = o[i] + sp[i], h[i] + sp[i], l[i] + sp[i], c[i] + sp[i]
            if hm[i] in EOD: record(i, ask_c, "eod"); pos = None
            elif ask_o >= pos["stop"]: record(i, ask_o, "stop"); pos = None
            elif ask_h >= pos["stop"]: record(i, pos["stop"], "stop"); pos = None
            elif ask_o <= pos["target"]: record(i, ask_o, "target"); pos = None
            elif ask_l <= pos["target"]: record(i, pos["target"], "target"); pos = None
            i += 1; continue
        T = t0[i]
        if np.isnan(rh[i]) or np.isnan(rl[i]): i += 1; continue
        sess = (930 <= hm[i] <= 1600) or hm[i] >= 1900 or hm[i] <= 200
        if sess and hm[i] not in EMB:
            fib = rh[i] - (rh[i] - rl[i]) * 0.79; top, bot = F.latest(ob_t, ob_top, T), F.latest(ob_t, ob_bot, T); tgt = F.latest(sw_t, sw_v, T); lowrange = rl[i]
            if not np.isnan(top) and not np.isnan(tgt) and bot <= fib <= top and lowrange < fib < tgt:
                if variant == "FM1" and l[i] <= fib:
                    fill = min(fib, o[i]); stop, target = tgt, lowrange
                    if stop > fill > target:
                        pos = dict(entry=fill, stop=stop, target=target, t=T)
                        if h[i] + sp[i] >= stop: record(i, stop, "stop_same_bar"); pos = None
                elif variant == "FM2" and l[i] <= fib < c[i] and i + 1 < n:
                    tg2 = F.latest(sw_t, sw_v, t0[i + 1]); ent = o[i + 1]; stop, target = tg2, lowrange
                    if stop > ent > target: pos = dict(entry=ent, stop=stop, target=target, t=t0[i + 1]); i += 1; continue
        i += 1
    return pd.DataFrame(out)


def win(df, w): return df[(df.entry >= w[0]) & (df.entry <= pd.Timestamp(w[1]) + pd.Timedelta(days=1))]


def summ(df, w, years):
    d = win(df, w)
    if d.empty: return dict(n=0)
    g = d.groupby(d.entry.dt.normalize()).bp.mean(); wn, ls = d.bp[d.bp > 0].sum(), -d.bp[d.bp < 0].sum()
    return dict(n=len(d), win=100 * (d.bp > 0).mean(), mean_bp=d.bp.mean(), tot_bp=d.bp.sum(), meanR=d.R.mean(), rr=d.rr.mean(), pf=wn / ls if ls else np.inf, t=g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan, usd=500 * d.R.sum(), per_year=len(d) / years)


def f(s): return f"trades {s['n']:4d} ({s['per_year']:4.0f}/yr) | win {s['win']:3.0f}% | planned RR {s['rr']:.2f} | mean {s['mean_bp']:+6.1f} bp | mean R {s['meanR']:+.3f} | PF {s['pf']:.2f} | total {s['tot_bp']:+8.0f} bp | t {s['t']:.2f}" if s["n"] else "no trades"


if __name__ == "__main__":
    mode = os.environ.get("FM"); T = {(v, m): run(m, v) for v in ("FM1", "FM2") for m in ("NSDQ", "SP", "DOW")}
    if mode == "dry":
        for (v, m), df in T.items(): print(v, m, "trades", len(df), "2022-25", len(win(df, ALLB)), "HOLD", len(win(df, HOLD)))
    if mode == "run":
        lines = []
        for v in ("FM1", "FM2"):
            df = T[(v, "NSDQ")]; a, h_ = summ(df, ALLB, 4.0), summ(df, HOLD, 0.75); acc = bool(h_["n"] >= 40 and h_["mean_bp"] >= 10 and h_["pf"] >= 1.3 and h_["t"] >= 1.65 and a["n"] and a["mean_bp"] > 0)
            lines.append(f"{v} NSDQ inverted ({'sell-stop at the fib' if v == 'FM1' else 'confirmed close, sell next open'})\n  2022-25 (consistency only): {f(a)}\n  HOLD 2026-01..09          : {f(h_)}\n  accepted: {acc}")
            lines.append("  exits: " + str(df.how.value_counts().to_dict()) + " | by year (trades, mean bp): " + str({int(y): (len(x), round(x.bp.mean(), 1)) for y, x in df.groupby(df.entry.dt.year)}))
            for m in ("SP", "DOW"): lines.append(f"  descriptive {m}: 2022-25 {f(summ(T[(v, m)], ALLB, 4.0))} | 2026 {f(summ(T[(v, m)], HOLD, 0.75))}")
            lines.append("")
        txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "FIB_OB_MIRROR_RESULT.txt"), "w").write(txt)
