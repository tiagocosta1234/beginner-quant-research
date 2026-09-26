"""
Round 146: does Round 145's IBS lead hold on data it has never seen? Pre-registered
2026-09-26, committed before any result is run.

The lead (Round 145, L3): long ES/NQ/YM/RTY from the 18:00 open to settlement on the
day after IBS = (close - low) / (high - low) < 0.2. +0.077R net; 2013-26 +0.114R,
P 1.00000 (above the 0.99994 bar); 2000-12 +0.031R, P 0.888 (needed 0.95), so no
edge by the rule. Its futures data starts 2000-10; everything before is untouched.

Primary test: the S&P 500 index (^GSPC), 1990-01-02 .. 2000-09-29. IBS from the
index's own high, low and close of the previous day; return close -> close (the
full-day analog of the futures window, as Round 143). Why the index, not SPY: IBS
fires when the close is near the low, and an ETF close printed at the bid would
bounce back the next day -- a fake reversal. The index has no bid/ask (its stale
component prices bias close -> close *against* reversal). The signal is set by a
close and entered at that close; S&P futures traded until 16:15 ET, so it was
executable after the 16:00 print (Round 143's reasoning).

Units: R = close -> close return / the 20-day SD of those returns (prior days).
Costs (fixed now, fixing Round 143's flaw): Round 143 charged one MES contract at
the 1990s index level, which made costs 0.08-0.27R per trade against 0.03-0.07R on
the futures data. Here every trade pays a fixed cost equal to the median ES cost in
R over 2000-12 (computed from batch D's frame; the higher, more conservative of the
futures-era levels). The same cost applies to the long-every-day baseline.

Replication rule (same form as Rounds 140 and 143):
  (1) mean R after the fixed cost > 0 with bootstrap P(edge>0) >= 0.95, AND
  (2) the excess over long every day (same window, units and cost) > 0 with
      P(excess>0) >= 0.90.
A pass makes IBS a "replicated lead", not a candidate: the ledger's bar is not
changed after the fact. 1 ledger variant (k=168 -> 169).

Descriptive only: sub-periods 1990-94 / 1995-2000; before costs; with Round 143's
MES-at-index-level cost; SPY open -> close 1993-2000 on the same signal days (no
overnight, no bounce); IBS < 0.1 and 0.2-0.8 / > 0.8 buckets.

Power notes and data checks (dry run, before any result): 2,717 index days, 544 signal days (20.0%;
261 in 1990-94, 283 in 1995-2000; 289 with IBS < 0.1). Fixed cost = 0.0656R per trade
(Round 143's MES-at-index cost had a median of 0.203R). Data: ^GSPC's 1990s opens
are copies of the prior close, but its high/low are real -- same-day IBS correlates
0.866 with SPY's (1993-2000), and only 2-5% of days a year have high/low equal to the
open/close extremes; 5-15% of days a year close exactly at the high or low (no year
stands out). Power: condition (1) needs a net mean of about +0.071R (1.645 standard
errors). If the 1990s effect matched the futures era's +0.115R before costs (+0.049R
net), it would pass about 30% of the time; if it matched 2013-26, about 55-60%. A
miss is weak evidence against; a pass would be real support.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
import round135_batch_d as D
from round122b_tom_long_history import load_daily
from round140_vix_spike_1990s import bootstrap_excess
from round143_dip_family_1990s import START, END, SUBS, index_frame, spy_open_close
from round145_batch_l import load_ohlc


def fixed_cost():
    es = D.market_frame("ES=F")
    return float(es.loc[es.index < "2013-01-01", "cost_r"].median())


def gspc_ibs():
    g = index_frame()
    o = load_ohlc("^GSPC")
    o = o[~o.index.duplicated(keep="last")]
    g = g.join(o[["high", "low", "close"]], rsuffix="_o", how="left")
    ok = ((g["close"] - g["close_o"]).abs() <= 1e-6 * g["close"]) & (g["high"] > g["low"]) & \
         (g["low"] <= g["close"]) & (g["close"] <= g["high"])
    g["ibs"] = np.where(ok, (g["close"] - g["low"]) / (g["high"] - g["low"]), np.nan)
    g["p_ibs"] = g["ibs"].shift(1)  # previous day's IBS, known at the entry close
    return g


def dry_run():
    g = gspc_ibs()
    w = (g.index >= START) & (g.index < END) & g["sd"].notna().values
    x = g[w]
    print(f"sample {x.index[0].date()} .. {x.index[-1].date()}: {len(x)} days; previous-day IBS available "
          f"{x['p_ibs'].notna().mean():.3f}; share of IBS exactly 0 or 1 {x['ibs'].isin([0, 1]).mean():.3f}")
    print(f"signal days (previous IBS < 0.2): {(x['p_ibs'] < 0.2).sum()} ({(x['p_ibs'] < 0.2).mean():.3f}); "
          f"< 0.1: {(x['p_ibs'] < 0.1).sum()}; by half: {((x.index < '1995') & (x['p_ibs'] < 0.2)).sum()} / "
          f"{((x.index >= '1995') & (x['p_ibs'] < 0.2)).sum()}")
    s = load_ohlc("SPY")
    s = s[(s.index < END) & (s["high"] > s["low"])]
    s_ibs = (s["close"] - s["low"]) / (s["high"] - s["low"])
    both = pd.concat([x["ibs"], s_ibs], axis=1, join="inner").dropna()
    print(f"^GSPC vs SPY same-day IBS 1993-2000: n={len(both)} correlation {both.corr().iloc[0, 1]:.3f}")
    print(f"fixed cost per trade = ES 2000-12 median {fixed_cost():.4f}R; Round 143's MES-at-index cost median "
          f"{x['cost_r'].median():.3f}R")
    spy = spy_open_close()
    print(f"SPY open->close descriptive days on signal: {spy.index.isin(x.index[x['p_ibs'] < 0.2]).sum()}")


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        dry_run()
        sys.exit()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    fc = fixed_cost()
    g = gspc_ibs()
    w = (g.index >= START) & (g.index < END) & g["sd"].notna().values
    x = g[w].copy()
    x["G"] = x["r"] / x["sd"]
    x["N"] = x["G"] - fc
    sig = (x["p_ibs"] < 0.2).values
    on, every = x.loc[sig, "N"].values, x["N"].values
    st = J.edge_stats(pd.DataFrame({"pnl": on}), n_boot=40_000)
    p_ex = bootstrap_excess(on, every)
    ex = on.mean() - every.mean()
    rep = bool(st["exp"] > 0 and st["p_pos"] >= 0.95 and ex > 0 and p_ex >= 0.90)
    print(f"PRIMARY  ^GSPC close->close {x.index[0].date()} .. {x.index[-1].date()} ({len(x)} days), cost {fc:.4f}R/trade")
    print(f"  IBS < 0.2 days: n={st['n']} mean {st['exp']:+.3f}R (before costs {x.loc[sig, 'G'].mean():+.3f}R)  "
          f"P(edge>0) {st['p_pos']:.4f}")
    print(f"  long every day {every.mean():+.3f}R -> excess {ex:+.3f}R  P(excess>0) {p_ex:.3f}")
    print(f"  => {'REPLICATES' if rep else 'does NOT replicate'} (rule: P(edge>0) >= 0.95 and P(excess>0) >= 0.90)")
    print("\nDescriptive only:")
    for lab, lo, hi in SUBS:
        m = (x.index >= lo) & (x.index <= hi)
        print(f"  {lab}: IBS < 0.2 n={int((m & sig).sum())} {x.loc[m & sig, 'N'].mean():+.3f}R vs every day "
              f"{x.loc[m, 'N'].mean():+.3f}R")
    print(f"  with Round 143's MES-at-index cost: {x.loc[sig, 'R'].mean():+.3f}R vs every day {x['R'].mean():+.3f}R")
    for lab, m in [("IBS < 0.1", x["p_ibs"] < 0.1), ("0.2-0.8", (x["p_ibs"] >= 0.2) & (x["p_ibs"] <= 0.8)),
                   ("IBS > 0.8", x["p_ibs"] > 0.8)]:
        print(f"  {lab}: n={int(m.sum())} {x.loc[m, 'N'].mean():+.3f}R")
    spy = spy_open_close()
    s_on = spy.loc[spy.index.isin(x.index[sig]), "R"]
    print(f"  SPY open->close 1993-2000 (MES-at-index cost): n={len(s_on)} {s_on.mean():+.3f}R vs every day "
          f"{spy['R'].mean():+.3f}R, P(excess>0) {bootstrap_excess(s_on.values, spy['R'].values):.3f}")

    row = dict(name="IBS < 0.2 long, 1990-2000 S&P 500 replication (R units)", n=st["n"], exp=st["exp"],
               exp_gross=float(x.loc[sig, "G"].mean()), p_pos=st["p_pos"], excess=ex, p_excess=p_ex,
               cost=fc, replicated=rep)
    line = (f"| {H.ledger_count() + 1} | 2026-09-26 | {row['name']} | Round 146 replication (pre-registered) | {commit} | "
            f"{row['n']} | {row['exp']:+.3f}R | {row['exp_gross']:+.3f}R | replication P {row['p_pos']:.3f}, "
            f"excess P {p_ex:.3f} | {'replicated lead' if rep else 'not replicated'} |")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    with open(os.path.join(H.HERE, "round146_results.json"), "w") as f:
        json.dump(row, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
