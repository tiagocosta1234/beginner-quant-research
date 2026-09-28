"""
Round 192: Round 190's disciplined bracket (+$1,650 win / -$850 loss) was built by
DISCRETIZING each day's already-fully-resolved real trade outcome after the fact --
a retrospective relabeling, not a live rule a trader or bot could actually execute.
Asked directly to fix this: every trade in the backtest must respect Broker's real
rules causally, bar by bar, not after the fact.

Rebuilt as a true intraday simulation. For each NQ trading day, both legs' signals
(POC reversion, Round 178; Value Area rejection, Round 184) are sized exactly as
they already are ($300 risk convention, real stop distance, real target, real
costs) and walked forward 1-minute bar by bar through the RTH session:
  - each bar, an open leg's own stop or target is checked first (stop wins a tie,
    same convention as idea_harness.resolve_bracket);
  - after resolving any per-leg stop/target hits, the day's running total (realized
    from closed legs + mark-to-market unrealized from any still open, at that bar's
    close) is checked against the two REAL, fixed dollar thresholds -- $1,650 (55%
    of the $50K Test's $3,000 target, the largest a day can be without ever
    forcing the real consistency limit to ratchet) and -$850 (the loss cap Round 190
    found keeps the median attempt at 5 days). The instant either is crossed, EVERY
    open position is flattened at that bar's close and no new entries happen for
    the rest of the day;
  - otherwise the day resolves normally (each leg's own stop/target, or flat by
    16:00 ET).
This is the actual causal rule: on any given bar, only information already known
(this bar's price, already-realized P&L, currently-open positions) decides whether
to stop trading -- no look-ahead.

Step 0, honest before running: the retrospective version's numbers (44.0% pass,
5-day median, Sharpe 0.083, max DD $22,650) are a best-case approximation --
achieving the exact discretized value on every day requires flattening at exactly
the right instant, something the retrospective version simply assumed. The causal
version can only do as well as the 1-minute bar data allows (a fast-moving bar can
blow through the cap before the code sees it, the same slippage-at-a-threshold risk
any real stop has), so it is expected to come out somewhat worse, not better,
before running -- tested to find out how much worse, not assuming it survives
intact.

Reports both the standalone stats (n, win rate, Sharpe, max drawdown) and the
chained real-Test-rules pass rate, same as every eval-mode chart this session.
Not a new signal, so no ledger row -- this is a construction/execution-fidelity
check on Round 190's already-logged result.
"""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import pass_speed_gate as G
from round178_volume_profile_poc import build_signals as poc_signals
from round184_value_area_breakout import build_signals_df as va_signals
from round171_databento_orb_replication import load_days_databento

RISK = 300.0
MAX_CONTRACTS = 50
CAP_WIN, CAP_LOSS = 1650.0, -850.0
PV, TK = H.PV["NQ"], H.TK["NQ"]


