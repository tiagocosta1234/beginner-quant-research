"""Patch the SAVED charts of the MT5 broker terminal on THIS PC to the x2.0 test settings (2026-10-14, the trader: x2.0 plan, forex/PLAN_WEEKEND_X2_L2000.md).
Run it ONLY while the MT5 broker terminal is closed (python -m forex.handover stop closes it):   python -m forex.tools.apply_x2_charts
ManualSDB chart:   InpLots -> 0.24, InpGuardDayPct -> 2.0        XAUUSD 5 minute chart: Entry_Amount -> 0.08
Finds the charts by the EA name inside each chart*.chr (so the file numbering does not matter), asserts each key exists once, keeps the UTF-16 BOM, backs the files up first (folder chart_backup_<time> next to the charts' parent), idempotent."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

D = Path(os.environ["APPDATA"]) / "MetaQuotes" / "Terminal" / "A2DE5F95DF1B92F855BD63606EC1CA5B" / "MQL5" / "Profiles" / "Charts" / "Default"
PLAN = {"manualsdb": {"InpLots": "0.24", "InpGuardDayPct": "2.0"}, "xauusd5minute": {"Entry_Amount": "0.08"}}


def terminal_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq terminal64.exe"], capture_output=True, text=True).stdout.lower()
    return "terminal64.exe" in out


def ea_name(t: str) -> str | None:
    m = re.search(r"<expert>\s*\r?\nname=([^\r\n]+)", t)
    return m.group(1).lower().replace(" ", "") if m else None


def main() -> int:
    if not D.exists(): print(f"charts folder not found: {D}"); return 1
    if terminal_running(): print("A terminal64.exe is RUNNING: close the MT5 broker terminal first (python -m forex.handover stop). Nothing changed."); return 1
    files = {}
    for f in sorted(D.glob("chart*.chr")):
        raw = f.read_bytes(); t = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", errors="ignore"); n = ea_name(t)
        if n in PLAN: files[n] = (f, raw[:2] == b"\xff\xfe", t)
    missing = [k for k in PLAN if k not in files]
    if missing: print("no saved chart found for:", missing, "(open the EA's chart once, close the terminal, run again). Nothing changed."); return 1
    bk = D.parent.parent.parent / f"chart_backup_{time.strftime('%Y%m%d_%H%M%S')}"; bk.mkdir(); [shutil.copy2(f, bk / f.name) for f, _, _ in files.values()]
    for n, (f, bom, t) in files.items():
        for k, new in PLAN[n].items():
            cur = re.findall(rf"^{k}=(\S+?)\r?$", t, re.M); assert len(cur) == 1, f"{f.name}: {k} found {len(cur)} times, expected once"
            if cur[0] == new: print(f"{f.name} ({n}): {k} already {new}"); continue
            t = re.sub(rf"^{k}={re.escape(cur[0])}(\r?)$", lambda m: f"{k}={new}{m.group(1)}", t, flags=re.M); print(f"{f.name} ({n}): {k} {cur[0]} -> {new}")
        f.write_bytes((b"\xff\xfe" if bom else b"") + t.encode("utf-16-le"))
    print(f"backup: {bk}\nNext: python -m forex.handover check  (must say READY), then python -m forex.handover start --yes and arm the Algo Trading")
    return 0


if __name__ == "__main__":
    sys.exit(main())
