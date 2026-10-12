"""ManualFVG.mq5 in the MT5 Strategy Tester on MT5 broker real ticks (portable tester terminal), DAX+, 2025-10-01 .. 2026-09-30, risk 500 USD per trade;
R0 = no execution delay, R1 = 250 ms; compared with the Python model of the same rule (forex/early_mt5/ea_research/ict_scan.py FVG_KZ, slippage 0 and 1).
   python -m mt5broker.ea_batch.verify_manualfvg_mt5"""
from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_batch import mt5data_run as ER
from mt5broker.ea_batch.verify_manualonb_mt5 import trades_from_deals

TR, TERM = ER.TR, ER.TERM_DIR
FRM, TO, RISK = "2025.10.01", "2026.09.30", 500.0


def ea_log() -> list[str]:
    files = sorted(glob.glob(str(TERM / "Tester" / "Agent-*" / "logs" / "*.log")), key=os.path.getmtime)
    if not files: return []
    raw = Path(files[-1]).read_bytes(); txt = raw.decode("utf-16", errors="ignore") if raw[:2] == b"\xff\xfe" else raw.decode("utf-8", errors="ignore")
    return [l for l in txt.splitlines() if "[ManualFVG]" in l]


def main() -> int:
    out = {}
    for tag, mode in (("R0", 0), ("R1", 250)):
        r = TR.run_test(f"manualfvg_{tag}", r"the trader\ManualFVG.ex5", "DAX+", "M15", FRM, TO, {"InpRiskUSD": str(int(RISK))}, timeout=21600, execution_mode=mode)
        L = ea_log(); T = trades_from_deals(r["deals"]) if r["deals"] is not None and len(r["deals"]) else pd.DataFrame(columns=["entry", "exit", "side", "pts", "net"]); out[tag] = (r, L, T)
        print(f"\n=== {tag} (execution delay {mode} ms): net {r['net']:,.2f} | eq DD {r['eq_dd']} | seconds {r['seconds']} | note {r['note']!r}")
        placed = [l for l in L if "-> placed" in l]; rej = [l for l in L if "REJECTED" in l]; canc = [l for l in L if "cancelled" in l]
        print(f"EA log: {len(L)} lines | gaps placed {len(placed)} | rejected {len(rej)} | cancelled {len(canc)} | closed trades {len(T)}")
        if len(T):
            w, l_ = T.net[T.net > 0].sum(), -T.net[T.net < 0].sum(); day = T.groupby(pd.to_datetime(T.exit).dt.normalize()).net.sum(); eq = day.cumsum()
            print(f"tester: trades {len(T)}, win {100 * (T.net > 0).mean():.0f}%, net {T.net.sum():+,.0f} USD, PF {w / l_ if l_ else float('inf'):.2f}, avg {T.net.mean():+.1f} USD per trade (= {T.net.mean() / RISK:+.3f} R), worst day {day.min():,.0f}, best day {day.max():,.0f}, realised max drawdown {(eq.cummax() - eq).max():,.0f}")
    from mt5broker.ea_research import ict_scan as I
    for slip in (0.0, 1.0):
        I.SLIPPTS = slip; P = I.symbol_trades("DAX")["FVG_KZ"]; P.index = pd.to_datetime(P.index); P = P[(P.index >= "2025-10-01") & (P.index < "2026-10-01")]
        print(f"\nPython FVG_KZ DAX, same window, slippage {slip:.0f} pt: {len(P)} trades, mean {P.mean():+.3f} R, total {P.sum():+.1f} R = {P.sum() * RISK:+,.0f} USD at {RISK:.0f}")
    r1 = out["R1"][2]
    if len(r1):
        w, l_ = r1.net[r1.net > 0].sum(), -r1.net[r1.net < 0].sum(); pf = w / l_ if l_ else float("inf"); acc = bool(len(r1) >= 100 and r1.net.sum() > 0 and pf >= 1.15)
        print(f"\nREGISTERED CHECK (R1: >= 100 trades, net > 0, PF >= 1.15): trades {len(r1)}, net {r1.net.sum():+,.0f}, PF {pf:.2f} -> {'PASS' if acc else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