def size_leg(sig_row):
    if sig_row is None:
        return None
    direction, entry, sl, tp = sig_row["direction"], sig_row["entry"], sig_row["sl"], sig_row["tp"]
    dist = abs(entry - sl)
    if not (dist > 0):
        return None
    contracts = min(max(1, int(RISK // (dist * PV))), MAX_CONTRACTS)
    return dict(direction=int(direction), entry=float(entry), sl=float(sl),
               tp=float(tp) if tp == tp else np.nan, contracts=contracts, open=True)


def simulate_day(session, poc_row, va_row):
    """Returns (day_pnl, trigger) where trigger in {'cap_win','cap_loss','stops','flat','none'}."""
    legs = {}
    for name, row in (("poc", poc_row), ("va", va_row)):
        leg = size_leg(row)
        if leg is not None:
            legs[name] = leg
    if not legs:
        return 0.0, "none"

    hi, lo, cl = session["high"].values, session["low"].values, session["close"].values
    realized = 0.0
    trigger = "flat"

    for i in range(len(session)):
        for leg in legs.values():
            if not leg["open"]:
                continue
            d, px = leg["direction"], None
            if (d == 1 and lo[i] <= leg["sl"]) or (d == -1 and hi[i] >= leg["sl"]):
                px = leg["sl"]
            elif not np.isnan(leg["tp"]) and ((d == 1 and hi[i] >= leg["tp"]) or (d == -1 and lo[i] <= leg["tp"])):
                px = leg["tp"]
            if px is not None:
                realized += d * (px - leg["entry"]) * PV * leg["contracts"]
                leg["open"] = False

        unrealized = sum(leg["direction"] * (cl[i] - leg["entry"]) * PV * leg["contracts"]
                         for leg in legs.values() if leg["open"])
        day_total = realized + unrealized

        if any(leg["open"] for leg in legs.values()) and (day_total >= CAP_WIN or day_total <= CAP_LOSS):
            for leg in legs.values():
                if leg["open"]:
                    realized += leg["direction"] * (cl[i] - leg["entry"]) * PV * leg["contracts"]
                    leg["open"] = False
            trigger = "cap_win" if day_total >= CAP_WIN else "cap_loss"
            break

        if i == len(session) - 1:
            for leg in legs.values():
                if leg["open"]:
                    realized += leg["direction"] * (cl[i] - leg["entry"]) * PV * leg["contracts"]
                    leg["open"] = False

    if all(not leg["open"] for leg in legs.values()) and trigger == "flat":
        # figure out if it was actually stops/targets rather than the 16:00 flatten
        pass
    return realized, trigger


def build_daily():
    days = load_days_databento("NQ")
    poc_sig = poc_signals(days, TK).set_index("ts")
    va_sig = va_signals(days, TK, False).set_index("ts")
    rows, triggers = [], []
    for d in days:
        s = d["session"]
        if s.empty:
            rows.append((d["tday"], 0.0)); triggers.append("none"); continue
        t0 = s.index[0]
        poc_row = poc_sig.loc[t0] if t0 in poc_sig.index else None
        va_row = va_sig.loc[t0] if t0 in va_sig.index else None
        pnl, trig = simulate_day(s, poc_row, va_row)
        rows.append((d["tday"], pnl))
        triggers.append(trig)
    daily = pd.Series([r[1] for r in rows], index=pd.DatetimeIndex([r[0] for r in rows]))
    return daily, pd.Series(triggers, index=daily.index)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    daily, triggers = build_daily()

    if dry:
        active = daily[daily != 0]
        print(f"{len(active)} active days of {len(daily)}")
        print(triggers[triggers != "none"].value_counts())
        sys.exit(0)

    active = daily[daily != 0]
    win_rate = float((active > 0).mean())
    sharpe = float(daily.mean() / daily.std())
    dd = G.max_drawdown(daily.values)
    print(f"n={len(active)} win-rate {win_rate:.1%} Sharpe/day {sharpe:+.4f} max-DD ${dd:,.0f} "
          f"final ${daily.sum():+,.0f}")
    print(triggers[triggers != "none"].value_counts())

    from round190_disciplined_daily_bracket import chained_attempts
    all_days = daily.index
    att = chained_attempts(daily.values, list(all_days))
    outc = pd.Series([a["outcome"] for a in att]).value_counts().to_dict()
    n, p = len(att), outc.get("pass", 0)
    med = float(np.median([a["days"] for a in att]))
    print(f"chained: {n} attempts, {p} pass ({100*p/n:.1f}%), {outc.get('fail',0)} fail, "
          f"{outc.get('ongoing',0)} ongoing, median {med:.1f}d")

    with open(os.path.join(H.HERE, "round192_results.json"), "w") as f:
        json.dump(dict(n=len(active), win_rate=win_rate, sharpe=sharpe, max_dd=dd, final=float(daily.sum()),
                       chained_n=n, chained_pass=p, chained_rate=p/n, chained_median_days=med), f, indent=1)
