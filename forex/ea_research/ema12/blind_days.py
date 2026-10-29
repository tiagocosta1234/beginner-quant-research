"""Day lists for the blind replay (PREREG_BLIND2026.md). python blind_days.py --batch 1 | --batch 2
Reads only the time column of the MT5 broker gold file (no prices): a day is eligible if it is a weekday with >= 10 one-minute bars in the first 15 minutes of the London session.
Batch 1 = every eligible weekday of January 2026, shuffled (seed 20261019). Batch 2 = 30 eligible weekdays drawn from 2026-02-02..2026-09-30 (seed 20261020), made only when batch 1 says continue."""
import sys, numpy as np, pandas as pd
from ema12_test import open_min
BATCH = {"1": ("2026-01-01", "2026-01-31", 20261019, None), "2": ("2026-02-02", "2026-09-30", 20261020, 30)}
b = sys.argv[sys.argv.index("--batch") + 1] if "--batch" in sys.argv else "1"
lo, hi, seed, k = BATCH[b]
t = pd.read_parquet("forex/data_mt5/XAUUSD_M1_rates.parquet", columns=["t"],
                    filters=[("t", ">=", int(pd.Timestamp(lo).timestamp())), ("t", "<", int((pd.Timestamp(hi) + pd.Timedelta(days=1)).timestamp()))]).t
d = pd.DataFrame({"dt": pd.to_datetime(t, unit="s")}); d["day"] = d.dt.dt.date; d["hm"] = d.dt.dt.hour * 60 + d.dt.dt.minute
ok = sorted(dy for dy, g in d.groupby("day") if dy.weekday() < 5 and ((g.hm >= open_min(dy, "London")) & (g.hm <= open_min(dy, "London") + 14)).sum() >= 10)
order = list(np.random.default_rng(seed).permutation(len(ok))[:k or len(ok)])
out = pd.DataFrame({"order": range(1, len(order) + 1), "date": [str(ok[i]) for i in order], "weekday": [ok[i].strftime("%a") for i in order]})
print("eligible weekdays %d (%s..%s), seed %d, listed %d" % (len(ok), ok[0], ok[-1], seed, len(out)))
print(out.to_string(index=False)); out.to_csv("BLIND_BATCH%s.csv" % b, index=False)
