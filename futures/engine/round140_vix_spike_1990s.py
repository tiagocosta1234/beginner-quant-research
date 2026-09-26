"""
Round 140: does Round 139's lead -- "buy equities the day after a VIX spike" --
hold on data it has never seen? Pre-registered 2026-09-26, committed before any
result is run.

The lead (Round 139, H1c): long ES/NQ/YM/RTY from the 18:00 open to settlement on
the day after VIX closes >= 1.2 x its average of the 20 trading days before that.
+0.117R/trade, positive 2000-12 and 2013-26, beats long-every-day in both; failed
the pre-registered bar. Its futures data starts 2000-10, so everything before is
untouched: VIX (Yahoo ^VIX) from 1990, SPY from 1993-01-29.

Primary test (clean timing -- VIX's previous close is known before today's 09:30
open): SPY open -> close on signal days, 1993-02 .. 2000-09-30. Identical signal.
R units = the 20-day SD of SPY's open->close returns (prior days). Costs as one
MES contract (commission $1.22 + 2 ticks) on the equivalent index level (10 x SPY).
Days with open == close (missing opens) are dropped, as in batch D.

Replication rule (fixed now): the lead REPLICATES if, on the primary test,
  (1) signal-day mean R > 0 with bootstrap P(edge>0) >= 0.95, AND
  (2) its excess over being long every day (same days, same units) > 0 with
      P(excess>0) >= 0.90.
Power note (from the dry-run count, before any result): 92 signal days out of
1,893 (4.9%) -- the 1990s had fewer spikes -- so a true effect of Round 139's size
could easily miss; a miss here is weak evidence either way.
Secondary, descriptive only: the S&P 500 index close -> close (the full-day
analog of the futures window; Yahoo's 1990s index opens are unusable), 1990-2000.
Close -> close enters at 16:00, 15 minutes before VIX's 16:15 close, a small timing
advantage; that is why it is descriptive only.

Even if it replicates, the lead stays a lead (not a candidate): the ledger's bar is
not changed after the fact. A replication would justify forward paper-tracking.
1 ledger variant (k=144 -> 145).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round122b_tom_long_history import load_daily
from round139_batch_h import prior

END = pd.Timestamp("2000-10-01")
MES_COST = 1.22 + 2 * H.TK["MES"] * H.PV["MES"]


def spike_signal(dates):
    vix = load_daily("^VIX")["close"]
    ratio = (vix / vix.shift(1).rolling(20).mean()).dropna()
    return prior(ratio, dates) >= 1.2


def bootstrap_excess(a, b, n=20_000, seed=0):
    rng = np.random.default_rng(seed)
    return float(np.mean([rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() > 0 for _ in range(n)]))


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    spy = load_daily("SPY")
    spy = spy[(spy.index < END) & (spy["open"] != spy["close"])].copy()
    spy["r"] = np.log(spy["close"] / spy["open"])
    spy["sd"] = spy["r"].shift(1).rolling(20).std()
    spy = spy[spy["sd"] > 0]
    spy["cost_r"] = MES_COST / (spy["sd"] * spy["open"] * 10 * H.PV["MES"])
    spy["R"] = spy["r"] / spy["sd"] - spy["cost_r"]
    sig = spike_signal(spy.index)
    on, every = spy.loc[sig.values, "R"].values, spy["R"].values
    st = J.edge_stats(pd.DataFrame({"pnl": on}), n_boot=40_000)
    p_ex = bootstrap_excess(on, every)
    ex = on.mean() - every.mean()
    replicated = bool(st["exp"] > 0 and st["p_pos"] >= 0.95 and ex > 0 and p_ex >= 0.90)
    print(f"PRIMARY  SPY open->close {spy.index[0].date()} .. {spy.index[-1].date()} ({len(spy)} days)")
    print(f"  VIX-spike days: n={st['n']} mean {st['exp']:+.3f}R  P(edge>0) {st['p_pos']:.4f}")
    print(f"  long every day: {every.mean():+.3f}R  -> excess {ex:+.3f}R  P(excess>0) {p_ex:.3f}")
    for lo, hi in [("1993", "1996-12-31"), ("1997", "2000-09-30")]:
        m = (spy.index >= lo) & (spy.index <= hi)
        s_on = spy.loc[m & sig.values, "R"]
        print(f"    {lo}-{hi[:4]}: spike days n={len(s_on)} {s_on.mean():+.3f}R vs every day {spy.loc[m, 'R'].mean():+.3f}R")
    print(f"  => {'REPLICATES' if replicated else 'does NOT replicate'} (rule: P(edge>0) >= 0.95 and P(excess>0) >= 0.90)")

    gs = load_daily("^GSPC")["close"]
    gs = gs[(gs.index >= "1990-01-01") & (gs.index < END)]
    cc = np.log(gs / gs.shift(1)).dropna()
    sd = cc.shift(1).rolling(20).std()
    Rc = (cc / sd).dropna()
    sig_c = spike_signal(Rc.index)
    on_c = Rc[sig_c.values].values
    stc = J.edge_stats(pd.DataFrame({"pnl": on_c}))
    print(f"\nSECONDARY (descriptive) S&P 500 close->close 1990-2000, before costs: spike days n={stc['n']} "
          f"{stc['exp']:+.3f}R P {stc['p_pos']:.3f} | every day {Rc.mean():+.3f}R | excess {on_c.mean() - Rc.mean():+.3f}R "
          f"P(excess>0) {bootstrap_excess(on_c, Rc.values):.3f}")

    row = dict(name="H1c VIX-spike long, 1993-2000 SPY replication (R units)", n=st["n"], exp=st["exp"],
               p_pos=st["p_pos"], excess=ex, p_excess=p_ex, replicated=replicated)
    line = (f"| {H.ledger_count() + 1} | 2026-09-26 | {row['name']} | Round 140 replication (pre-registered) | {commit} | "
            f"{row['n']} | {row['exp']:+.3f}R | n/a | replication P {row['p_pos']:.3f}, excess P {p_ex:.3f} | "
            f"{'replicated lead' if replicated else 'not replicated'} |")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    with open(os.path.join(H.HERE, "round140_results.json"), "w") as f:
        json.dump(row, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
