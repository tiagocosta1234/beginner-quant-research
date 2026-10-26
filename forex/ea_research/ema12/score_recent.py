"""Scoring of the recent-2026 schedule and Look 2 (PREREG_BLIND2026 Amendments 8, 9, 11).
1. Converts the futures-priced rows of BLIND_LOG_EXTRA_FUT.csv to MT5 broker spot prices with the basis at the logged minute (GC close minus MT5 broker mid
   close, both on the local clock with the fixed MT5 broker offset), keeping his stop / target DISTANCES -> BLIND_LOG_EXTRA_mt5.csv.
2. Writes the pooled Look-2 log (January + batch 2 + extension rows) -> BLIND_LOOK2_FOR_SCORE.csv. blind_score.py is then run on both.
3. Futures secondary from BLIND_RESULTS_EXTRA_FUT.csv (app results): mean R, wins, random-side P (20,000 sign flips to the mirror trade,
   which on futures pays -R minus twice the cost in R; the app's R already includes one tick on entry and on stop exits).
4. The batch-3 gate (PREREG_BLIND2026_B3): batch-2 + batch-3 own-read trades >= 30 with >= 20 wins.
Usage (from ema12): python score_recent.py"""
import numpy as np, pandas as pd
import blind_png as B, spot_vs_futures as V

ext = pd.read_csv("BLIND_LOG_EXTRA_FUT.csv", dtype={"hhmm": str})
rows = []
for r in ext.itertuples():
    if not isinstance(r.side, str) or r.side not in ("L", "S"):
        rows.append(dict(date=r.date, ses=r.ses, side="", hhmm="", entry="", stop="", target="", flag=r.flag, pre=r.pre)); continue
    t = pd.Timestamp(f"{r.date} {r.hhmm}")
    g = B.load_fut(r.date, t); s = V.spot_day(r.date)
    mid = float((s.loc[t, "bc"] + s.loc[t, "ac"]) / 2); basis = float(g.close.loc[t]) - mid
    rows.append(dict(date=r.date, ses=r.ses, side=r.side, hhmm=r.hhmm, entry=round(r.entry - basis, 2), stop=round(r.stop - basis, 2),
                     target=round(r.target - basis, 2), flag=r.flag, pre=r.pre, basis=round(basis, 2)))
E = pd.DataFrame(rows)
E.drop(columns=["basis"]).to_csv("BLIND_LOG_EXTRA_mt5.csv", index=False)
print("basis GC - MT5 broker at the logged minute: median %.2f, range %.2f .. %.2f" % (E.basis.median(), E.basis.min(), E.basis.max()))
E[E.date >= "2026-07-27"].drop(columns=["basis"]).to_csv("BLIND_RECENT_mt5_FOR_SCORE.csv", index=False)

jan = pd.read_csv("BLIND_LOG_JAN2026_FXR.csv", dtype={"hhmm": str})
b2 = pd.read_csv("BLIND_B2_FOR_SCORE.csv", dtype={"hhmm": str})          # batch 2 as scored at Look 1 (23 Feb row converted, '~' stripped)
pd.concat([jan, b2, E.drop(columns=["basis"])], ignore_index=True).to_csv("BLIND_LOOK2_FOR_SCORE.csv", index=False)

# futures secondary (app results), recent schedule only
res = pd.read_csv("BLIND_RESULTS_EXTRA_FUT.csv")
rec = res[res.date >= "2026-07-27"].copy()
rec["R"] = pd.to_numeric(rec.R); rec["usd_750"] = pd.to_numeric(rec.usd_750); R = rec.R.to_numpy(float)
cost_R = 2 * 0.1 / (rec.entry - rec.stop).abs().to_numpy(float)              # entry tick + stop tick, in R
mirror = -R - cost_R
rng = np.random.default_rng(20261026)
p = float((np.where(rng.random((20000, len(R))) < 0.5, R, mirror).mean(axis=1) >= R.mean()).mean())
print("\nFUTURES (app) recent 2026: trades %d, wins %d (%.0f%%), mean R %+.3f, sum R %+.2f, random-side P %.4f, $ at $750 risk %+.0f" % (
    len(R), (R > 0).sum(), 100 * (R > 0).mean(), R.mean(), R.sum(), p, rec.usd_750.sum()))
print("  by month: " + "  ".join("%s %+.2fR (%d)" % (m, g.R.sum(), len(g)) for m, g in rec.groupby(rec.date.str[:7])))
b3 = set(open("BATCH3_DATES_SEALED.txt").read().split())
r3 = rec[rec.date.isin(b3)]
print("  sealed batch-3 days: %d trades, %d wins, sum R %+.2f" % (len(r3), (r3.R > 0).sum(), r3.R.sum()))
agree = (rec.side.map({"L": "long", "S": "short"}) == rec.bias)
print("  trade side = 07:59 bias on %d of %d trades; with the bias: %d wins / %d, against it: %d wins / %d" % (
    agree.sum(), len(rec), (rec[agree].R > 0).sum(), agree.sum(), (rec[~agree].R > 0).sum(), (~agree).sum()))
