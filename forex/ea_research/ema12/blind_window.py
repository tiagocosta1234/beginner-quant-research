"""Random 30-calendar-day extension window of the blind replay (PREREG_BLIND2026 Amendment 2: used only if Look 1 does not decide). python blind_window.py [seed] [--avoid START END] [--out FILE]
Drawn from 2022-2025 only: 2026 stays reserved for batches 1-2, and a window never overlaps his first sample (14 Apr-12 May 2025) or an earlier window (--avoid). Reads only the time column of the MT5 broker gold file (no prices)."""
import sys, numpy as np, pandas as pd
from ema12_test import open_min
args = sys.argv[1:]; seed = int(args[0]) if args and args[0].isdigit() else 202610193; OUT = args[args.index("--out") + 1] if "--out" in args else "BLIND_EXTRA.csv"
AV = (pd.Timestamp(args[args.index("--avoid") + 1]), pd.Timestamp(args[args.index("--avoid") + 2])) if "--avoid" in args else None   # a window already drawn: never overlap it
lo, hi, A0, A1 = pd.Timestamp("2022-01-03"), pd.Timestamp("2025-12-31"), pd.Timestamp("2025-04-14"), pd.Timestamp("2025-05-12")
t = pd.read_parquet("D:/finance/beginner-quant-research/forex/data_mt5/XAUUSD_M1_rates.parquet", columns=["t"], filters=[("t", ">=", int(lo.timestamp())), ("t", "<", int((hi + pd.Timedelta(days=1)).timestamp()))]).t
d = pd.DataFrame({"dt": pd.to_datetime(t, unit="s")}); d["day"] = d.dt.dt.date; d["hm"] = d.dt.dt.hour * 60 + d.dt.dt.minute
ok = sorted(dy for dy, g in d.groupby("day") if dy.weekday() < 5 and ((g.hm >= open_min(dy, "London")) & (g.hm <= open_min(dy, "London") + 14)).sum() >= 10)
starts = [dy for dy in ok if pd.Timestamp(dy) + pd.Timedelta(days=29) <= hi and not (pd.Timestamp(dy) <= A1 and pd.Timestamp(dy) + pd.Timedelta(days=29) >= A0) and not (AV and pd.Timestamp(dy) <= AV[1] and pd.Timestamp(dy) + pd.Timedelta(days=29) >= AV[0])]
start = pd.Timestamp(starts[int(np.random.default_rng(seed).integers(len(starts)))]); end = start + pd.Timedelta(days=29)
win = [dy for dy in ok if start <= pd.Timestamp(dy) <= end]
print("seed %d | %d eligible weekdays, %d eligible start days | start %s (%s), end %s | %d London sessions with data" % (seed, len(ok), len(starts), start.date(), start.strftime("%a"), end.date(), len(win)))
out = pd.DataFrame({"order": range(1, len(win) + 1), "date": [str(x) for x in win], "weekday": [x.strftime("%a") for x in win]}); print(out.to_string(index=False)); out.to_csv(OUT, index=False)
