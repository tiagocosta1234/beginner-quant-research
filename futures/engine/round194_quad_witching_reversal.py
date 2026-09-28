"""
Round 194: continuing the pivot to genuinely new idea classes after Rounds
187/193 closed both directions of the naive daily-open-gap trigger. Checked
IDEA_LEDGER.md first (k=365) -- turn-of-month, month-end rebalancing,
day-of-week, pre-holiday, options-expiration WEEKS (Round 141, a different
granularity: the whole week, not a specific day) and Treasury auctions have
all been tested; nothing has tested the Nasdaq-100's own quarterly index
rebalance / quadruple-witching EFFECTIVE DAY specifically.

Two real, calendar-computable (no new data source) mechanisms coincide on
the same date every March/June/September/December:
  1. Quadruple witching: US index options, index futures, stock options and
     single-stock futures all expire simultaneously on the third Friday of
     March/June/September/December. Published research documents elevated
     volume/volatility that Friday and a partial unwind the following week
     as expiring positions get closed and rolled.
  2. The Nasdaq-100's own quarterly rebalance (share/weight adjustment, and
     in December the annual membership reconstitution) becomes effective
     before market open on the Monday immediately after that same Friday
     (confirmed directly against Nasdaq's own investor-relations release,
     "Nasdaq-100 Index(R) June 2026 Quarterly Changes": effective prior to
     market open Monday, June 22, 2026, the Monday after the June 19 third
     Friday) -- an NQ-specific flow on top of the market-wide expiration
     unwind.

Rule: on the trading day that is the third Friday of March/June/September/
December (weekday==Friday, day-of-month 15-21), measure that day's open->
close return. On the immediately following trading day (normally the
Monday after; the next available trading day if a holiday falls between),
take a position that FADES Friday's move (direction = -sign(Friday's
return)) from the open to the close -- the expiration-unwind/rebalance-flow
reversal hypothesis, not a guessed continuation. ES, NQ, YM, RTY (`NQ` is
the one hypothesized to carry an EXTRA rebalancing-specific component on top
of the market-wide expiration effect the other three also have).
`round135_batch_d`'s frames/costs/splits unchanged (2013/2020 splits, R
units, one contract's risk-adjusted size).

Control (isolates whether quad-witching Fridays are special, or this is just
Round 135 D2's generic "fade any big day" reversal wearing a calendar mask):
the same fade-Friday's-move-on-Monday construction applied to EVERY Friday-
to-next-trading-day transition in the data, not just quad-witching ones.
The quad-witching variant must beat this generic-Friday-fade baseline, same
"must beat the naive comparison" discipline Round 163 applied to the
long-Tue-Fri variant.

Step 0, honest before running: quad-witching's own volume/volatility spike
is well documented, but the DIRECTIONAL "expiration unwind gets faded"
mechanism is a specific, less-established reading of it, and this fires only
~4x/year per market -- roughly 52 IS occurrences (2000-2012) and ~52 OOS
(2013-2026) per market, an order of magnitude fewer than every other test in
this ledger. Expect wide bootstrap intervals and correspondingly limited
power to clear a 0.99-plus bar even if a real, small effect exists; tested
for completeness of the calendar-effects class and because it is one of the
only two genuinely new leads identified after the gap-fade/continuation
class closed, not because the small-n problem has been solved.

5 variants (4 markets + 1 baseline check, though only the 4 market variants
carry ledger rows -- the baseline is a comparison, not its own candidate).
Ledger k=365 -> 369; OOS bar 1 - 0.01/369 at the last variant.

Candidate (each market variant): net AND before-cost mean R > 0; IS
P(edge>0) >= 0.95 (2000-12); OOS P(edge>0) >= the bar at that variant's k
(2013-26); 2020-26 mean R > 0; must beat the generic-Friday-fade baseline
(Round 163's own standard, applied here).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round135_batch_d as D

FRIDAY = 4


def _fade_next_day(d, fri_mask):
    idx = d.index
    fri_pos = np.where(fri_mask)[0]
    fri_pos = fri_pos[fri_pos + 1 < len(idx)]  # need a following trading day
    nxt_pos = fri_pos + 1
    direction = pd.Series(0, index=idx)
    direction.iloc[nxt_pos] = -np.sign(d["r"].values[fri_pos])
    return direction


def build_quad_witching(frames):
    out = []
    for sym in D.EQUITY:
        d = frames[sym]
        is_3rd_fri = (d.index.dayofweek == FRIDAY) & (d.index.day >= 15) & (d.index.day <= 21) & \
                     d.index.month.isin([3, 6, 9, 12])
        out.append(D.trades_from(d, _fade_next_day(d, is_3rd_fri), sym))
    return pd.concat(out, ignore_index=True)


def build_generic_friday_baseline(frames):
    out = []
    for sym in D.EQUITY:
        d = frames[sym]
        is_fri = (d.index.dayofweek == FRIDAY)
        out.append(D.trades_from(d, _fade_next_day(d, is_fri), sym))
    return pd.concat(out, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    k0 = H.ledger_count()
    frames = {sym: D.market_frame(sym) for sym in D.EQUITY}

    if dry:
        d = frames["NQ=F"]
        is_3rd_fri = (d.index.dayofweek == FRIDAY) & (d.index.day >= 15) & (d.index.day <= 21) & \
                     d.index.month.isin([3, 6, 9, 12])
        print(f"NQ=F: {is_3rd_fri.sum()} quad-witching Fridays of {len(d)} days "
              f"({d.index[0].date()}..{d.index[-1].date()})")
        print("Sample dates:", list(d.index[is_3rd_fri][:6].date))
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"k0 = {k0}\n", flush=True)

    tr_qw = build_quad_witching(frames)
    tr_base = build_generic_friday_baseline(frames)
    print(f"generic-Friday-fade baseline (all 4 markets pooled): mean ${tr_base['pnl'].mean():+.4f}R "
          f"n={len(tr_base)}\n", flush=True)

    rows = []
    for sym in D.EQUITY:
        k = H.ledger_count() + 1
        sub = tr_qw[tr_qw["market"] == sym]
        base_sub = tr_base[tr_base["market"] == sym]
        r = D.judge_variant(f"Quad-witching Friday fade on next trading day, {sym}", sub, k)
        beats_base = bool(sub["pnl"].mean() > base_sub["pnl"].mean())
        r["candidate"] = bool(r["candidate"] and beats_base)
        print(f"      {sym} generic-Friday-fade baseline: ${base_sub['pnl'].mean():+.4f}R vs "
              f"quad-witching ${sub['pnl'].mean():+.4f}R | beats baseline: {beats_base} | "
              f"{'CANDIDATE' if r['candidate'] else 'no'}", flush=True)
        rows.append(r)
        lines = [f"| {H.ledger_count() + 1} | 2026-09-28 | {r['name']} (R units) | "
                 f"Round 194 (pre-registered, new idea class: quad-witching/Nasdaq-100 rebalance reversal) | "
                 f"{commit} | {r['n']} | {r['exp']:+.3f}R | {r['exp_gross']:+.3f}R | "
                 f"{r['p_is']:.2f} / {r['p_oos']:.3f} | {'CANDIDATE' if r['candidate'] else 'no edge'} |"]
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    with open(os.path.join(H.HERE, "round194_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
