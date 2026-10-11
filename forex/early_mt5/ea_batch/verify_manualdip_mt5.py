"""ManualDip.mq5 (DA2 index dip EA) in the MT5 Strategy Tester on MT5 broker real ticks (portable tester terminal), 2025-10-01..2026-09-30,
compared trade by trade with the Python simulation of the same rule (forex/early_mt5/ea_research/dip_addon.py, Z 1.5, risk 500).
   python -m mt5broker.ea_batch.verify_manualdip_mt5"""
from __future__ import annotations

import glob
import os
import re
from pathlib import Path

import pandas as pd

from mt5broker.ea_batch import mt5data_run as ER

TR, TERM = ER.TR, ER.TERM_DIR


def ea_log() -> list[str]:
    files = sorted(glob.glob(str(TERM / "Tester" / "Agent-*" / "logs" / "*.log")), key=os.path.getmtime)
    if not files: return []
    raw = Path(files[-1]).read_bytes(); txt = raw.decode("utf-16", errors="ignore") if raw[:2] == b"\xff\xfe" else raw.decode("utf-8", errors="ignore")
    return [l for l in txt.splitlines() if "[ManualDip]" in l]


def main() -> int:
    r = TR.run_test("manualdip", r"the trader\ManualDip.ex5", "NSDQ+", "M1", "2025.10.01", "2026.09.30", None, timeout=7200)
    print(f"tester: net {r['net']:,.2f} | note {r['note']!r} | seconds {r['seconds']} | eq DD {r['eq_dd']}")
    L = ea_log(); buys = [l for l in L if "] BUY " in l]; exits = [l for l in L if "] EXIT " in l]
    print(f"log lines {len(L)} | buys {len(buys)} | exits {len(exits)}")
    for l in buys + exits: print("  ", l[l.index("[ManualDip]"):][:170] if "[ManualDip]" in l else l[:170], " @", l[:40])
    nodata = [l for l in L if "no signal data" in l]; print(f"days without signal data: {len(nodata)}", nodata[:3])
    os.environ["DA_Z"] = "1.5"
    from mt5broker.ea_research import dip_addon as DA
    DA.RISK = 500.0; T, bars = DA.trades(); T, D = DA.day_arrays(T, bars)
    T = T[(T.date >= "2025-10-01") & (T.date <= "2026-09-30")]
    print("\nPython simulation, same window:"); print(T[["date", "mkt", "e", "sd", "n", "q", "pl", "stopped"]].round(4).to_string(index=False)); print("sim total", round(T.pl.sum(), 2))
    if r["deals"] is not None: d = r["deals"]; o = d[d.direction.astype(str).str.lower().str.startswith("out")]; print("tester closed trades", len(o), "net", round(float((o.profit + o.commission + o.swap).sum()), 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
