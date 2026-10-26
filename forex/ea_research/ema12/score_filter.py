"""PREREG_CLAUDE_FILTER step 3 (run only after CLAUDE_FILTER_CALLS.csv was hashed): outcomes of the trader's logged trades on GC futures with the app
convention (fill at the next minute's open one tick worse; stop exit one tick worse; target at its price; ties = stop; 17:00 close), then
TAKE vs SKIP. Usage: python score_filter.py"""
import numpy as np, pandas as pd
import blind_png as B

L = pd.read_csv("BLIND_LOG_FILTER.csv", dtype={"hhmm": str}); L = L[L.side.isin(["L", "S"])].reset_index(drop=True)
C = pd.read_csv("CLAUDE_FILTER_CALLS.csv")
assert list(C.date) == list(L.date) and list(C.side) == list(L.side)
R = []
for r in L.itertuples():
    sd = 1 if r.side == "L" else -1; sdist, tdist = abs(r.entry - r.stop), abs(r.target - r.entry)
    g = B.load_fut(r.date, pd.Timestamp(f"{r.date} 17:00")); g = g[g.index > pd.Timestamp(f"{r.date} {r.hhmm}")]
    fill = g.open.iloc[0] + sd * 0.1; sl, tp = fill - sd * sdist, fill + sd * tdist; out = None
    for ts, b in g.iterrows():
        if (b.low <= sl) if sd > 0 else (b.high >= sl): out = -1 - 0.1 / sdist; break
        if (b.high >= tp) if sd > 0 else (b.low <= tp): out = tdist / sdist; break
    if out is None: out = sd * (g.close.iloc[-1] - fill) / sdist
    R.append(out)
C["R"] = np.round(R, 3); C.to_csv("FILTER_RESULTS.csv", index=False)
take, skip = C[C.call == "TAKE"].R.to_numpy(), C[C.call == "SKIP"].R.to_numpy()
diff = take.mean() - skip.mean()
rng = np.random.default_rng(20261026); allR = C.R.to_numpy(); nT = len(take)
perm = np.array([(lambda p: allR[p[:nT]].mean() - allR[p[nT:]].mean())(rng.permutation(len(allR))) for _ in range(20000)])
p = float((perm >= diff).mean())
print("the trader ALL   n %2d  wins %2d (%.0f%%)  mean R %+.3f  sum %+.2f" % (len(allR), (allR > 0).sum(), 100 * (allR > 0).mean(), allR.mean(), allR.sum()))
print("TAKE       n %2d  wins %2d (%.0f%%)  mean R %+.3f  sum %+.2f" % (len(take), (take > 0).sum(), 100 * (take > 0).mean(), take.mean(), take.sum()))
print("SKIP       n %2d  wins %2d (%.0f%%)  mean R %+.3f  sum %+.2f" % (len(skip), (skip > 0).sum(), 100 * (skip > 0).mean(), skip.mean(), skip.sum()))
print("TAKE - SKIP %+.3f R, permutation P %.4f  ->  %s" % (diff, p, "FILTER WORKS" if (diff >= 0.20 and p <= 0.05 and take.mean() > 0) else "NOT SHOWN"))
for (call, conf), g in C.groupby(["call", "confidence"]):
    print("  %-4s conf %d: n %2d  wins %2d  mean R %+.3f" % (call, conf, len(g), (g.R > 0).sum(), g.R.mean()))
