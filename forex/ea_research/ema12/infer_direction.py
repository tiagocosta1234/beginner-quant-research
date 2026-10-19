"""Which simple context rule agrees with the trader's trade direction on the 30 dated gold trades? Descriptive only (no P&L); 30 points, so no tuning claims."""
import numpy as np, pandas as pd
from ema12_test import load
O = pd.read_csv("replay_mt5.csv"); g = load("XAUUSD", last_day="2025-12-31")
idx = {(d, h): i for i, (d, h) in enumerate(zip(g.day, g.hm))}
sgn = lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
g["ema5m"] = g.mid.rolling(5).mean().ewm(span=12, adjust=False).mean()          # slow EMA proxy
g["ema60"] = g.mid.ewm(span=720, adjust=False).mean(); g["ema240"] = g.mid.ewm(span=240, adjust=False).mean()
rules = {k: [] for k in ("price>EMA12 1m (prev close)", "move since session open", "move over previous 30 min", "move over previous 2 h", "move since previous day 22:00 close", "price>EMA(240m)", "price>EMA(720m)", "first 5 min of session direction", "against the last 60 min move (fade)")}
truth = []
for _, r in O.iterrows():
    import datetime as dt
    day = pd.Timestamp(r.day).date(); i = idx[(day, int(r.hm))]; om = 600 if r.ses == "London" else 990
    i_open = idx.get((day, om)) or idx.get((day, om + 1)) or i - 3
    side = 1 if r.side == "L" else -1; truth.append(side)
    rules["price>EMA12 1m (prev close)"].append(sgn(g.mid[i-1] - g.ema[i-1]))
    rules["move since session open"].append(sgn(g.mid[i-1] - g.mo_[i_open]) if False else sgn(g.mid[i-1] - g.mid[max(i_open-1, 0)]))
    rules["move over previous 30 min"].append(sgn(g.mid[i-1] - g.mid[i-31]))
    rules["move over previous 2 h"].append(sgn(g.mid[i-1] - g.mid[i-121]))
    rules["move since previous day 22:00 close"].append(sgn(g.mid[i-1] - g.mid[i-(int(r.hm) - 0) - 120 if i-int(r.hm)-120 > 0 else 0]))
    rules["price>EMA(240m)"].append(sgn(g.mid[i-1] - g.ema240[i-1])); rules["price>EMA(720m)"].append(sgn(g.mid[i-1] - g.ema60[i-1]))
    rules["first 5 min of session direction"].append(sgn(g.mid[min(i_open+4, i-1)] - g.mid[max(i_open-1, 0)]))
    rules["against the last 60 min move (fade)"].append(-sgn(g.mid[i-1] - g.mid[i-61]))
truth = np.array(truth)
print("agreement with the trader's direction (out of 30; 15 = coin flip):")
for k, v in rules.items():
    v = np.array(v); ok = int((v == truth).sum()); print("  %-40s %2d/30  (long share of rule %.0f%%)" % (k, ok, 100 * (v > 0).mean()))
print("the trader's long share: %.0f%%" % (100 * (truth > 0).mean()))
