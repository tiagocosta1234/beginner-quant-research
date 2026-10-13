"""Verify ManualSDB (forex/expert_advisors/ManualSDB.mq5) against the original SDB EA (batch id 77900): same symbol / period / dates, real-tick tester, default inputs (0.01 lot).
   python -m forex.ea_batch.verify_manualsdb      (stop the batch first: both use the one MT5 terminal)
Compares every deal (time, direction, volume, price) of the 2026 screen's results_2026/77900.csv with the ManualSDB run."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from forex.ea_batch import run_batch as rb

REF = Path(__file__).resolve().parent / "results_2026" / "77900.csv"


def main():
    rb.FROM, rb.TO = "2026.01.01", "2026.09.30"
    extra = sys.argv[1:]                                    # optional: expert path, e.g. ea_own\ManualSDB.ex5
    data = rb.data_folder(); rep_root = data / "ea_batch_reports"; rep_root.mkdir(exist_ok=True)
    for old in rep_root.glob("manualsdb_verify*"):
        old.unlink()
    ini = Path("D:/finance/scratch/manualsdb_verify.ini")
    rb.write_ini(ini, extra[0] if extra else r"ea_own\ManualSDB.ex5", "XAUUSD", "H1", r"ea_batch_reports\manualsdb_verify", 4)
    rb.kill_terminal()
    p = rb.start_terminal(ini)
    p.wait(timeout=1500)
    htm = next(iter(rep_root.glob("manualsdb_verify*.htm*")), None)
    if htm is None:
        sys.exit("no report")
    new = rb.parse_report(htm); new.to_csv(Path("D:/finance/scratch/manualsdb_verify_deals.csv"), index=False)
    ref = pd.read_csv(REF)
    cols = ["time", "direction", "volume", "price"]
    a, b = ref[cols].reset_index(drop=True), new[cols].reset_index(drop=True)
    print(f"original deals {len(a)}, ManualSDB deals {len(b)}")
    if len(a) == len(b):
        same = (a.time == b.time) & (a.direction == b.direction) & (a.volume == b.volume) & ((a.price - b.price).abs() < 1e-6)
        print(f"identical deals: {int(same.sum())} of {len(a)}")
        if not same.all():
            print(pd.concat([a[~same], b[~same]], axis=1, keys=["orig", "manual"]).head(20).to_string())
    else:
        print("original:", a.head(6).to_string(), "\nManualSDB:", b.head(6).to_string(), sep="\n")
    print("net original", round(float(ref.profit.sum() + ref.commission.sum() + ref.swap.sum()), 2), "net ManualSDB", round(float(new.profit.sum() + new.commission.sum() + new.swap.sum()), 2))


if __name__ == "__main__":
    main()
