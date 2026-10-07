"""
Round 347 robustness checks (POST HOC, disclosed: written after the interim results showed tester artifacts; the pre-registered verdict in
results_summary.* is not changed by this file).

  python forex/early_mt5/ea_batch/robustness_checks.py      # writes forex/early_mt5/ea_batch/robustness_summary.csv / .json

1. COMMISSION: the cloud run's offline custom symbols carry none. MT5 broker charges about $3 per lot per side on FX and XAUUSD (Round 272 probe:
   $6 a lot round trip), nothing on index CFDs. Each deal's commission is replaced by -3 x volume (FX, XAUUSD) and the pre-registered
   analyze_reports.py is re-run, unchanged, on that copy.
2. SUB-MINUTE HOLDS: the median time from an "in" deal to the next "out" deal; under 60 s the 1-minute-OHLC model invents the price path
   inside the bar, so the result is not resolvable (needs a real-tick test).
3. HIDDEN TAILS: the largest single closed loss at the EA's default lots above $3,000 (3% of $100K: one day's MT5 broker limit).
An EA is CLEAN only if it passes all three; the 70% bar is then read on the commission-charged run.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
COMM_SYMS = {"EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "USDCHF", "USDCAD", "XAUUSD", "NZDUSD", "GBPJPY", "EURJPY", "EURGBP", "XAGUSD"}
PER_SIDE = 3.0


def deal_stats(d: pd.DataFrame) -> tuple[float, float]:
    t = pd.to_datetime(d["time"].astype(str).str.replace(".", "-", regex=False), errors="coerce")
    dirn = d["direction"].astype(str).str.lower()
    holds, opens = [], []                                         # FIFO pairing: an EA can hold several positions at once
    for ti, di in zip(t, dirn):
        if "out" in di and opens:
            holds.append((ti - opens.pop(0)).total_seconds())
        if di in ("in", "in/out"):
            opens.append(ti)
    net = d["profit"] + d["commission"] + d["swap"]
    return (float(np.median(holds)) if holds else float("nan")), float(net[dirn.str.contains("out")].min()) if len(d) else 0.0


def main():
    status = pd.read_csv(RES / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last").set_index("id")
    tmp = Path(tempfile.mkdtemp(prefix="r347_comm_"))
    (tmp / "results").mkdir()
    shutil.copy(RES / "status.csv", tmp / "results" / "status.csv")
    flags = []
    for f in RES.glob("*.csv"):
        if f.name == "status.csv":
            continue
        d = pd.read_csv(f)
        if d.empty:
            continue
        sym = str(status.loc[f.stem, "symbol"]) if f.stem in status.index else ""
        hold, worst = deal_stats(d)
        flags.append(dict(id=f.stem, median_hold_s=hold, worst_loss=worst))
        if sym in COMM_SYMS:
            d["commission"] = -PER_SIDE * d["volume"].abs()
        d.to_csv(tmp / "results" / f.name, index=False)
    env = dict(os.environ, EA_BATCH_RESULTS=str(tmp / "results"), EA_BATCH_OUT=str(tmp))
    subprocess.run([sys.executable, str(HERE / "analyze_reports.py")], env=env, check=True, capture_output=True)
    base = pd.read_csv(HERE / "results_summary.csv", dtype={"id": str})
    comm = pd.read_csv(tmp / "results_summary.csv", dtype={"id": str})
    fl = pd.DataFrame(flags)
    m = base[["id", "title", "symbol", "period", "testable", "pass30_IS", "pass30_OOS", "bh", "beats_table", "meets_70"]].merge(
        comm[["id", "pass30_IS", "pass30_OOS", "bh", "beats_table", "meets_70"]].rename(columns=lambda c: c if c == "id" else c + "_comm"), on="id", how="left").merge(fl, on="id", how="left")
    m["sub_minute"] = m.median_hold_s < 60
    m["tail_over_3pct"] = m.worst_loss < -3000
    m["clean"] = m.testable.fillna(False).astype(bool) & ~m.sub_minute.fillna(False) & ~m.tail_over_3pct.fillna(False)
    m["clean_meets_70"] = m.clean & m.meets_70_comm.fillna(False).astype(bool)
    m["clean_beats_table"] = m.clean & m.beats_table_comm.fillna(False).astype(bool)
    m["clean_edge"] = m.clean & m.bh_comm.fillna(False).astype(bool)
    m.sort_values("pass30_OOS_comm", ascending=False).to_csv(HERE / "robustness_summary.csv", index=False)
    t = m[m.testable.fillna(False).astype(bool)]
    out = dict(testable=int(len(t)), sub_minute=int(t.sub_minute.sum()), tail_over_3pct=int(t.tail_over_3pct.sum()), clean=int(t.clean.sum()),
               with_commission=dict(bh=int(t.bh_comm.fillna(False).astype(bool).sum()), beats_table=int(t.beats_table_comm.fillna(False).astype(bool).sum()),
                                    meets_70=int(t.meets_70_comm.fillna(False).astype(bool).sum())),
               clean_and=dict(bh=int(t.clean_edge.sum()), beats_table=int(t.clean_beats_table.sum()), meets_70=int(t.clean_meets_70.sum())),
               survivors=t[t.bh | t.beats_table | t.meets_70][["id", "title", "symbol", "pass30_IS", "pass30_OOS", "pass30_IS_comm", "pass30_OOS_comm",
                                                              "median_hold_s", "worst_loss", "clean"]].round(3).to_dict("records"))
    json.dump(out, open(HERE / "robustness_summary.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != "survivors"}, indent=1))
    print(pd.DataFrame(out["survivors"]).sort_values("pass30_OOS", ascending=False).to_string(index=False))
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
