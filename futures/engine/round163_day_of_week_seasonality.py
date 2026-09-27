"""
Round 163: a second new idea class today (after Round 162's rates/discount-
rate test). Checked IDEA_LEDGER.md first (k=219) -- turn-of-month, month-end
rebalancing, pre-holiday days and the Halloween 6-month block have all been
tested; nothing has tested plain DAY-OF-WEEK seasonality. Different
granularity again: a weekly-cycle effect, not a day-count-from-an-event or
month-block rule.

The "weekend effect" / "Monday effect" (French 1980): US equity returns on
Monday have historically run lower than other weekdays, commonly attributed
to bad news accumulating/being released over the weekend, or short-sellers
covering into the close on Friday and reopening short into Monday. Widely
taught and, per multiple published follow-ups, largely faded or reversed
after the mid-1980s -- exactly the kind of decay this ledger's own published-
anomaly rounds (FOMC drift, Treasury auction rebound) keep finding directly.

Step 0, honest before running: one of the oldest, most publicly known
calendar effects in finance (45+ years old). Every well-known published
effect this ledger has tested so far has either decayed after publication or
never cleared the bar. Tested for completeness of the calendar-effects class,
not because prior odds have improved.

Rule: long ES/NQ/YM/RTY open->close every trading day EXCEPT Monday (flat
Monday); compare against long-every-day (D1's own baseline, same requirement
Round 156 applied to the Halloween block -- a day-of-week filter that merely
matches the market's average long-only drift isn't a real effect). A second,
sharper variant isolates the claimed mechanism directly: SHORT Monday only
(flat every other day), which only makes money if Monday itself is actually
negative on average, not just weaker than other days.
`round135_batch_d`'s frames/costs/splits unchanged (2013/2020 splits).

2 variants. Ledger k=219 -> 221; OOS bar 1 - 0.01/221 at the second variant.

Candidate (each variant separately): net AND before-cost mean R > 0; IS
P(edge>0) >= 0.95 (pre-2013); OOS P(edge>0) >= the bar at that variant's k
(2013-26); 2020-26 mean R > 0; the long-Tue-Fri variant must also beat being
long every day (Round 156's own standard).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round135_batch_d as D

MONDAY = 0


def build_long_tue_fri(frames):
    out, base = [], []
    for sym, f in frames.items():
        direction = pd.Series(np.where(f.index.dayofweek != MONDAY, 1, 0), index=f.index)
        out.append(D.trades_from(f, direction, sym))
        base.append(D.trades_from(f, pd.Series(1, index=f.index), sym))
    return pd.concat(out, ignore_index=True), pd.concat(base, ignore_index=True)


def build_short_monday(frames):
    out = []
    for sym, f in frames.items():
        direction = pd.Series(np.where(f.index.dayofweek == MONDAY, -1, 0), index=f.index)
        out.append(D.trades_from(f, direction, sym))
    return pd.concat(out, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    k0 = H.ledger_count()
    frames = {sym: D.market_frame(sym) for sym in D.EQUITY}

    if dry:
        f = frames["ES=F"]
        n_mon = int((f.index.dayofweek == MONDAY).sum())
        print(f"ES=F calendar days: {len(f)}, Mondays: {n_mon} ({n_mon / len(f):.1%})")
        print("\n--dry-run: counts only, no P&L. Hand-check a few weeks before running for real.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"k0 = {k0}\n", flush=True)

    tr_tf, tr_base = build_long_tue_fri(frames)
    k = k0 + 1
    r1 = D.judge_variant("Long Tue-Fri, flat Monday, ES/NQ/YM/RTY (weekend effect)", tr_tf, k)
    beats_base = bool(tr_tf["pnl"].mean() > tr_base["pnl"].mean())
    r1["candidate"] = bool(r1["candidate"] and beats_base)
    print(f"      long-every-day baseline: mean ${tr_base['pnl'].mean():+.2f} vs Tue-Fri "
          f"${tr_tf['pnl'].mean():+.2f} | beats baseline: {beats_base} | "
          f"{'CANDIDATE' if r1['candidate'] else 'no'}", flush=True)

    tr_mon = build_short_monday(frames)
    k = k0 + 2
    r2 = D.judge_variant("Short Monday only, flat Tue-Fri, ES/NQ/YM/RTY (Monday-effect direct test)", tr_mon, k)

    lines = H.ledger_rows([r1, r2], "Round 163 (pre-registered, new idea class: day-of-week seasonality)",
                           commit, date="2026-09-27")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round163_results.json"), "w") as f:
        json.dump([r1, r2], f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
