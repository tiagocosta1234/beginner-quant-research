"""Frozen SDB (CodeBase 77900, defaults, 0.01 lot, H1) on XAGUSD+ in the portable MT5 broker tester, as registered in PREREG_SDB_SILVER.md.
   python -m mt5broker.ea_research.sdb_silver_run --run 2022,2023,2024,2025      run the tester per year (resumable), then print the analysis
   python -m mt5broker.ea_research.sdb_silver_run --analyse 2022,2023,2024,2025  analysis only (silver + the gold control from the existing MT5 broker runs)
   python -m mt5broker.ea_research.sdb_silver_run --run 2026                     the one-time hold-out (only if DEV and VAL passed)"""
import sys
_args = sys.argv[1:]; sys.argv = ["x"]
import numpy as np, pandas as pd
from pathlib import Path
from mt5broker.ea_batch import mt5data_run as ER

HERE = Path(__file__).resolve().parent; OUT = HERE / "sdb_silver"; LEDGER = HERE / "LEDGER.csv"
EXPERT = r"ea_batch\77900\StochDailyBreakout.ex5"; CONTRACT = {"XAGUSD+": 5000.0, "XAUUSD+": 100.0}


def run_year(sym: str, year: str):
    f = OUT / f"{sym.replace('+', '')}_{year}.csv"
    if f.exists(): print("skip", f.name); return
    frm, to = ER.YEARS[year]; r = ER.TR.run_test(f"sdbsilver_{sym.replace('+','')}_{year}", EXPERT, sym, "H1", frm, to, None, timeout=7200)
    q = ER.quality(r.get("report")); d = r.get("deals")
    print(f"{sym} {year}: seconds {r['seconds']} deals {0 if d is None else len(d)} net {r['net']:.2f} quality {q} note {r['note']!r}", flush=True)
    if d is not None and len(d): d.to_csv(f, index=False)


def trades(sym: str, year: str) -> pd.DataFrame:
    f = OUT / f"{sym.replace('+', '')}_{year}.csv" if sym == "XAGUSD+" else Path("forex/early_mt5/ea_batch/mt5data") / f"results_{year}" / "77900.csv"
    if not f.exists(): return pd.DataFrame()
    d = pd.read_csv(f); d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S")
    i = d[d.direction == "in"].reset_index(drop=True); o = d[d.direction == "out"].reset_index(drop=True); n = min(len(i), len(o))
    t = pd.DataFrame({"t_in": i.time[:n], "t_out": o.time[:n], "entry": i.price[:n], "exit": o.price[:n], "profit": o.profit[:n] + o.commission[:n]})   # swap zeroed: swap-free account
    move = t.exit - t.entry; t["side"] = np.where(t.profit * move >= 0, 1.0, -1.0); t.loc[move == 0, "side"] = 1.0
    t["bp"] = t.side * move / t.entry * 1e4; t["day"] = t.t_out.dt.normalize(); return t


def stats(t: pd.DataFrame) -> dict:
    if not len(t): return dict(n=0, mean=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"), net=0.0)
    w, l = t.bp[t.bp > 0].sum(), -t.bp[t.bp <= 0].sum(); n = len(t)
    return dict(n=n, mean=float(t.bp.mean()), pf=float(w / l) if l > 0 else float("inf"), t=float(t.bp.mean() / (t.bp.std(ddof=1) / np.sqrt(n))) if n > 2 else float("nan"), win=float((t.bp > 0).mean()), net=float(t.bp.sum()))


def fmt(tag, s): return f"{tag:34s} trades {s['n']:4d} | mean {s['mean']:+7.1f} bp/trade | PF {s['pf']:5.2f} | per-trade t {s['t']:+5.2f} | win {100*s['win']:4.1f}% | net {s['net']:+9,.0f} bp"


def analyse(years):
    pools = {"DEV": [y for y in years if y in ("2022", "2023", "2024")], "VAL": [y for y in years if y == "2025"], "HOLD": [y for y in years if y == "2026"]}
    for sym, lab in (("XAGUSD+", "SILVER"), ("XAUUSD+", "GOLD control")):
        for y in years:
            t = trades(sym, y); print(fmt(f"{lab} {y}", stats(t)))
        for per, ys in pools.items():
            if ys:
                t = pd.concat([trades(sym, y) for y in ys]); s = stats(t); print(fmt(f"{lab} {per} ({','.join(ys)})", s))
                if sym == "XAGUSD+":
                    with open(LEDGER, "a", encoding="utf-8") as f:
                        f.write(f"2026-10-09 10:xx,sdb_silver,S-{per},{per},,{s['n']},{s['net']:.1f},{s['mean']:.3f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},frozen SDB 77900 on XAGUSD+ H1\n")


if __name__ == "__main__":
    yrs = (_args[_args.index("--run") + 1] if "--run" in _args else _args[_args.index("--analyse") + 1]).split(",")
    if "--run" in _args:
        for y in yrs: run_year("XAGUSD+", y)
    analyse(yrs)
