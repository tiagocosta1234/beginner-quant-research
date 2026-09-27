"""
Round 166: the trader asked to build an original strategy, not another borrowed
named concept (ICT, a YouTube scalper, a published anomaly). This is the
first genuinely original construction in this campaign -- synthesized from
its OWN 224 rows of findings, not copied from outside.

The actual constraint every one of those 224 rows has run into: the
pass-speed gate needs a daily Sharpe near 0.5, and no single signal has ever
landed above ~0.06 (Connors RSI(2): 0.017; IBS: 0.042 -- both from
pass_speed_gate.py's own power notes). That's 10-30x short, and no amount of
re-parameterizing a single rule closes a gap that size.

The idea: `CURRENT_STATE.md`'s own "Open leads" section already names four
survivors from the SAME family (equity weakness in an uptrend) that fire on
mostly DIFFERENT trigger conditions -- Connors RSI(2)<10 (a 2-day momentum
extreme), IBS<0.2 (yesterday's candle closed near its low), month-end
rebalancing (a calendar/flow-driven 3-day window), pre-holiday (a calendar
day-count rule). None of the four has ever been combined with the others in
this ledger; each was always tested alone. Portfolio theory says combining
several imperfectly-correlated return streams of similar quality can raise
the AGGREGATE Sharpe above any single piece's (Sharpe_combined ~ sqrt(N) x
Sharpe_avg for N independent, equal streams) -- not a new predictive signal,
a new PORTFOLIO CONSTRUCTION on top of already-tested pieces. This is the
one lever this campaign has never pulled: diversification, not a new rule.

Step 0, honest before running, three ways: (1) these four aren't
independent -- they're all "buy the dip in an uptrend" restated four ways,
so they likely correlate with each other and with the market's own drift;
the real diversification benefit could be far below the naive sqrt(4)=2x
ceiling. (2) Choosing exactly these four, after seeing which members of the
dip-buy family survived individually, is itself a form of selection -- this
is disclosed as exploratory and held to the SAME OOS bar as any new idea at
the ledger's current k, not given a pass. (3) Summing each leg's R-return
per (date, symbol) is not just a convenience -- it's the economically
correct model of running all four systems on one real account, since
same-contract netting (this repo's own documented Broker rule) means two
signals disagreeing on ES the same day actually DO net into a smaller
position, and two agreeing DO combine into a bigger one; summing signed R
reproduces that directly.

Rule: reuse each leg's already-validated logic unchanged (no new tuning):
  Connors: round142.connors(frame, 10) -- RSI(2)<10 above the 200-day MA
  IBS: round145.ibs_long(ohlc_frame(sym)) -- yesterday's IBS < 0.2
  Month-end: round144.rebalance_direction(ES, ZN) -- fade stocks-vs-bonds
             MTD move, last 3 trading days of complete months
  Pre-holiday: round135.d3(frames) -- long the day before an NYSE holiday
On ES/NQ/YM/RTY, 2000-2026. Per (date, symbol), sum whichever legs are
active that day into one combined R contribution (0 legs = flat that day
for that symbol). Judged exactly like every other batch-D-style test
(round135.judge_variant: net/gross positive, IS P>=0.95 pre-2013, OOS
P>=bar 2013-26) -- PLUS the number that actually matters for going live:
the combined book's daily Sharpe against the pass-speed gate's ~0.5
requirement, and each leg's own daily-R correlation with the others, to
show directly whether diversification helped or the four just move together.

1 variant (plus diagnostics). Ledger k=224 -> 225; OOS bar 1 - 0.01/225.

Candidate: same as every batch-D test (net AND gross > 0; IS P>=0.95;
OOS P>=bar) -- combining does not earn a different bar.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round135_batch_d as D
from round142_batch_j import connors
from round144_batch_k import rebalance_direction
from round145_batch_l import ohlc_frame, ibs_long


def build_legs():
    eq = {s: D.market_frame(s) for s in D.EQUITY}
    zn = D.market_frame("ZN=F")
    rb = rebalance_direction(eq["ES=F"], zn)

    legs = {}
    legs["connors"] = pd.concat([D.trades_from(eq[s], connors(eq[s], 10), s) for s in D.EQUITY], ignore_index=True)
    legs["ibs"] = pd.concat([D.trades_from(ohlc_frame(s), ibs_long(ohlc_frame(s)), s) for s in D.EQUITY],
                            ignore_index=True)
    legs["month_end"] = pd.concat([D.trades_from(eq[s], rb.reindex(eq[s].index).fillna(0), s) for s in D.EQUITY],
                                  ignore_index=True)
    legs["pre_holiday"] = D.d3(eq)
    return legs


def leg_daily(legs):
    """Each leg's own daily-summed R series (all 4 symbols combined), for the
    correlation diagnostic -- separate from the per-symbol combination below."""
    out = {}
    for name, tr in legs.items():
        out[name] = tr.groupby("date")["pnl"].sum()
    return pd.DataFrame(out).fillna(0.0)


def combine(legs):
    """Sum whichever legs are active on each (date, symbol) -- the economically
    correct model of running all four systems on one netted account."""
    tagged = [df.assign(signal=name) for name, df in legs.items()]
    all_tr = pd.concat(tagged, ignore_index=True)
    overlap = all_tr.groupby(["date", "market"]).size()
    n_overlap = int((overlap > 1).sum())
    combined = all_tr.groupby(["date", "market"], as_index=False)[["gross", "pnl"]].sum()
    return combined, n_overlap, len(overlap)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    k = H.ledger_count() + 1
    print(f"k = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)

    legs = build_legs()
    for name, tr in legs.items():
        print(f"  leg {name:<12} {len(tr):>6} trades  {tr.index.size and tr['pnl'].mean():+.4f}R/trade")

    daily = leg_daily(legs)
    corr = daily.corr()
    print("\nDaily-R correlation between legs (all 4 symbols summed per day):")
    print(corr.round(3).to_string())

    combined, n_overlap, n_leg_days = combine(legs)
    print(f"\n(date,symbol) pairs with 2+ legs active same day: {n_overlap} of {n_leg_days} "
          f"({n_overlap / n_leg_days:.1%})")

    if dry:
        print("\n--dry-run: counts and correlations only, no candidate judgment. Hand-check before running for real.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    r = D.judge_variant("Round 166 ensemble: Connors+IBS+month-end+pre-holiday, netted, 4 indices", combined, k)

    calendar = D.market_frame("ES=F").index
    active_days = combined.groupby("date")["pnl"].sum()
    full_calendar = active_days.reindex(calendar, fill_value=0.0)
    active_sharpe = float(active_days.mean() / active_days.std())
    gate_sharpe = float(full_calendar.mean() / full_calendar.std())
    print(f"\nDaily Sharpe on ACTIVE days only: {active_sharpe:+.3f} (misleading on its own)")
    print(f"Daily Sharpe on the FULL calendar ({len(calendar)} days, {len(calendar) - len(active_days)} flat): "
          f"{gate_sharpe:+.3f} -- this is the number the pass-speed gate actually needs near 0.5")

    lines = H.ledger_rows([r], "Round 166 (pre-registered, original strategy: dip-buy-family ensemble)",
                           commit, date="2026-09-27")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round166_results.json"), "w") as f:
        json.dump(dict(result=r, leg_corr=corr.to_dict(), n_overlap=n_overlap, n_leg_days=n_leg_days,
                       active_days_sharpe=active_sharpe, full_calendar_gate_sharpe=gate_sharpe),
                  f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
