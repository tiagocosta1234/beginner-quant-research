"""Family SM: ManualSDB on 12 other MT5, exactly as registered in PREREG_SDB_MARKETS.md.
   python -m mt5broker.ea_research.sdb_markets --run (DEV+VAL, resumable) | --report | --holdout"""
from __future__ import annotations

import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_batch import mt5data_run as ER

OUT = Path(__file__).resolve().parents[1] / "ea_batch" / "sdb_markets"; OUT.mkdir(exist_ok=True)
RATIO = {"NSDQ": 2.54, "SP": 1.74, "DOW": 1.44, "DAX": 1.82, "NIKKEI": 1.62, "BTCUSD": 5.06, "ETHUSD": 5.97, "WTI": 2.65, "EURUSD": 0.61, "GBPUSD": 0.51, "USDJPY": 0.43, "AUDUSD": 0.86}
DEV, VAL, HOLD = ("2022", "2023", "2024"), ("2025",), ("2026",)


def run(mkt: str, var: str, year: str) -> None:
    f = OUT / f"{mkt}_{var}_{year}.csv"; meta = OUT / f"{mkt}_{var}_{year}.json"
    if meta.exists(): return
    pct = 1.9 if var == "SM1" else round(1.9 * RATIO[mkt], 3); frm, to = ER.YEARS[year]
    inputs = {"InpLots": "0.01", "InpRiskPct": "1.0", "InpRiskBase": "100000", "InpUseGuard": "false", "InpStopPct": str(pct), "InpTargetPct": str(pct)}
    r = ER.TR.run_test(f"sm_{mkt}_{var}_{year}", r"the trader\ManualSDB.ex5", f"{mkt}+", "H1", frm, to, inputs, timeout=900)          # a hung run (NSDQ SM2 2024, 2026-10-11) blocked the batch for an hour: 15 min cap
    d = r.get("deals"); n = 0 if d is None else len(d)
    if n: d.to_csv(f, index=False)
    meta.write_text(json.dumps(dict(mkt=mkt, var=var, year=year, stop_pct=pct, deals=n, net=float(r["net"]) if n else 0.0, eq_dd=float(r["eq_dd"]) if n else 0.0, note=r.get("note") or "")))
    print(f"{mkt} {var} {year}: deals {n} net {r['net'] if n else 0:,.0f} note {r.get('note')!r}", flush=True)


def stats(mkt, var, years):
    pls, per = [], {}
    for y in years:
        f = OUT / f"{mkt}_{var}_{y}.csv"
        if not f.exists(): per[y] = (0, np.nan); continue
        d = pd.read_csv(f); o = d[d.direction == "out"]; p = (o.profit + o.commission + o.swap).to_numpy(); pls.append(p)
        per[y] = (len(p), p[p > 0].sum() / -p[p < 0].sum() if (p < 0).any() else np.inf)
    p = np.concatenate(pls) if pls else np.array([])
    pf = p[p > 0].sum() / -p[p < 0].sum() if (p < 0).any() else np.nan
    t = p.mean() / (p.std(ddof=1) / np.sqrt(len(p))) if len(p) > 2 else np.nan
    return dict(trades=len(p), net=float(p.sum()) if len(p) else 0.0, pf=pf, t=t, per=per)


def report(open_hold=False):
    rows = []
    for mkt in RATIO:
        for var in ("SM1", "SM2"):
            dv, vl = stats(mkt, var, DEV), stats(mkt, var, VAL)
            yrs_ok = sum(1 for y in DEV if np.isfinite(dv["per"][y][1]) and dv["per"][y][1] >= 1.0)
            acc = bool(dv["pf"] >= 1.2 and yrs_ok >= 2 and dv["trades"] >= 60 and vl["pf"] >= 1.1)
            row = dict(market=mkt, var=var, dev_trades=dv["trades"], dev_net=round(dv["net"]), dev_pf=round(dv["pf"], 2), dev_t=round(dv["t"], 2), dev_years_ok=yrs_ok,
                       val_trades=vl["trades"], val_net=round(vl["net"]), val_pf=round(vl["pf"], 2), to_holdout=acc)
            if open_hold and acc:
                for y in HOLD: run(mkt, var, y)
                h = stats(mkt, var, HOLD); row.update(hold_trades=h["trades"], hold_net=round(h["net"]), hold_pf=round(h["pf"], 2), PASS=bool(h["pf"] >= 1.1 and h["net"] > 0))
            rows.append(row)
    R = pd.DataFrame(rows); txt = R.to_string(index=False); print(txt)
    (Path(__file__).resolve().parent / ("SDB_MARKETS_HOLDOUT.txt" if open_hold else "SDB_MARKETS_DEV.txt")).write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    if "--run" in sys.argv:
        for mkt in RATIO:
            for var in ("SM1", "SM2"):
                for y in DEV + VAL: run(mkt, var, y)
        report()
    if "--report" in sys.argv: report()
    if "--holdout" in sys.argv: report(True)
