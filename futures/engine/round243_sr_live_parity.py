"""
Round 243 (2026-09-30), verification: does the LIVE S/R bounce bot
(live_bot/support_resistance_bounce_strategy.py) trade what the backtest behind
Rounds 234/236/241 traded? Plan step 3, before any money depends on it.

PART A -- signal parity. Real MGC 1-minute bars (MGC_CONTINUOUS.txt) are fed to the
live strategy one completed bar at a time, each call getting the most recent 3,000
bars exactly as main.py does (bars_needed = 3000). Its entry signals (time,
direction, stop distance) are matched against round30.build_swing_touch_signals on
the same data (raw touches, before any one-position filter -- the live strategy
consumes levels whether or not a position is open, so raw touches are the right
comparison). Two windows of 12 trading days: early (2024-03) and recent (2026-08).
Reported: matched signals, live-only, backtest-only, stop-distance ratio.

PART B -- the live governor. The backtest S/R series (Round 234, flat by 16:10 ET,
backtest sizing) had no daily risk rules; live_bot applies them to every strategy:
no new entry after 2 losing trades in a row within a day (consecutive_loss_limit,
resets on a win), none after the daily loss limit ($1,000 for a $50K account)
is reached on realized P&L. Replayed on Round 234's own trade sequence, per trading
day, in order. Then Round 241's one-month pass rate is recomputed with and without
these rules (same fresh-start, 21-day, intraday-free close-only eval; S/R at $217).
Sizing note (not simulated, stated): live sizes contracts on the TRAIL distance
(1.5x the stop), the backtest on the initial stop while placing the stop at 1.5x --
so live needs BRACKET-equivalent risk ~1.5x the backtest figure ($325 for the $217
backtest) to trade the same number of contracts.
"""
import os, sys, json, datetime as dt, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import numpy as np
import pandas as pd
import polars as pl
from round11_fvg_bias import load_1m, resample_causal
from round19_random_entry import causal_atr15_lookup
from round30_support_resistance import build_swing_touch_signals
from live_bot.support_resistance_bounce_strategy import SupportResistanceBounceStrategy
from live_bot.strategy_interface import SignalAction

WINDOWS = (("early", "2024-03-04", 12), ("recent", "2026-08-10", 12))


def live_signals(df, start_i, end_i):
    strat = SupportResistanceBounceStrategy()
    ts_all = df.index
    base = pl.from_pandas(df.reset_index().rename(columns={"ts": "timestamp", "index": "timestamp"})[
        ["timestamp", "open", "high", "low", "close", "vol"]].rename(columns={"vol": "volume"}))
    out = []
    for i in range(start_i, end_i):
        window = base.slice(max(0, i - 2999), min(3000, i + 1))
        sig = strat.on_bar(window)
        if sig.action in (SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT):
            out.append((ts_all[i], 1 if sig.action == SignalAction.ENTER_LONG else -1, sig.initial_stop_distance_points))
    return pd.DataFrame(out, columns=["ts", "direction", "stop_dist"])


def part_a(df, h15, atr15):
    bt = build_swing_touch_signals(df, h15, atr15, 3, 0.50)
    bt["stop_dist"] = (bt["entry"] - bt["stop"]).abs()
    res = {}
    for label, start, n_days in WINDOWS:
        s_ts = pd.Timestamp(start)
        days = sorted(set(df.index[df.index >= s_ts].normalize()))[:n_days + 1]
        lo_ts, hi_ts = days[0], days[-1]
        i0 = int(df.index.searchsorted(lo_ts)); i1 = int(df.index.searchsorted(hi_ts))
        t0 = time.time()
        lv = live_signals(df, i0, i1)
        b = bt[(bt["ts"] >= df.index[i0]) & (bt["ts"] < df.index[i1])].reset_index(drop=True)
        matched, used = [], set()
        for r in lv.itertuples(index=False):
            cand = b[(b["direction"] == r.direction) & ((b["ts"] - r.ts).abs() <= pd.Timedelta(minutes=1))]
            cand = cand[~cand.index.isin(used)]
            if len(cand):
                j = cand.index[0]; used.add(j)
                matched.append(r.stop_dist / b.loc[j, "stop_dist"])
        res[label] = dict(window=f"{df.index[i0]} .. {df.index[i1]}", live=len(lv), backtest=len(b), matched=len(matched),
                          live_only=len(lv) - len(matched), backtest_only=len(b) - len(used),
                          stop_ratio_median=float(np.median(matched)) if matched else float("nan"),
                          stop_ratio_p5_p95=[float(np.percentile(matched, 5)), float(np.percentile(matched, 95))] if matched else None,
                          seconds=round(time.time() - t0))
        print(f"PART A {label}: {res[label]}", flush=True)
    return res


def part_b():
    import round234_session_bounded_top5 as R234
    import round233_top5_combine_race as R233
    import round236_600eur_goal_2026 as R236
    import round241_one_month_sprint as R241
    R233.SR_RISK = 650.0 / 3.0
    tr, daily_raw = R234.sr_bounded()
    tr = tr.sort_values("entry")
    tday = tr["tday"]
    gov_daily, blocked = {}, 0
    for d, g in tr.groupby(tday, sort=True):
        realized, streak, locked = 0.0, 0, False
        for p in g["pnl"]:
            if locked or streak >= 2 or realized <= -1000.0:
                blocked += 1
                continue
            realized += p
            streak = streak + 1 if p < 0 else 0
        gov_daily[d] = realized
    gov = pd.Series(gov_daily).reindex(daily_raw.index, fill_value=0.0)
    S, common, _ = R236.build_inputs(check_parity=False)
    out = {}
    for label, series in (("backtest (no governor)", daily_raw), ("with live governor rules", gov)):
        v = series.reindex(common, fill_value=0.0).to_numpy(float)
        w = np.minimum(v, 0.0)
        starts_oos = [i for i in range(len(common) - 21) if common[i] >= pd.Timestamp("2025-07-01")]
        starts_all = list(range(len(common) - 21))
        p_oos, _ = R241.p21(v, w, starts_oos)
        p_all, _ = R241.p21(v, w, starts_all)
        out[label] = dict(mean_day=float(v.mean()), trades_per_day=None, p21_oos=p_oos, p21_all=p_all)
        print(f"PART B {label:<26} mean/day ${v.mean():+7.2f}  P(pass within 21 days) OOS {p_oos:6.1%}  all {p_all:6.1%}", flush=True)
    out["trades_blocked_by_governor"] = int(blocked)
    out["trades_total"] = int(len(tr))
    print(f"PART B governor blocks {blocked} of {len(tr)} backtest trades ({blocked / len(tr):.0%})")
    return out


if __name__ == "__main__":
    df = load_1m(os.path.join(HERE, "..", "data", "MGC_CONTINUOUS.txt"))
    h15, atr15 = resample_causal(df, "15min"), causal_atr15_lookup(df)
    a = part_a(df, h15, atr15)
    b = part_b()
    with open(os.path.join(HERE, "round243_results.json"), "w") as f:
        json.dump(dict(part_a=a, part_b=b), f, indent=1, default=str)
    print("Saved round243_results.json")
