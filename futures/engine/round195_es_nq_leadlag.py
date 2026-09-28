"""
Round 195: continuing the pivot to genuinely new idea classes (Rounds
187/193 closed the daily-gap trigger; Round 194 closed quad-witching/rebalance
reversal). Checked IDEA_LEDGER.md first (k=369) -- Round 138's sub-hour scan
tested a 1-minute lead-lag construction ("a >= k SD move in one market ->
trade the other one bar later"), but only between MNQ and MGC, an index and
a metal with weak cross-correlation. The much more obviously correlated pair
available in this repo's own clean Databento data -- ES and NQ, both large,
liquid US equity-index futures -- has never been tested for INTRADAY lead-lag
at all (Round 142's "NQ-vs-ES relative value" was a daily-resolution pairs/
mean-reversion spread trade on the LEVEL gap between them, a different
question from "does one market's short-term move predict the other's next
move").

Economic hypothesis: ES (broader participation, S&P 500) and NQ (more
concentrated in mega-cap tech) are ~90%+ correlated, but differential
participation speed across market-maker/algo populations trading each
product can let one lead the other by seconds to minutes intraday --
documented in academic microstructure literature for closely related index
products. No strong prior on WHICH leads which, so both directions are
tested as separate, equally pre-registered variants, not chosen after seeing
either result.

Rule: build 5-minute RTH bars for both symbols (resampled from the clean
Databento 1-minute data already used in Rounds 171/187/193/194 -- 5-minute,
not 1-minute, specifically BECAUSE Round 177 already found that 1-minute-
resolution signals need enough contracts that fixed per-contract costs
dwarf a real, gross-positive, microscopic edge; 5 minutes gives more room
per trade without abandoning the "intraday microstructure" hypothesis
entirely). For the LEADER, compute each bar's own log return; trigger when
|return| >= 2.5x the causal rolling SD of that same return series (1,560
bars = 20 trading days at 78 bars/day, matching the 20-day window convention
Rounds 147/148/178/187 already use for this data, min_periods 780, shifted
1 bar -- no look-ahead). On a trigger, enter the FOLLOWER in the SAME
direction as the leader's move, at the triggering bar's own close, held for
exactly one more 5-minute bar (exit at the next bar's close) -- the same
"act one bar after the other market's move, fixed one-bar hold" construction
as Round 138's P5, just for a tightly-correlated pair and a coarser bar.
Signals whose next bar would cross into a different trading day are skipped
(no overnight holds). 1 contract per signal, full-size ES/NQ point values
and costs (as already used throughout Rounds 171-195).

Step 0, honest before running: even a real, gross-positive momentum-transfer
effect between two ~90%-correlated products is inherently small (it can only
be the sliver of NQ's move NOT already explained by ES's own contemporaneous
move, or vice versa) -- Round 177 found exactly this shape of problem (real
gross edge, swamped by fixed per-contract costs) at 1-minute resolution on a
DIFFERENT signal; 5-minute bars reduce but do not guarantee escape from that
failure mode. Tested because it is the one genuinely unexplored
microstructure-lead-lag pairing this ledger has clean data for, not because
the economics obviously clear the cost bar.

2 variants (ES leads NQ; NQ leads ES). Ledger k=369 -> 371; OOS bar
1 - 0.01/371 at the second variant.

Candidate: idea_harness.test_idea's own rule (positive net and gross; IS
P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round171_databento_orb_replication import load_days_databento

WINDOW = 1560   # 20 trading days x 78 five-minute bars/day
MIN_PERIODS = 780
Z = 2.5


def five_min_bars(sym):
    days = load_days_databento(sym)
    sess = pd.concat([d["session"] for d in days if not d["session"].empty]).sort_index()
    bars = sess.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}).dropna()
    bars["tday"] = bars.index.normalize()
    return bars


def build_signals(leader_bars, follower_bars, leader_sym, follower_sym):
    df = leader_bars[["close", "tday"]].join(follower_bars[["close"]], how="inner", rsuffix="_f")
    df = df.rename(columns={"close": "close_l", "close_f": "close_f"})
    ret = np.log(df["close_l"] / df["close_l"].shift(1))
    sd = ret.rolling(WINDOW, min_periods=MIN_PERIODS).std().shift(1)
    trig = ret.abs() >= Z * sd
    direction = np.sign(ret)

    same_day_next = df["tday"].shift(-1) == df["tday"]
    idx = df.index.values
    close_f = df["close_f"].values
    fire = (trig & (sd > 0) & same_day_next).values
    rows = []
    pv, cost = H.PV[follower_sym], H.cost_per_contract(follower_sym)
    d_arr = direction.values
    for i in np.where(fire)[0]:
        if i + 1 >= len(idx):
            continue
        pnl = d_arr[i] * (close_f[i + 1] - close_f[i]) * pv - cost
        rows.append((idx[i], idx[i + 1], int(d_arr[i]), 1, pnl, cost))
    return pd.DataFrame(rows, columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "cost"])


def build_trades(leader_sym, follower_sym):
    leader_bars = five_min_bars(leader_sym)
    follower_bars = five_min_bars(follower_sym)
    tr = build_signals(leader_bars, follower_bars, leader_sym, follower_sym)
    all_days = [d["tday"] for d in load_days_databento(follower_sym)]
    return tr, all_days


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv

    if dry:
        for leader, follower in (("ES", "NQ"), ("NQ", "ES")):
            tr, all_days = build_trades(leader, follower)
            print(f"{leader} leads {follower}: {len(tr)} trades of {len(all_days)} days")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for leader, follower in (("ES", "NQ"), ("NQ", "ES")):
        k = H.ledger_count() + 1
        tr, all_days = build_trades(leader, follower)
        name = f"{leader} leads {follower}, 5-min bars, 2.5 SD, 1-bar hold, Databento"
        r = H.test_idea(name, tr, all_days, follower, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 195 (pre-registered, new idea class: ES/NQ intraday lead-lag)",
                               commit, date="2026-09-28")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round195_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
