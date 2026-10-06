"""Register an EA that was backtested by hand -- a MetaTrader Market .ex5, which is not in manifest.csv -- so that stages 1-3 treat it like any batch EA.

For each year given, the deals CSV (the format run_batch.py writes: time, direction, volume, price, commission, swap, profit) is copied to results_<year>/<id>.csv and one row is
appended to results_<year>/status.csv, with the tester's own equity / balance drawdown read from the HTML report. 2026 is the stage-1 run, 2025 and 2024 the confirmation runs.
Run the tests first with the same settings as the batch: real ticks (model 4), commission, $100K, the EA's default inputs, the whole year (2026: 2026.01.01 - 2026.09.30).

  python -m mt5broker.ea_batch.register_market_ea --id mkt_xau5min --title "XAUUSD 5 minute (Market)" --symbol XAUUSD --period M5 \\
      --run 2026=deals2026.csv,report2026.htm --run 2025=deals2025.csv,report2025.htm --run 2024=deals2024.csv,report2024.htm

Existing ids are left alone. Append-only, so it is safe while the batch is running.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd

from mt5broker.ea_batch.run_batch import parse_drawdowns

HERE = Path(__file__).resolve().parent


def register(eid: str, title: str, symbol: str, period: str, runs: dict) -> None:
    for year, (csv, htm) in runs.items():
        rd = HERE / f"results_{year}"; rd.mkdir(exist_ok=True)
        stf = rd / "status.csv"
        if stf.exists() and eid in set(pd.read_csv(stf, dtype={"id": str}).id):
            print(f"{year}: {eid} already registered"); continue
        d = pd.read_csv(csv)
        shutil.copy(csv, rd / f"{eid}.csv")
        eq, bal = parse_drawdowns(Path(htm))
        rec = dict(id=eid, title=title, symbol=symbol, period=period, compiled=True, deals=len(d), net=float((d.profit + d.commission + d.swap).sum()), seconds=0.0,
                   note="registered by hand (Market EA)", eq_dd=eq, bal_dd=bal)
        pd.DataFrame([rec]).to_csv(stf, mode="a", header=not stf.exists(), index=False)
        print(f"{year}: registered {eid}: {len(d)} deals, net {rec['net']:,.0f}, equity drawdown {eq:,.0f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True); ap.add_argument("--title", required=True); ap.add_argument("--symbol", required=True); ap.add_argument("--period", required=True)
    ap.add_argument("--run", action="append", required=True, help="YEAR=deals.csv,report.htm (repeat for each year)")
    a = ap.parse_args()
    runs = {}
    for item in a.run:
        year, files = item.split("=", 1)
        csv, htm = files.split(",", 1)
        runs[int(year)] = (csv, htm)
    register(a.id, a.title, a.symbol, a.period, runs)


if __name__ == "__main__":
    main()
