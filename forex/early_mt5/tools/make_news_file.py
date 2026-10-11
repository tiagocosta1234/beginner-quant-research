r"""Write ManualNews.csv for the guard's NEWS FLAT rule (AccountGuard.mqh, 2026-10-11): one release per line, MT5 SERVER clock
(Europe/Athens wall time), "YYYY.MM.DD HH:MM,label". Copy the output to %APPDATA%\MetaQuotes\Terminal\Common\Files on EACH PC.
Sources (checked 2026-10-11): BLS CPI and Employment Situation schedules, Federal Reserve FOMC calendar (2027 dates tentative);
September 2026 CPI (Oct 14) from secondary calendars that agree. Update the list when BLS publishes the 2027 schedule.
   python forex/early_mt5/tools/make_news_file.py [--out PATH]"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

EVENTS = [  # (kind, New York date, New York time)
    ("CPI", "2026-10-14", "08:30"), ("FOMC", "2026-10-28", "14:00"), ("NFP", "2026-11-06", "08:30"), ("CPI", "2026-11-10", "08:30"),
    ("NFP", "2026-12-04", "08:30"), ("FOMC", "2026-12-09", "14:00"), ("CPI", "2026-12-10", "08:30"), ("NFP", "2027-01-08", "08:30"),
    ("CPI", "2027-01-13", "08:30"), ("FOMC", "2027-01-27", "14:00"), ("NFP", "2027-02-05", "08:30"), ("CPI", "2027-02-11", "08:30"),
    ("NFP", "2027-03-05", "08:30"), ("CPI", "2027-03-10", "08:30"), ("FOMC", "2027-03-17", "14:00"),
]


def server_time(day: str, hm: str) -> pd.Timestamp:
    return pd.Timestamp(f"{day} {hm}").tz_localize("America/New_York").tz_convert("Europe/Athens").tz_localize(None)


def main() -> int:
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path(__file__).resolve().parents[1] / "expert_advisors" / "ManualNews.csv"
    rows = sorted((server_time(d, t), k) for k, d, t in EVENTS)
    lines = ["# ManualNews.csv: release times on the MT5 SERVER clock (Europe/Athens), written by forex/early_mt5/tools/make_news_file.py"] + [f"{t:%Y.%m.%d %H:%M},{k}" for t, k in rows]
    out.write_text("\r\n".join(lines) + "\r\n", encoding="ascii")
    print(f"{len(rows)} releases -> {out}"); [print("  ", l) for l in lines[1:]]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
