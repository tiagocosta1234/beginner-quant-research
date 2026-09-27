"""
Round 155: another genuinely new idea class -- checked against `IDEA_LEDGER.md`
first (k=196). 6E=F (Euro futures, an inverse dollar proxy) has only been
tested for its own FX-hours edge (Round 136, E1a/E1b) and in a month-end
hedging-flow spread against the DAX (Round 145, L1). Nothing has tested it as
a LEADING indicator for another market. Round 154 tried that shape once
already (BTC -> equities, on a risk-sentiment story) and found nothing --
this is a different economic channel, not a re-skin: gold is priced in
US dollars, so dollar weakness (Euro strength) has a mechanical,
decades-documented tendency to lift USD gold prices, not just a shared-
sentiment correlation. Worth testing as its own hypothesis for that reason,
not because the previous cross-asset test looked promising.

Step 0, honest before running: dollar-gold co-movement is mostly
CONTEMPORANEOUS (both react to the same rate/inflation news the same day),
which is exactly why this tests a ONE-DAY LAG (yesterday's 6E move ->
today's GC session), not same-day correlation -- the real question is
whether the mechanical transmission is instant and fully priced by the next
session, or whether it continues. Plausible size: unknown going in, but
likely a real (not sentiment-thin) relationship given the direct
denomination link, so worth measuring even though most calendar/lead-lag
ideas tested so far land at 0.02-0.15 daily Sharpe against a ~0.5 bar.

Rule: sig = sign(6E's prior-day open->close return r), filtered to |r| >=
0.5 x that day's 20-day SD (same magnitude filter used throughout this
ledger, e.g. Round 142's GAP_Z). Trades GC=F open->close the SAME direction
(Euro up -> dollar down -> long gold) the next session.
`round135_batch_d.market_frame`/`trades_from`/`judge_variant` unchanged for
data quality, R-units and real costs; split 2013-01-01 (matches every batch-D
round) plus the 2020-26 check.

1 variant. Ledger k=196 -> 197; OOS bar 1 - 0.01/197.

Candidate (as every batch-D round): net AND before-cost mean R > 0; IS
P(edge>0) >= 0.95 (pre-2013); OOS P(edge>0) >= the k=197 bar (2013-26); 2020-26
mean R > 0 too.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round135_batch_d as D

NAME = "6E prior-day move -> same-direction GC open->close (dollar leads gold)"
GAP_Z = 0.5


def build_signal(e6):
    r_prev = e6["r"].shift(1)
    sd_prev = e6["sd"]  # sd is already shift(1).rolling(20).std() inside market_frame
    big = r_prev.abs() >= GAP_Z * sd_prev
    return pd.Series(np.where(big, np.sign(r_prev), 0), index=e6.index).fillna(0)


def build_trades(dry_run=False):
    e6 = D.market_frame("6E=F")
    sig = build_signal(e6)
    sig = sig[sig != 0]
    if dry_run:
        return sig, None
    gc = D.market_frame("GC=F")
    direction = sig.reindex(gc.index).fillna(0)
    tr = D.trades_from(gc, direction, "GC=F")
    return sig, tr


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    k = H.ledger_count() + 1
    print(f"k = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)

    sig, tr = build_trades(dry_run=dry)
    if dry:
        print(f"6E qualifying days (|prior r|>={GAP_Z}xSD): {len(sig)}")
        print(f"  first: {sig.index.min()}  last: {sig.index.max()}")
        print(f"  long days: {(sig > 0).sum()}  short days: {(sig < 0).sum()}")
        span_years = (sig.index.max() - sig.index.min()).days / 365.25
        print(f"  ~{len(sig) / span_years:.1f} qualifying days per year")
        print("\n--dry-run: counts only, no P&L. Hand-check a few signals before running for real.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    r = D.judge_variant(NAME, tr, k)
    lines = H.ledger_rows([r], "Round 155 (pre-registered, new idea class: dollar/currency leading a commodity)",
                           commit, date="2026-09-27")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round155_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
