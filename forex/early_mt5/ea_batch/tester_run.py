"""Run one EA in the MetaTrader 5 Strategy Tester with CUSTOM INPUTS, the way run_batch.py does (real ticks, $100K, hidden desktop, the same report parser). Used to verify the pair's scaled lots and the guard.

  from mt5broker.ea_batch.tester_run import run_test
  r = run_test("stoch_031_2026", r"ea_batch\\77900\\StochDailyBreakout.ex5", "XAUUSD", "H1", "2026.01.01", "2026.09.30", {"InpLots": "0.31"})
  r -> dict(deals=DataFrame, net, eq_dd, bal_dd, note)

The terminal is shared with the EA batch: STOP THE BATCH FIRST (it restarts / kills terminal64 for every run). Read-only for accounts: AllowLiveTrading=0, AllowDllImport=0.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pandas as pd

from mt5broker.ea_batch import run_batch as RB


def run_test(name: str, expert_rel: str, symbol: str, period: str, frm: str, to: str, inputs: dict | None = None, timeout: int = 3600, deposit: int = 100000, leverage: int = 100, execution_mode: int = 0) -> dict:
    data = RB.data_folder(); rep_root = data / "ea_batch_reports"; rep_root.mkdir(exist_ok=True)
    ini = Path(r"D:\finance\tmp") / f"{name}.ini"; ini.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[Experts]", "AllowLiveTrading=0", "AllowDllImport=0", "Enabled=1", "[Tester]", f"Expert={expert_rel}", f"Symbol={symbol}", f"Period={period}", "Model=4", "Optimization=0", f"FromDate={frm}", f"ToDate={to}",
             "ForwardMode=0", f"Deposit={deposit}", "Currency=USD", f"Leverage={leverage}", f"ExecutionMode={execution_mode}", "Visual=0", f"Report=ea_batch_reports\\{name}", "ReplaceReport=1", "ShutdownTerminal=1"]
    if inputs:
        lines += ["[TesterInputs]"] + [f"{k}={v}" for k, v in inputs.items()]
    ini.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for old in rep_root.glob(f"{name}.*"):
        old.unlink()
    RB.kill_terminal(); RB.wait_for_disk(data)
    t0 = time.time(); p = RB.start_terminal(ini); note = ""
    while True:
        try:
            p.wait(timeout=5); break
        except subprocess.TimeoutExpired:
            if time.time() - t0 > timeout:
                RB.kill_terminal(); note = f"timeout {timeout}s"; break
    htm = next(iter(rep_root.glob(f"{name}*.htm*")), None)
    out = dict(deals=None, net=float("nan"), eq_dd=float("nan"), bal_dd=float("nan"), note=note, seconds=round(time.time() - t0), report=htm)
    if htm is not None:
        d = RB.parse_report(htm)
        out.update(deals=d, net=float((d.profit + d.commission + d.swap).sum()))
        out["eq_dd"], out["bal_dd"] = RB.parse_drawdowns(htm)
    elif not note:
        out["note"] = "no report"
    return out
