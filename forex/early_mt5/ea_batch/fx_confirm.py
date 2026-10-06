"""Out-of-time check of the best FX EAs of the 2026 screen (ranked by net / tester equity drawdown): the top ones that never reached the 2024-25 confirmation. Default inputs, real ticks, $100K, each year 2022-2025 on the EA's own symbol and period.
Reported per year: round trips, net, tester equity drawdown (% of $100K), profit factor. Pre-registered pass: net > 0 and equity drawdown <= 10% in at least 3 of the 4 years.  STOP THE SCREEN / BATCH FIRST.   python -m mt5broker.ea_batch.fx_confirm
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from mt5broker.ea_batch.tester_run import run_test

HERE = Path(__file__).resolve().parent
IDS = ("23029", "64444", "19968")                      # BADX EURUSD M30, Babi Ngepet EURUSD H1, Invest System 4.5 EURUSD M30


def main():
    s = pd.read_csv(HERE / "results_2026" / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last").set_index("id")
    m = pd.read_csv(HERE / "manifest.csv", dtype={"id": str}).set_index("id")
    for eid in IDS:
        sym, per, main_f = s.loc[eid, "symbol"], s.loc[eid, "period"], m.loc[eid, "main"]
        for y in (2022, 2023, 2024, 2025):
            if (HERE / f"results_{y}" / f"{eid}.csv").exists():                        # resumable: a saved run is not repeated
                continue
            r = run_test(f"fxc_{eid}_{y}", f"ea_batch\\{eid}\\{Path(main_f).with_suffix('.ex5').name}", sym, per, f"{y}.01.01", f"{y}.12.31", None, timeout=2400)
            d = r["deals"]; o = d[d.direction == "out"] if d is not None and len(d) else None
            net = float((o.profit + o.commission + o.swap).sum()) if o is not None else float("nan")
            w = (o.profit + o.commission + o.swap); pf = float(w[w > 0].sum() / -w[w <= 0].sum()) if o is not None and (w <= 0).any() and w[w <= 0].sum() < 0 else float("nan")
            print(f"{eid} {s.loc[eid, 'title'][:26]:<26} {sym} {per} {y}: trips {0 if o is None else len(o)} net {net:,.0f} eqDD {r['eq_dd'] / 1000:.1f}% pf {pf:.2f} {r['note']}", flush=True)
            if d is not None and len(d):
                d.to_csv(HERE / f"results_{y}" / f"{eid}.csv", index=False)


if __name__ == "__main__":
    main()
