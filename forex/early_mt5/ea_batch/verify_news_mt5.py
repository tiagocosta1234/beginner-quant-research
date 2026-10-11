"""Test of the 2026-10-11 NEWS FLAT rule of AccountGuard in the MT5 Strategy Tester on MT5 broker's real ticks (portable MT5 broker tester terminal, never a live terminal).
   python -m mt5broker.ea_batch.verify_news_mt5
GuardSelfTest.mq5 = the real guard code + a driver that opens 0.1 lot of XAUUSD+ every 45 minutes (1 lot hit the emergency floor in the first days and left nothing to test) (random side, closed after 40 minutes).
A synthetic release file ManualNews_test.csv (common Files folder; the live file is ManualNews.csv and is NOT touched) lists every weekday of the
test month at 15:30 and 21:00 server time. Window = 120 s before to 300 s after.
Run A (rule ON): no one-minute snapshot inside a window [T-115 s, T+300 s] may show an open position, and the guard must have closed positions
(NEWSFLAT events) at most of the windows. Run B (rule OFF, control): the same driver must show positions open inside the windows.
Then the no-hedge regression (verify_nohedge_mt5) is run on the same build."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from mt5broker.ea_batch import mt5data_run as ER
from mt5broker.ea_batch import verify_nohedge_mt5 as NH

TR = ER.TR
COMMON = Path(os.environ["APPDATA"]) / "MetaQuotes" / "Terminal" / "Common" / "Files"
DAYS = pd.bdate_range("2026-03-02", "2026-03-27")
TIMES = sorted(pd.Timestamp(f"{d.date()} {hm}") for d in DAYS for hm in ("15:30", "21:00"))


def write_file() -> None:
    COMMON.mkdir(parents=True, exist_ok=True)
    (COMMON / "ManualNews_test.csv").write_text("# test file for verify_news_mt5\r\n" + "".join(f"{t:%Y.%m.%d %H:%M},TEST\r\n" for t in TIMES), encoding="ascii")


def run(tag: str, news: bool, name: str) -> pd.DataFrame:
    inputs = {"InpGuardOn": "true", "InpDriverLots": "0.1", "InpEveryMin": "45", "InpHoldMin": "40", "InpStubborn": "false", "InpDirMode": "0", "InpInitial": "100000", "InpDailyStopPct": "4.0",
              "InpFloorStopPct": "9.0", "InpTargetPct": "0.0", "InpShiftSec": "0", "InpNoHedge": "false", "InpOppositeDriver": "false", "InpNews": "true" if news else "false", "InpNewsFile": "ManualNews_test.csv", "InpLogName": name}
    r = TR.run_test(tag, r"the trader\GuardSelfTest.ex5", "XAUUSD+", "M1", "2026.03.02", "2026.03.27", inputs, timeout=7200)
    l = NH.read_log(name); print(f"{tag}: net {r['net']:,.0f}, log rows {len(l)}, events {l.event.value_counts().to_dict() if len(l) else {}}", flush=True)
    return l


def inside(l: pd.DataFrame) -> pd.DataFrame:
    s = l[l.event == "SNAP"].copy(); s["n"] = s.detail.str.extract(r"b=(\d+) s=(\d+)").astype(float).sum(axis=1)
    win = pd.Series(False, index=s.index)
    for T in TIMES: win |= (s.time >= T - pd.Timedelta(seconds=115)) & (s.time <= T + pd.Timedelta(seconds=300))
    return s[win]


def main() -> int:
    write_file(); NH.compile_sources(); ok = True
    a = run("news_A", True, "news_A.csv"); b = run("news_B", False, "news_B.csv")
    ia, ib = inside(a), inside(b); na = int(a.detail.str.extract(r"closed=(\d+)")[0].astype(float).sum()) if (a.event == "NEWSFLAT").any() else 0
    c1 = len(ia) > 100 and int((ia.n > 0).sum()) == 0 and na >= 0.5 * len(TIMES)
    print(f"A (rule ON): {len(TIMES)} windows, snapshots inside windows {len(ia)}, with a position open {int((ia.n > 0).sum())}, positions closed by the news rule {na} -> {'PASS' if c1 else 'FAIL'}", flush=True); ok &= c1
    c2 = len(ib) > 100 and int((ib.n > 0).sum()) > 0 and not (b.event == "NEWSFLAT").any()
    print(f"B (rule OFF, control): snapshots inside windows with a position open {int((ib.n > 0).sum())} of {len(ib)}, NEWSFLAT events {int((b.event == 'NEWSFLAT').sum())} -> {'PASS (the test can see positions in the windows)' if c2 else 'FAIL'}", flush=True); ok &= c2
    print("news checks:", "ALL PASS" if ok else "SOME FAILED", flush=True)
    print("--- regression: no-hedge rule on the same build ---", flush=True)
    ok &= NH.main() == 0
    print("ALL CHECKS PASS" if ok else "SOME CHECK FAILED", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
