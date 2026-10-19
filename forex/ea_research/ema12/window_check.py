"""Descriptive: the mechanical rules over the trader's 4-week window (2025-04-14..05-12) vs his 30 trades. Exploratory, not part of the registered acceptance."""
import numpy as np, pandas as pd
from ema12_test import load, signals, simulate, stats
g = load("XAUUSD", last_day="2025-12-31"); a, b = pd.Timestamp("2025-04-14"), pd.Timestamp("2025-05-12")
O = pd.read_csv("replay_mt5.csv"); days = {(pd.Timestamp(r.day), "London" if r.ses == "London" else "NY") for _, r in O.iterrows()}
print("the trader's 30 trades on MT5 broker prices: mean R +0.219, wins 24/30")
for f in ("F0", "F30"):
    for st in ("ATR25", "SW15"):
        for sess in ("London", "NY"):
            x = simulate(g, signals(g, sess, st, filt=f), 0.525); w = x[(x.day >= a) & (x.day <= b)]; s = stats(w)
            print("%s %-5s %-6s window 2025-04-14..05-12: n %3d meanR %+.3f win %.0f%% | whole 2025: n %3d meanR %+.3f" % (f, st, sess, s["n"], s["meanR"], s["win"], len(x[x.day.dt.year == 2025]), x[x.day.dt.year == 2025].R.mean()))
# pooled both sessions, window vs rest of 2025
for f in ("F0", "F30"):
    xs = pd.concat([simulate(g, signals(g, s_, "ATR25", filt=f), 0.525) for s_ in ("London", "NY")]); xs = xs[xs.day.dt.year == 2025]
    w = xs[(xs.day >= a) & (xs.day <= b)]; r = xs[~((xs.day >= a) & (xs.day <= b))]
    print("%s pooled London+NY ATR25 r0.525: window n %d meanR %+.3f win %.0f%% | rest of 2025 n %d meanR %+.3f win %.0f%%" % (f, len(w), w.R.mean(), 100*(w.R > 0).mean(), len(r), r.R.mean(), 100*(r.R > 0).mean()))
