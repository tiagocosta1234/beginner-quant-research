"""
DailyHistory: a year-plus of daily regular-session (09:30-16:00 ET) history for
strategies whose features need more than the broker's 1-minute feed holds.

Why (2026-09-30): the broker's live 1-minute window is ~27,500 bars (~22 sessions).
Round 244's POC filter needs a 20-session range average and a 250-session median
of 20-day realized volatility, and the Combined bot's meta-model needs >20 POC
trades of history. This module starts from a bundled seed file
(live_bot/data/nq_daily_rth_seed.csv, built by
futures/engine/build_daily_rth_seed.py from Databento NQ -- the same
sessions Round 244 was computed on) and merges every COMPLETED session it sees in
the live bars, saving them to a state file so the history keeps growing after the
seed ends and survives restarts.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DEFAULT_SEED = HERE / "data" / "nq_daily_rth_seed.csv"
DEFAULT_STATE = HERE / "state" / "daily_rth_history.csv"
RTH_START, RTH_END = dt.time(9, 30), dt.time(16, 0)
OPEN_BY = dt.time(9, 31)       # the feed covers the session from its open...
CLOSE_FROM = dt.time(12, 59)   # ...to at least 12:59, the last bar of a 13:00 ET early close


def completed_sessions(rth_ny: pd.DataFrame, today: dt.date):
    """(date, bars) for every session before `today` that the feed covers from its open
    to its close. Shared by both history caches and live_bot/update_history.py.

    Replaces the old rule "a bar at/after 15:55 exists" (2026-09-30), which dropped
    early-close sessions for good (the Friday after Thanksgiving and Christmas Eve end
    at 13:00 ET; the Databento seeds and the backtests include them, and the next day
    then read the wrong previous session), and let in the first session of a feed
    window that starts mid-session (the broker's 1-minute history can: its MNQ pull
    of 2026-09-27 began at 11:46). A regular session whose feed stops between 13:00
    and 15:55 is kept as-is; that takes a broker data outage."""
    if rth_ny is None or rth_ny.empty:
        return
    for d, g in rth_ny.groupby(rth_ny.index.date):
        if d < today and g.index[0].time() <= OPEN_BY and g.index[-1].time() >= CLOSE_FROM:
            yield d, g


class DailyHistory:
    def __init__(self, seed_path: str | os.PathLike | None = None, state_path: str | os.PathLike | None = None) -> None:
        self.seed_path = Path(seed_path or os.getenv("BRACKET_DAILY_SEED", DEFAULT_SEED))
        self.state_path = Path(state_path or os.getenv("BRACKET_DAILY_HISTORY", DEFAULT_STATE))
        frames = []
        for p in (self.seed_path, self.state_path):
            if p.exists():
                frames.append(pd.read_csv(p, dtype={"date": str}))
        if frames:
            df = pd.concat(frames).drop_duplicates("date", keep="last")
        else:
            df = pd.DataFrame(columns=["date", "open", "high", "low", "close"])
        df["date"] = pd.to_datetime(df["date"]).dt.date
        self.df = df.sort_values("date").reset_index(drop=True)

    def merge_live(self, rth_ny: pd.DataFrame, today: dt.date) -> int:
        """rth_ny: live 1-min RTH bars indexed by naive New York time. Adds/updates every
        completed session before `today`; saves when anything changed. Returns rows changed."""
        if rth_ny is None or rth_ny.empty:
            return 0
        known = {r.date: r for r in self.df.itertuples(index=False)}
        new_rows, changed = [], 0
        for d, g in completed_sessions(rth_ny, today):
            row = dict(date=d, open=float(g["open"].iloc[0]), high=float(g["high"].max()),
                       low=float(g["low"].min()), close=float(g["close"].iloc[-1]))
            old = known.get(d)
            if old is None or any(abs(getattr(old, k) - row[k]) > 1e-9 for k in ("open", "high", "low", "close")):
                new_rows.append(row)
                changed += 1
        if changed:
            add = pd.DataFrame(new_rows)
            self.df = (pd.concat([self.df[~self.df["date"].isin(add["date"])], add])
                       .sort_values("date").reset_index(drop=True))
            self.save_state()
        return changed

    def save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        out = self.df.copy()
        out["date"] = out["date"].map(lambda d: d.isoformat())
        out.to_csv(self.state_path, index=False)

    def before(self, today: dt.date) -> pd.DataFrame:
        return self.df[self.df["date"] < today].reset_index(drop=True)


def poc_filter_features(hist: pd.DataFrame) -> dict | None:
    """Round 244's lead, computed exactly as round244_confluence_mix.daily_context does
    for the trade day that follows the last row of `hist` (sessions strictly before
    today, oldest first). Returns None if there is not enough history."""
    if len(hist) < 21:
        return None
    rng = (hist["high"] - hist["low"]).to_numpy(float)
    closes = hist["close"].to_numpy(float)
    prev_range = float(rng[-1])
    rng_sma20 = float(rng[-20:].mean())
    rets = pd.Series(np.diff(np.log(closes)))
    rv = rets.rolling(20).std().to_numpy()          # value j = rv20 for the day after close j+1
    rv_valid = rv[~np.isnan(rv)]
    if len(rv_valid) < 120:
        return None
    rv20 = float(rv[-1])
    med250 = float(np.median(rv_valid[-250:]))
    narrow = prev_range < rng_sma20
    lowvol = rv20 < med250
    return dict(prev_range=prev_range, rng_sma20=rng_sma20, rv20=rv20, rv20_med250=med250,
                narrow=bool(narrow), lowvol=bool(lowvol), passed=bool(narrow and not lowvol),
                history_days=int(len(hist)), last_session=str(hist["date"].iloc[-1]))
