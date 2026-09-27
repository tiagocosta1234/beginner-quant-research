"""
Round 156: a third new idea class today. Checked against `IDEA_LEDGER.md`
first (k=197) -- turn-of-month (specific days around the month boundary),
month-end rebalancing flows, and pre-holiday days have all been tested.
Nothing has tested a SEASONAL MONTH-BLOCK effect: the "Halloween indicator"
/ "Sell in May and go away" (Bouman & Jacobsen 2002) -- equities have
historically returned more Nov-Apr than May-Oct. Different granularity from
everything else tried (a 6-month regime, not a day-of-month or day-count-
from-an-event rule).

Step 0, honest before running: this is one of the most publicly known
calendar effects in finance, published over 20 years ago. Published
anomalies in this ledger have consistently either decayed after publication
(FOMC drift, Treasury auction rebound) or held up only weakly since 2013
(Connors RSI(2), IBS, month-end rebalancing). No reason to expect this one
to be different -- tested for completeness of the "well-known calendar
effects" class the earlier batches already opened, not because its
plausible size looks better.

Rule: long ES/NQ/YM/RTY open->close every trading day in November through
April; flat May through October. `round135_batch_d`'s frames/costs/splits
unchanged (2013/2020 splits); Broker requires flat daily, so "the
Halloween trade" here means long every day inside the favorable window, not
a literal 6-month hold -- matching how every other batch-D idea already
handles "positions" (D1 already reports the "long every day" baseline this
is a seasonal filter ON TOP of).

1 variant. Ledger k=197 -> 198; OOS bar 1 - 0.01/198.

Candidate: net AND before-cost mean R > 0; IS P(edge>0) >= 0.95 (pre-2013);
OOS P(edge>0) >= the k=198 bar (2013-26); 2020-26 mean R > 0 too; must also
beat being long every day (D1's own descriptive baseline), since a seasonal
LONG filter that merely matches the market's average long-only drift isn't
a seasonal effect, just being long in an uptrending market.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round135_batch_d as D

NAME = "Halloween indicator: long Nov-Apr, flat May-Oct, ES/NQ/YM/RTY"


def build_trades(dry_run=False):
    frames = {sym: D.market_frame(sym) for sym in D.EQUITY}
    favorable = lambda idx: idx.month.isin([11, 12, 1, 2, 3, 4])
    if dry_run:
        f = frames["ES=F"]
        sig = pd.Series(np.where(favorable(f.index), 1, 0), index=f.index)
        return sig, None
    out, long_every_day = [], []
    for sym, f in frames.items():
        direction = pd.Series(np.where(favorable(f.index), 1, 0), index=f.index)
        out.append(D.trades_from(f, direction, sym))
        long_every_day.append(D.trades_from(f, pd.Series(1, index=f.index), sym))
    return pd.concat(out, ignore_index=True), pd.concat(long_every_day, ignore_index=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    k = H.ledger_count() + 1
    print(f"k = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)

    if dry:
        sig, _ = build_trades(dry_run=True)
        n_favorable = int(sig.sum())
        print(f"ES=F calendar days: {len(sig)}, favorable (Nov-Apr) days: {n_favorable} "
              f"({n_favorable / len(sig):.1%})")
        print("\n--dry-run: counts only, no P&L. Hand-check a few months before running for real.")
        sys.exit(0)

    tr, tr_every_day = build_trades()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    r = D.judge_variant(NAME, tr, k)
    beats_long_every_day = bool(tr["pnl"].mean() > tr_every_day["pnl"].mean())
    r["candidate"] = bool(r["candidate"] and beats_long_every_day)
    print(f"      long-every-day baseline: mean ${tr_every_day['pnl'].mean():+.2f} "
          f"vs seasonal ${tr['pnl'].mean():+.2f} | beats baseline: {beats_long_every_day} | "
          f"{'CANDIDATE' if r['candidate'] else 'no'}", flush=True)
    lines = H.ledger_rows([r], "Round 156 (pre-registered, new idea class: Halloween/seasonal month-block)",
                           commit, date="2026-09-27")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round156_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
