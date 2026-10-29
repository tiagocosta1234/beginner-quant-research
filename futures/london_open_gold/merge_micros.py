"""27 Oct 2026: merge the old BrokerAPI 1m files (29 Jul..25/27 Sep) with the new pull (28 Aug..27 Oct, brokerapi_2026-10-27/) into one series per micro symbol:
old rows before the new file's first bar + all new rows (the overlap is identical bar for bar except MCL, which rolled contract, so MCL keeps old only before 28 Aug).
Writes data/merged_micros_2026-10-27/<SYM>_1MIN_MERGED.csv; the originals are not touched. Usage: python merge_micros.py"""
import pandas as pd
from pathlib import Path
D = Path("futures/data"); OUT = D / "merged_micros_2026-10-27"; OUT.mkdir(exist_ok=True)
for s in ("MGC", "SIL", "MNQ", "MES", "MYM", "M2K", "MCL", "MBT", "MET"):
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    o = pd.read_csv(D / f"{s}_1MIN_BROKERAPI.csv", usecols=cols); n = pd.read_csv(D / "brokerapi_2026-10-27" / f"{s}_1MIN_BROKERAPI.csv", usecols=cols)
    for d in (o, n): d["t"] = pd.to_datetime(d.timestamp, utc=True)
    m = pd.concat([o[o.t < n.t.min()], n]).drop_duplicates("t").sort_values("t")
    m["timestamp"] = m.t.dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    m[cols].to_csv(OUT / f"{s}_1MIN_MERGED.csv", index=False)
    print(f"{s}: {len(m):,} bars, {m.t.min():%d %b %H:%M} -> {m.t.max():%d %b %H:%M} UTC (old rows kept {int((o.t < n.t.min()).sum()):,}, new {len(n):,}), duplicate timestamps {int(m.t.duplicated().sum())}")
