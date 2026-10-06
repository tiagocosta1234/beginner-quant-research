"""The XAUUSD 5 minute product page (v7.3) says: attach to M15 (newer versions use M15); our tests and deployment kit used M5. Runs the Market EA at default inputs on M15 for 2026 / 2025 / 2024 and compares with the M5 runs (results_<year>/mkt_xau5min.csv, net / trades).  STOP THE BATCH / SCREEN FIRST.
  python -m mt5broker.ea_batch.xau5_m15_check
"""
import pandas as pd

from mt5broker.ea_batch.tester_run import run_test

for y, frm, to in ((2026, "2026.01.01", "2026.09.30"), (2025, "2025.01.01", "2025.12.31"), (2024, "2024.01.01", "2024.12.31")):
    r = run_test(f"xau5_m15_{y}", r"Market\XAUUSD 5 minute.ex5", "XAUUSD", "M15", frm, to, None, timeout=2400)
    d = r["deals"]
    o = d[d.direction == "out"] if d is not None and len(d) else None
    m5 = pd.read_csv(f"forex/early_mt5/ea_batch/results_{y}/mkt_xau5min.csv"); m5o = m5[m5.direction == "out"]
    print(f"{y}: M15 trips {0 if o is None else len(o)} net {0 if o is None else float((o.profit + o.commission + o.swap).sum()):,.0f} eq_dd {r['eq_dd']} | M5 trips {len(m5o)} net {float((m5o.profit + m5o.commission + m5o.swap).sum()):,.0f} {r['note']}", flush=True)
    if d is not None and len(d):
        d.to_csv(f"forex/early_mt5/ea_batch/results_{y}/mkt_xau5min_M15.csv", index=False)
