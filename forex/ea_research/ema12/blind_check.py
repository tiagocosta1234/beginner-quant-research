"""FORMAT-ONLY check of the blind-replay log (no outcome is computed): does the logged entry price sit on the MT5 broker price path at the logged minute?
python blind_check.py LOG.csv     LOG.csv as for blind_score.py. For each trade prints the MT5 broker mid close of the logged minute and of the minutes around it (offsets -4..+4), the difference entry - MT5, and the offset whose difference is closest to the median basis (FX Replay's OANDA feed vs MT5 broker differ by a roughly constant basis)."""
import sys, numpy as np, pandas as pd
from blind_score import load_days
log = pd.read_csv(sys.argv[1], dtype={"hhmm": str}); log = log[log.side.isin(["L", "S"])].reset_index(drop=True)
days = load_days(log.date.min(), log.date.max()); rows = []
for _, r in log.iterrows():
    g = days[pd.Timestamp(r.date).date()]; hm = int(r.hhmm[:2]) * 60 + int(r.hhmm[3:]) + 120; d = {}
    for o in range(-4, 5):
        j = g.index[g.hm == hm + o]
        d[o] = float(r.entry - ((g.bc[j[0]] + g.ac[j[0]]) / 2)) if len(j) else np.nan
    rows.append(d)
D = pd.DataFrame(rows); basis = float(np.nanmedian(D[0])); print("basis (entry - MT5 broker mid close at the logged minute), median over trades: %+.2f" % basis)
for i, r in log.iterrows():
    dev = (D.loc[i] - basis).abs(); best = int(dev.idxmin())
    print("%s %s entry %.3f logged %s | diff at 0: %+.2f | closest-to-basis offset %+d (%+.2f) | diffs -2..+2: %s" % (r.date, r.side, r.entry, r.hhmm, D.loc[i, 0], best, D.loc[i, best] - basis, " ".join("%+.2f" % D.loc[i, o] for o in range(-2, 3))))
