"""Gold hit-rate battery on other markets (PREREG_MULTI.md). python -m forex.self_improving.hitrate.hitrate_multi"""
import numpy as np, pandas as pd
from forex.self_improving.hitrate import hitrate_lab as H

import os
FX = ["AUDCAD","AUDCHF","AUDJPY","AUDNZD","AUDUSD","CADCHF","CADJPY","CHFJPY","EURAUD","EURCAD","EURCHF","EURGBP","EURJPY","EURNZD","EURUSD","GBPAUD","GBPCAD","GBPCHF","GBPJPY","GBPNZD","GBPUSD","NZDCAD","NZDCHF","NZDJPY","NZDUSD","USDCAD","USDCHF","USDJPY"]
MARKETS = FX if os.environ.get("SET") == "FX" else ["SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX", "WTI", "BRENT", "XAGUSD", "BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "LTCUSD", "BCHUSD", "XRPUSD", "ADAUSD"]
DIR = "D:/finance/beginner-quant-research/forex/data_mt5/"


def cells(tr):
    out = {}
    for rule in H.RULES:
        r = {}
        for nm, (a, b) in H.WINDOWS.items():
            x = tr[(tr.rule == rule) & (tr.date >= a) & (tr.date <= b)]; n = len(x); dec = x[x.res != 0]
            m = x.R.mean() if n else np.nan; z = m / (x.R.std() / np.sqrt(n)) if n > 5 and x.R.std() > 0 else np.nan
            r[nm] = (n, m, z, 100 * (dec.res == 1).mean() if len(dec) else np.nan)
        out[rule] = r
    return out


def main():
    rng = np.random.default_rng(20261014); rows = []; plac = {1: [], 2: []}
    for mk in MARKETS:
        H.F = DIR + f"{mk}_M1_rates.parquet"
        try:
            d = H.load(); t, day, hour, u, st, en = H.days(d); sig = H.signals(d, t, hour, u, st, en)
        except Exception as e:
            print(mk, "failed", repr(e)[:100], flush=True); continue
        print(mk, "signals", len(sig), flush=True)
        for w in (0.20, 0.35):
            tr = H.simulate(d, sig, w); tr["date"] = pd.to_datetime(tr.day * 86400, unit="s")
            for rule, c in cells(tr).items():
                rows.append(dict(market=mk, rule=rule, w=w, **{f"{k}_{s}": v for k, vals in c.items() for s, v in zip(("n", "R", "z", "hit"), vals)}))
            for wd in (1, 2):                                   # placebo worlds: random side per signal, same barriers and costs
                sg = [(r_, dy, i, int(rng.choice([-1, 1])), adr, ie) for r_, dy, i, sd, adr, ie in sig]
                tp = H.simulate(d, sg, w); tp["date"] = pd.to_datetime(tp.day * 86400, unit="s")
                zs = [c["VAL"][2] for c in cells(tp).values() if c["VAL"][0] >= 150 and not np.isnan(c["VAL"][2])]
                plac[wd] += zs
    o = pd.DataFrame(rows); o.to_csv("D:/finance/si_ledgers/HITRATE_" + ("fx" if os.environ.get("SET") == "FX" else "multi") + "_real.csv", index=False)
    pm = [max(v) for v in plac.values() if v]; p95 = float(np.percentile(np.concatenate([plac[1], plac[2]]), 99.5)) if plac[1] else np.nan
    o["pass"] = (o.A_R > 0) & (o.B_R > 0) & (o.VAL_R >= 0.15) & (o.VAL_n >= 150) & (o.VAL_z >= (3.78 if os.environ.get('SET') == 'FX' else 3.65)) & (o.VAL_z >= max(pm))
    print("placebo max VAL t per world:", [round(x, 2) for x in pm], "| cells", len(o), "| passing", int(o["pass"].sum()))
    cols = ["market", "rule", "w", "A_n", "A_R", "B_R", "VAL_n", "VAL_R", "VAL_z", "VAL_hit"]
    big = o[o.VAL_n >= 150].sort_values("VAL_z", ascending=False).head(10); print("top 10 by VAL t:"); print(big[cols].round(3).to_string(index=False))
    print("best decided-hit rates (n>=150):"); print(o[o.VAL_n >= 150].sort_values("VAL_hit", ascending=False).head(8)[cols].round(3).to_string(index=False))
    print("cells with A_R>0, B_R>0, VAL_R>0:", int(((o.A_R > 0) & (o.B_R > 0) & (o.VAL_R > 0) & (o.VAL_n >= 150)).sum()), "of", int((o.VAL_n >= 150).sum()))


if __name__ == "__main__":
    main()
