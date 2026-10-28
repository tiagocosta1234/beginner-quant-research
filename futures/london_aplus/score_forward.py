"""Scores FORWARD_LOG.csv against PREREG_FORWARD_LONDON_APLUS.md (bar: n >= 50, mean net R > +0.05, win rate >= 53%, no market > 40%). Usage: python score_forward.py"""
import pandas as pd
COST = {"MGC": 0.292, "MNQ": 0.860, "MES": 0.494, "MYM": 3.44}   # points per round trip: fee + 1 tick
d = pd.read_csv("FORWARD_LOG.csv").dropna(subset=["exit_px"])
if not len(d): print("no closed trades yet"); raise SystemExit
sd = d.side.str.upper().map({"LONG": 1, "SHORT": -1})
d["risk"] = (d.entry - d.stop).abs()
d["net"] = (sd * (d.exit_px - d.entry) - d.market.map(COST)) / d.risk
n, wr, mean = len(d), (d.net > 0).mean(), d.net.mean(); share = d.market.value_counts(normalize=True)
print("trades %d | win %.0f%% | mean net R %+.3f | total %+.1f R" % (n, 100 * wr, mean, d.net.sum()))
print("market share: " + "  ".join("%s %.0f%%" % (k, 100 * v) for k, v in share.items()))
print(d.groupby("market").net.agg(["size", "mean"]).round(3).to_string())
ok = n >= 50 and mean > 0.05 and wr >= 0.53 and share.max() <= 0.40
print("VERDICT:", "BAR MET (a lead only)" if ok else ("INCONCLUSIVE (< 50 trades)" if n < 50 else "NOT MET: close the rule"))
