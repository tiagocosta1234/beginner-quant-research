"""ManualSDB with InpRunner off / on in the MT5 Strategy Tester on MT5 broker real ticks (portable tester terminal D:\finance\mt5_mt5_tester, never the live terminal), XAUUSD+ H1, 2025-10-01..2026-09-30, 0.12 lot, guard off.
python -m forex.self_improving.session.verify_sdb_runner"""
import pandas as pd
from forex.ea_batch import mt5data_run as ER

TR = ER.TR


def main():
    for name, runner in (("sdb_runner_off", "false"), ("sdb_runner_on", "true")):
        r = TR.run_test(name, r"the trader\ManualSDB_run.ex5", "XAUUSD+", "H1", "2025.10.01", "2026.09.30", {"InpLots": "0.12", "InpUseGuard": "false", "InpRunner": runner}, timeout=7200)
        d = r["deals"]; print(f"{name}: net {r['net']:,.2f} | note {r['note']!r} | seconds {r['seconds']} | eq DD {r['eq_dd']}", flush=True)
        if d is not None: d.to_csv(f"D:/finance/si_ledgers/{name.upper()}_deals.csv", index=False); o = d[d.direction.astype(str).str.lower().str.startswith("out")]; print("  closed trades", len(o), flush=True)


if __name__ == "__main__":
    main()
