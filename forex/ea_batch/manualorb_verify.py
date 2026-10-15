"""Verify ManualORB (USDJPY London preset) in the MT5 Strategy Tester on MT5 broker real ticks and compare it with the Python tick replay.
NOT RUN YET: the portable tester terminal (D:\\finance\\mt5_mt5_tester) holds the LIVE account's saved login, so a run opens a second session
on account <acct> (Algo Trading off, AllowLiveTrading=0). Run it only with the trader's OK, never while he trades by hand, and check afterwards
that no terminal64.exe from the tester path is left running.
   python -m forex.ea_batch.manualorb_verify            writes the historical news file, runs Oct 2025 - Sep 2026, prints the comparison
Steps: 1. ManualNewsHist.csv (CPI / NFP / FOMC 2025-2026 on the server clock) into the COMMON Files folder (a new file; ManualNews.csv untouched);
2. run_test on USDJPY+ M1, Model 4, preset inputs with InpNewsFile=ManualNewsHist.csv, and once with InpNewsFlat=false;
3. per-day comparison with forex/ea_research/usdjpy_ticks.py (news flat off) to check fills, OCO, the market entry when price is already
   through the box at 08:30, sizing (150 USD at the stop) and the 17:00 exit."""
import os
from pathlib import Path

import pandas as pd

from forex.ea_research.event_macro import server_s

TESTER = r"D:\finance\mt5_mt5_tester\terminal64.exe"          # the portable tester copy, never a live terminal
os.environ["MT5BROKER_MT5_TERMINAL"] = TESTER                         # run_batch / tester_run read it at import (as mt5data_run does)
COMMON = Path(os.environ["APPDATA"]) / "MetaQuotes" / "Terminal" / "Common" / "Files"
INPUTS = {"InpSession": "0", "InpOpenHHMM": "800", "InpBoxMin": "30", "InpValidMin": "150", "InpExitHHMM": "1700", "InpStopMode": "0",
          "InpStopMinPct": "0", "InpStopMaxPct": "100", "InpSkipBoxPct": "0", "InpMinBoxSpreads": "2", "InpTPmult": "0", "InpTrendOnly": "false",
          "InpRiskUSD": "150", "InpDayStopUSD": "2000", "InpDayTargetUSD": "2000", "InpMagic": "261016", "InpVerbose": "true",
          "InpNewsFile": "ManualNewsHist.csv", "InpNewsBeforeMin": "5", "InpNewsAfterMin": "5"}


def news_file():
    cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv")
    cal = cal[(cal.date >= "2025-09-01") & (cal.date <= "2026-12-31")]
    lines = ["# ManualNewsHist.csv: CPI / NFP / FOMC on the MT5 SERVER clock, for tester runs (forex/ea_batch/manualorb_verify.py)"]
    for r in cal.itertuples():
        s = server_s(r.date, 14, 0) if r.kind == "FOMC" else server_s(r.date, 8, 30)
        lines.append(pd.Timestamp(s, unit="s").strftime("%Y.%m.%d %H:%M") + f",{r.kind}")
    (COMMON / "ManualNewsHist.csv").write_text("\n".join(lines) + "\n", encoding="ascii")
    return len(lines) - 1


def main():
    from forex.ea_batch.tester_run import run_test
    print("news releases written:", news_file())
    out = {}
    for tag, flat in (("news", "true"), ("nonews", "false")):
        inp = dict(INPUTS, InpNewsFlat=flat)
        out[tag] = run_test(f"manualorb_usdjpy_{tag}", r"ManualORB.ex5", "USDJPY+", "M1", "2025.10.01", "2026.09.30", inp)
        print(tag, "net", out[tag]["net"], "| deals", len(out[tag]["deals"]), "|", out[tag].get("note", ""))
    tick = pd.read_parquet("D:/finance/si_ledgers/USDJPY_TICKS.parquet")
    print("python tick replay (news flat off):", len(tick), "trades,", round(tick.R.sum() * 150, 0), "USD at 150 USD a trade")


if __name__ == "__main__":
    main()
