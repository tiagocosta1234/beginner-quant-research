"""Builds the benchmark sources (local only) into data/llm_bench/data.   python -m forex.self_improving.llm_bench.data
Lane MULTI: 16 markets, H1 bars from the MT5 M1 bid/ask files, 2021-12-01..2025-12-31 (2026 stays sealed). Lane TICK: EURUSD, XAUUSD, BTCUSD, 1-minute bars with MT5 tick volume, 2025-04-01..2025-12-31.
Columns: t (server-clock epoch), open, high, low, close (mid), bo, ao (bid/ask at the bar open, used by the harness for fills), spread_bp, tick_volume."""
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path("data/llm_bench/data")
MT5 = Path("forex/data_mt5")
MULTI = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "EURJPY", "GBPJPY", "XAUUSD", "XAGUSD", "SP", "NSDQ", "DAX", "NIKKEI", "BTCUSD", "ETHUSD"]
TICK = ["EURUSD", "XAUUSD", "BTCUSD"]
END = int(pd.Timestamp("2026-01-01").timestamp())


def build(sym, step, start):
    d = pd.read_parquet(MT5 / f"{sym}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]).sort_values("t").drop_duplicates("t")
    d = d[(d.t >= start) & (d.t < END) & (d.bo > 0) & (d.ao >= d.bo)]
    v = pd.read_parquet(f"data/ticks_vol/{sym}.parquet", columns=["time", "tick_volume"]).drop_duplicates("time").set_index("time").tick_volume
    d["tv"] = v.reindex(d.t.to_numpy()).to_numpy()
    d["mo"], d["mh"], d["ml"], d["mc"] = (d.bo + d.ao) / 2, (d.bh + d.ah) / 2, (d.bl + d.al) / 2, (d.bc + d.ac) / 2
    g = d.groupby((d.t // step) * step, sort=True)
    b = pd.DataFrame({"open": g.mo.first(), "high": g.mh.max(), "low": g.ml.min(), "close": g.mc.last(), "bo": g.bo.first(), "ao": g.ao.first(), "tick_volume": g.tv.sum(min_count=1)})
    b["spread_bp"] = (b.ao - b.bo) / b.open * 1e4
    b.index.name = "t"
    return b.reset_index()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s0 = int(pd.Timestamp("2021-12-01").timestamp())
    for s in MULTI:
        b = build(s, 3600, s0)
        b.to_parquet(OUT / f"MULTI__{s}_H1.parquet")
        print("MULTI", s, len(b))
    t0 = int(pd.Timestamp("2025-04-01").timestamp())
    for s in TICK:
        b = build(s, 60, t0)
        b.to_parquet(OUT / f"TICK__{s}_M1.parquet")
        print("TICK", s, len(b))


if __name__ == "__main__":
    main()
