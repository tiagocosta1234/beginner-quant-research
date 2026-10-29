"""
MT5 server clock -> New York time.

Established from data, not assumed (2026-10-01): US100.cash M1 bars (server wall-clock
seconds) against Databento NQ (UTC), Jun-Sep 2026: the 1-minute changes correlate +0.927 at
server = UTC+3 and <= 0.04 at every other hour or +-1/2 minute shift; the tick-volume jump sits
on the 16:30 server bar = 09:30 ET. That is the common "New York close = 00:00 server"
convention: server = New York wall clock + 7 hours all year (UTC+3 in US summer time, UTC+2 in
US winter time). The winter half is verified by `verify_offset` on the full history before any
backtest result is used (forex/specs/US100.cash_clock_check.json).
"""
from __future__ import annotations

import pandas as pd

SERVER_MINUS_NY = pd.Timedelta(hours=7)


def server_to_ny(server_seconds) -> pd.DatetimeIndex:
    """MT5 bar/tick `time` (server wall-clock seconds) -> naive New York wall-clock timestamps."""
    return pd.DatetimeIndex(pd.to_datetime(server_seconds, unit="s")) - SERVER_MINUS_NY


def ny_to_server_seconds(ny: pd.Timestamp) -> int:
    return int((pd.Timestamp(ny) + SERVER_MINUS_NY).timestamp())


def verify_offset(cfd: pd.DataFrame, reference_utc: pd.Series, months=None) -> pd.DataFrame:
    """Per calendar month: the whole-hour server->UTC offset (0..5) maximizing the correlation of 1-min
    close changes between the CFD (`time`, `close`) and a UTC-stamped reference close series, and
    whether it equals the NY+7 rule. Returns one row per month."""
    s = pd.Series(cfd["close"].values, index=pd.to_datetime(cfd["time"], unit="s"))
    ref = reference_utc.diff()
    rows = []
    for m, g in s.groupby(s.index.to_period("M")):
        if months is not None and str(m) not in months:
            continue
        best = None
        for h in range(0, 6):
            x = g.copy()
            x.index = x.index - pd.Timedelta(hours=h)
            j = pd.concat([x.diff(), ref], axis=1, join="inner").dropna()
            if len(j) < 1000:
                continue
            c = float(j.corr().iloc[0, 1])
            if best is None or c > best[1]:
                best = (h, c, len(j))
        if best is None:
            continue
        mid = pd.Timestamp(str(m)) + pd.Timedelta(days=14, hours=12)
        rule = int(mid.tz_localize("America/New_York").utcoffset().total_seconds() // 3600) + 7   # -4+7=3, -5+7=2
        rows.append(dict(month=str(m), best_offset=best[0], corr=round(best[1], 3), bars=best[2], rule_offset=rule,
                         agrees=best[0] == rule))
    return pd.DataFrame(rows)
