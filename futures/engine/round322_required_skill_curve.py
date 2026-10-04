"""
Round 322 (2026-10-03, DESCRIPTIVE, no ledger row, k stays 2025): how much directional skill does the deployed 1-Step table need to pass more often?
Same NQ / ES session proxy and table as Round 321 (reuses its functions). Stylized skill model: each day the direction equals the day's realised side (long if the 09:30-15:59 return is up, short if down) with
probability p and the opposite with probability 1 - p; p = 0.50 is the coin flip. Reported: P(pass within 57 trading days) for p in 0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.65 (20 random draws per start day).
Purpose: size the target for the search (what hit rate on a daily direction call is worth how many points of pass probability); not a strategy and not a test of any signal.
Pre-stated: p = 0.50 reproduces Round 321's COIN (41.0% NQ / 37.5% ES within 1-2 points).
"""
import os, sys, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import round321_long_bias_bold_play as R
from mt5broker import onestep as OS

pol = OS.Policy()
out = {}
for sym in ("NQ", "ES"):
    df = R.day_table(sym)
    b = R.load(sym)
    oc = b.groupby(b.index.normalize()).apply(lambda x: x.c.iloc[-1] - x.o.iloc[0])
    up = (oc.reindex(df.index) > 0).values
    recs = df.reset_index().to_dict("records")
    for i, r in enumerate(recs):
        r["up"] = bool(up[i])
    rng = np.random.default_rng(322)
    for p in (0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.65):
        fn = lambda r, g, p=p: (1 if r["up"] else -1) if g.random() < p else (-1 if r["up"] else 1)
        starts = range(0, len(recs) - 57)
        res = [np.mean([R.run_window(recs, s, 57, fn, pol, rng)[0] == "pass" for _ in range(20)]) for s in starts]
        out[f"{sym}|{p}"] = float(np.mean(res))
    print(sym, {k.split("|")[1]: round(v * 100, 1) for k, v in out.items() if k.startswith(sym)}, flush=True)
json.dump(out, open(R.result_path(HERE, "round322_results.json"), "w"), indent=1)
