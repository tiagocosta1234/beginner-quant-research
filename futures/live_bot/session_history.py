"""
SessionHistory: per-session history for the Combined bot's meta-model features.

Why (2026-09-30): CombinedStrategy needs the win rate of the last 20
reconstructed POC-reversion trades (trail_winrate), a 20-session range average and
the range 20 sessions before yesterday (range_chg). The broker's live 1-minute
window (~22 sessions) reconstructs only 3-9 such trades, so the bot held every day.

Each row is one completed regular session (09:30-16:00 ET): its open, range, POC,
VAL, VAH and the outcome of that day's POC-reversion trade (1 win, 0 loss, blank if
no trade), computed with the strategy's OWN functions (_session_profile,
_resolve_day_outcome) and the same causal rules it uses when it rebuilds them from
bars -- so this history is exactly what the bot would compute if the feed went back
far enough. Seeded from Databento NQ (the data the meta-model was trained on) by
futures/engine/build_session_seed.py; completed live sessions newer than
the history are appended and persisted to a state file.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd

from live_bot.daily_history import completed_sessions

HERE = Path(__file__).resolve().parent
DEFAULT_SEED = HERE / "data" / "nq_session_seed.csv"
DEFAULT_STATE = HERE / "state" / "combined_session_history.csv"
COLUMNS = ["date", "open", "range", "poc", "val", "vah", "poc_outcome"]
RANGE_WINDOW, RANGE_MIN_PERIODS, STOP_MULT = 20, 10, 0.15


def session_row(day_df: pd.DataFrame, hist: pd.DataFrame) -> dict | None:
    """Profile + POC-trade outcome for one session, given the sessions before it
    (oldest first, columns as COLUMNS). Mirrors CombinedStrategy's own loop."""
    from live_bot.combined_strategy import _resolve_day_outcome, _session_profile
    prof = _session_profile(day_df)
    if prof is None:
        return None
    rng, poc, val, vah = prof
    open_px = float(day_df["open"].iloc[0])
    outcome = np.nan
    ranges = hist["range"].to_numpy(float)[-RANGE_WINDOW:]
    if len(hist) >= 1 and len(ranges) >= RANGE_MIN_PERIODS:
        S_hist = float(np.mean(ranges))
        prev_poc = float(hist["poc"].iloc[-1])
        dist = prev_poc - open_px
        if S_hist > 0 and abs(dist) >= STOP_MULT * S_hist:
            direction = 1 if dist > 0 else -1
            sl = open_px - direction * STOP_MULT * S_hist
            outcome = 1.0 if _resolve_day_outcome(day_df, direction, open_px, sl, prev_poc) > 0 else 0.0
    return dict(date=day_df.index[0].date(), open=open_px, range=rng, poc=poc, val=val, vah=vah, poc_outcome=outcome)


class SessionHistory:
    def __init__(self, seed_path: str | os.PathLike | None = None, state_path: str | os.PathLike | None = None,
                 logger: logging.Logger | None = None) -> None:
        self.seed_path = Path(seed_path or os.getenv("COMBINED_SESSION_SEED", DEFAULT_SEED))
        self.state_path = Path(state_path or os.getenv("COMBINED_SESSION_HISTORY", DEFAULT_STATE))
        self.log = logger or logging.getLogger("SessionHistory")
        frames = [pd.read_csv(p, dtype={"date": str}) for p in (self.seed_path, self.state_path) if p.exists()]
        df = pd.concat(frames).drop_duplicates("date", keep="first") if frames else pd.DataFrame(columns=COLUMNS)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        self.df = df[COLUMNS].sort_values("date").reset_index(drop=True)

    @property
    def available(self) -> bool:
        return len(self.df) > 0

    def update_from_bars(self, rth_ny: pd.DataFrame, today: dt.date) -> int:
        """Append completed live sessions dated after the last known session. Sessions
        already known (seed or state) are left as they are. "Completed" is the shared
        rule in daily_history.completed_sessions (early closes count, a session the feed
        window cuts off at the start does not)."""
        if rth_ny is None or rth_ny.empty:
            return 0
        last = self.df["date"].iloc[-1] if len(self.df) else dt.date.min
        added = 0
        for d, g in completed_sessions(rth_ny, today):
            if d <= last:
                continue
            row = session_row(g, self.df)
            if row is None:
                continue
            gap = len(pd.bdate_range(last, d)) - 2 if last != dt.date.min else 0
            if gap > 3:
                self.log.warning("SessionHistory: ~%d business days missing between %s and %s", gap, last, d)
            self.df = pd.concat([self.df, pd.DataFrame([row])], ignore_index=True)
            last = d
            added += 1
        if added:
            self.save_state()
        return added

    def save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        out = self.df.copy()
        out["date"] = out["date"].map(lambda d: d.isoformat())
        out.to_csv(self.state_path, index=False)

    def before(self, today: dt.date) -> pd.DataFrame:
        return self.df[self.df["date"] < today].reset_index(drop=True)
