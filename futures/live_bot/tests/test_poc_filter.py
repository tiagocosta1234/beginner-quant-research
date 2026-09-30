"""Plain-Python tests for the Round 244 POC filter (daily_history.py and its use in
disciplined_bracket_strategy.py). No pytest dependency.

Run with: python live_bot/tests/test_poc_filter.py

Parity with Round 244's own feature code (1,660/1,660 days on the Databento seed)
was checked separately when this was built; these tests cover the logic, the three
modes, the paper-tracking log and the history cache.
"""

from __future__ import annotations

import datetime as dt
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from live_bot.daily_history import DailyHistory, poc_filter_features  # noqa: E402
from live_bot.disciplined_bracket_strategy import DisciplinedBracketStrategy  # noqa: E402
from live_bot.strategy_interface import SignalAction  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []
TMP = Path(tempfile.mkdtemp())


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, condition, detail))


def hist(n: int, last_range: float, vol: float, seed: int = 0) -> pd.DataFrame:
    """n sessions; last session's range fixed; recent 20 closes' volatility scaled by `vol`."""
    rng = np.random.default_rng(seed)
    dates = [d.date() for d in pd.bdate_range("2025-01-01", periods=n)]
    rets = rng.normal(0, 0.01, n)
    rets[-21:] *= vol
    close = 20_000 * np.exp(np.cumsum(rets))
    ranges = np.full(n, 200.0)
    ranges[-1] = last_range
    return pd.DataFrame(dict(date=dates, open=close, high=close + ranges / 2, low=close - ranges / 2, close=close))


def seed_file(df: pd.DataFrame) -> Path:
    p = TMP / f"seed_{np.random.randint(1e9)}.csv"
    out = df.copy()
    out["date"] = out["date"].map(lambda d: d.isoformat())
    out.to_csv(p, index=False)
    return p


def session(day: dt.date, open_px: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(f"{day} 09:30", f"{day} 15:59", freq="1min")
    close = open_px + np.round(rng.normal(0, 4, len(idx))) * 0.25
    return pd.DataFrame({"open": close, "high": close + 0.5, "low": close - 0.5, "close": close,
                         "volume": rng.integers(50, 150, len(idx)).astype(float)}, index=idx)


def poc_market(today: dt.date) -> pl.DataFrame:
    """12 prior sessions near 20,000 (enough range history for the POC leg) and a
    today that opens well below yesterday's POC -> a POC-reversion LONG."""
    prior = [d.date() for d in pd.bdate_range(end=today - dt.timedelta(days=1), periods=12)]
    parts = [session(d, 20_000.0, i) for i, d in enumerate(prior)]
    # yesterday is a WIDE day (one 500-point spike bar; closes unchanged, so its POC is
    # unchanged): these live sessions merge into the daily history, and a wide
    # yesterday makes the filter's "narrow prior day" condition fail.
    last = parts[-1]
    last.iloc[100, last.columns.get_loc("high")] += 250.0
    last.iloc[100, last.columns.get_loc("low")] -= 250.0
    idx = pd.date_range(f"{today} 09:30", f"{today} 09:32", freq="1min")
    parts.append(pd.DataFrame({"open": 19_900.0, "high": 19_900.5, "low": 19_899.5, "close": 19_900.0, "volume": 100.0}, index=idx))
    df = pd.concat(parts)
    df.index = df.index.tz_localize("America/New_York").tz_convert("America/Chicago")
    df.index.name = "timestamp"
    return pl.from_pandas(df.reset_index())


def main() -> int:
    # --- feature logic
    f = poc_filter_features(hist(400, last_range=100.0, vol=2.0))
    check("narrow day + high vol -> PASS", f is not None and f["narrow"] and not f["lowvol"] and f["passed"], str(f))
    f = poc_filter_features(hist(400, last_range=300.0, vol=2.0))
    check("wide prior day -> FAIL", f is not None and not f["narrow"] and not f["passed"], str(f))
    f = poc_filter_features(hist(400, last_range=100.0, vol=0.3))
    check("low-vol regime -> FAIL", f is not None and f["lowvol"] and not f["passed"], str(f))
    check("too little history -> None", poc_filter_features(hist(100, 100.0, 2.0)) is None)

    # --- history cache: merges completed live sessions, skips today/incomplete, persists
    base = hist(400, 100.0, 2.0)
    seed = seed_file(base)
    state = TMP / "state.csv"
    h = DailyHistory(seed, state)
    last = base["date"].iloc[-1]
    d1 = (pd.Timestamp(last) + pd.offsets.BDay(1)).date()
    d2 = (pd.Timestamp(last) + pd.offsets.BDay(2)).date()
    live = pd.concat([session(d1, 21_000.0, 1), session(d2, 21_000.0, 2).iloc[:60]])
    n = h.merge_live(live, today=d2 + dt.timedelta(days=1))
    check("completed live session merged, incomplete one skipped", n == 1 and h.df["date"].iloc[-1] == d1, f"n={n}")
    h2 = DailyHistory(seed, state)
    check("merged session persisted across a restart", h2.df["date"].iloc[-1] == d1)

    # --- strategy modes, on a market whose POC signal fires; history makes the filter FAIL
    today = dt.date(2026, 10, 1)
    fail_seed = seed_file(hist(400, last_range=300.0, vol=2.0).assign(
        date=[d.date() for d in pd.bdate_range(end=today - dt.timedelta(days=20), periods=400)]))
    for mode, want_action in (("off", SignalAction.ENTER_LONG), ("log", SignalAction.ENTER_LONG), ("on", SignalAction.HOLD)):
        logp = TMP / f"paper_{mode}.csv"
        s = DisciplinedBracketStrategy(disable_va=True, poc_filter=mode, filter_log_path=logp)
        import os
        os.environ["BRACKET_DAILY_SEED"], os.environ["BRACKET_DAILY_HISTORY"] = str(fail_seed), str(TMP / f"hist_{mode}.csv")
        sig = s.on_bar(poc_market(today))
        check(f"mode {mode}: action {want_action.name}", sig.action == want_action, f"{sig.action} {sig.reason}")
        if mode == "off":
            check("mode off: no filter note, no paper log", "filter[" not in (sig.reason or "") and not logp.exists())
        else:
            rows = pd.read_csv(logp)
            check(f"mode {mode}: one paper-log row with verdict FAIL", len(rows) == 1 and rows["verdict"].iloc[0] == "FAIL",
                  rows.to_dict("records").__repr__()[:200])
            check(f"mode {mode}: logged action", rows["acted"].iloc[0] == ("skipped" if mode == "on" else "traded"))
    check("invalid mode is rejected", _raises(lambda: DisciplinedBracketStrategy(poc_filter="maybe")))

    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail[:200]}]" if not ok else ""))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


def _raises(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


if __name__ == "__main__":
    sys.exit(main())
