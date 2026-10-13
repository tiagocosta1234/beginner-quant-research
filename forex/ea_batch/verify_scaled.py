"""Verify the pair's loadable lots in the real-tick Strategy Tester (the trader: "test it on every single aspect"): does 0.31 / 0.10 lots reproduce 31x / 10x the 0.01-lot results the replay is built on?

For every year 2022-2026 (2026 up to 09-30): Stochastic Daily Breakout (XAUUSD H1) at InpLots=0.31, XAUUSD 5 minute (Market, Use_Swing_SL=true) at Entry_Amount=0.10, MT5 broker server, real ticks, $100K, leverage 1:100.
Compared with the 0.01-lot runs in results_<year>/ (net P&L, maximal equity drawdown, number of deals, the daily P&L correlation). Also the ladder lots in 2026: Stochastic 0.21 / 0.10, XAU5min 0.07 / 0.03.
STOP THE EA BATCH BEFORE RUNNING (shared terminal).   python -m forex.ea_batch.verify_scaled
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_batch.tester_run import run_test
from forex.ea_batch.analyze_reports import daily_pnl

HERE = Path(__file__).resolve().parent
OUT = Path(r"D:\finance\scratch\verify_scaled"); OUT.mkdir(parents=True, exist_ok=True)
SPECS = {
    "stoch": dict(expert=r"ea_batch\77900\StochDailyBreakout.ex5", sym="XAUUSD", per="H1", base="77900", lot_key="InpLots", extra={}),
    "xau5": dict(expert=r"Market\XAUUSD 5 minute.ex5", sym="XAUUSD", per="M5", base="mkt_xau5min", lot_key="Entry_Amount", extra={"Use_Swing_SL": "true"}),
}


def baseline(base: str, year: int):
    f = HERE / f"results_{year}" / f"{base}.csv"
    d = pd.read_csv(f)
    st = pd.read_csv(HERE / f"results_{year}" / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last").set_index("id")
    return d, float((d.profit + d.commission + d.swap).sum()), float(st.loc[base, "eq_dd"]), f


def one(key: str, lot: float, year: int):
    sp = SPECS[key]
    frm, to = f"{year}.01.01", (f"{year}.12.31" if year < 2026 else "2026.09.30")
    r = run_test(f"v_{key}_{lot:.2f}_{year}", sp["expert"], sp["sym"], sp["per"], frm, to, {sp["lot_key"]: f"{lot:.2f}", **sp["extra"]})
    bd, bnet, bdd, bf = baseline(sp["base"], year)
    k = lot / 0.01
    row = dict(ea=key, lot=lot, year=year, note=r["note"], seconds=r["seconds"], deals=None if r["deals"] is None else len(r["deals"]), base_deals=len(bd), net=r["net"], expected_net=bnet * k,
               net_ratio=r["net"] / (bnet * k) if bnet else float("nan"), eq_dd=r["eq_dd"], expected_dd=bdd * k, dd_ratio=r["eq_dd"] / (bdd * k) if bdd else float("nan"))
    if r["deals"] is not None and len(r["deals"]):
        r["deals"].to_csv(OUT / f"{key}_{lot:.2f}_{year}.csv", index=False)
        a = daily_pnl(OUT / f"{key}_{lot:.2f}_{year}.csv"); b = daily_pnl(bf) * k
        j = pd.concat([a, b], axis=1).fillna(0.0)
        row["daily_corr"] = float(j.corr().iloc[0, 1]) if len(j) > 2 else float("nan")
        row["vol_set"] = sorted(set(r["deals"].volume.round(2)))[:4]
    print(json.dumps({k_: (round(v, 3) if isinstance(v, float) else v) for k_, v in row.items()}, default=str), flush=True)
    return row


def main():
    rows = []
    for year in (2026, 2025, 2024, 2023, 2022):
        rows.append(one("stoch", 0.31, year)); rows.append(one("xau5", 0.10, year))
    for key, lot in (("stoch", 0.21), ("stoch", 0.10), ("xau5", 0.07), ("xau5", 0.03)):
        rows.append(one(key, lot, 2026))
    pd.DataFrame(rows).to_csv(OUT / "verify_scaled.csv", index=False)
    print("done")


if __name__ == "__main__":
    main()
