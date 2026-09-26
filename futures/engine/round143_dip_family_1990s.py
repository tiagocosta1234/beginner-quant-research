"""
Round 143: do the two surviving "buy equity weakness in an uptrend" leads hold on
data they have never seen? Pre-registered 2026-09-26, committed before any result
is run.

The leads (both found on futures data that starts 2000-10, both failed the ledger bar):
  D3  pre-holiday long (Round 135): long ES/NQ/YM/RTY 18:00 open -> settlement on
      the last trading day before a weekday market holiday. +0.063R, positive in all
      4 indices, beats long-every-day; flat before 2013.
  J3  Connors RSI(2) < 10 (Round 142): long when the 2-day RSI of the previous
      settlement is < 10 and that settlement is above its 200-day average; stay long
      day by day until a settlement closes above its 5-day average, or 10 days.
      +0.059R, positive 2000-12 and 2013-26 (P 0.92 / 0.93) and in all 4 indices.
Everything before 2000-10 is untouched by both.

Primary test, both leads: the S&P 500 index (Yahoo ^GSPC) close -> close,
1990-01-02 .. 2000-09-29 -- the full-day analog of the futures window (the prior
evening's reopen -> settlement). ^GSPC is used, not SPY, because Yahoo's SPY closes
are not dividend-adjusted: every quarterly ex-date shows a fake ~0.5% drop that
would fire RSI(2) and distort returns. (Changed from the approved plan, which said
SPY, for that reason -- before any result.) Timing:
  - pre-holiday is a calendar fact known days ahead, so entering at the prior close
    has no look-ahead;
  - Connors' signal is set by a close and entered at that close. S&P futures traded
    until 16:15 ET, so the entry was executable after the 16:00 print; the index's
    stale component prices bias close -> close *against* buying a down close (the
    stale close sits above fair value after a fall), so this is not flattering.
Units and costs: R = return / the 20-day SD of close -> close returns (prior days);
costs one MES contract (commission $1.22 + 2 ticks) at the index level.
Pre-holiday days are detected from the index's own trading calendar with batch D's
d3 rule (a weekday is skipped before the next trading day). The signals and the
Connors state machine run on the full ^GSPC history (200-day warm-up from 1989),
then the sample is cut to 1990-01-02 .. 2000-09-29.

Replication rule (fixed now, same as Round 140), per lead:
  (1) signal-day mean R > 0 with bootstrap P(edge>0) >= 0.95, AND
  (2) its excess over being long every day (same window, same units) > 0 with
      P(excess>0) >= 0.90.
A lead that passes is a "replicated lead", not a candidate: the ledger's bar is not
changed after the fact. It would justify forward paper-tracking, nothing more.

Power notes (from dry-run counts, before any result): 87 pre-holiday days and 422
Connors held days (120 episodes) in 2,717 index days. With R's SD near 1, a true
effect the size found on futures (+0.063R pre-holiday, +0.059R Connors) would reach
P(edge>0) >= 0.95 only about 15% of the time for pre-holiday and about 1 time in 3
for Connors. A miss is weak evidence against; a pass would be real support.
Dry-run checks: 1997-11-26, 1998-07-02 and 1994-04-26 (Nixon funeral closure) flagged,
1999-12-31 not (Jan 1, 2000 was a Saturday); RSI(2) on 1990-01-10 = 9.50, matching an
explicit loop; connors() with its new px argument left unset still gives Round 142's
2,357 held days.
Caveat on Connors: Connors & Alvarez built RSI(2) on US index/ETF data that
includes the 1990s, so this checks our futures finding, not their original claim.

Descriptive only (not in the verdict): sub-periods 1990-94 and 1995-2000; SPY
open -> close 1993-02 .. 2000-09 on the same signal days (the regular session
only, no overnight; signals still from ^GSPC closes; SPY days with open == close
dropped), against SPY long-every-day.
2 ledger variants (k=155 -> 157).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round122b_tom_long_history import load_daily
from round140_vix_spike_1990s import MES_COST, bootstrap_excess
from round142_batch_j import connors

START, END = pd.Timestamp("1990-01-01"), pd.Timestamp("2000-10-01")
SUBS = [("1990-94", "1990", "1994-12-31"), ("1995-2000", "1995", "2000-09-30")]


def index_frame():
    g = load_daily("^GSPC")[["close"]].copy()
    g["prev"] = g["close"].shift(1)
    g["r"] = np.log(g["close"] / g["prev"])
    g["sd"] = g["r"].shift(1).rolling(20).std()
    g["cost_r"] = MES_COST / (g["sd"] * g["prev"] * H.PV["MES"])
    g["R"] = g["r"] / g["sd"] - g["cost_r"]
    return g


def pre_holiday(idx):
    """batch D's d3 rule on a trading calendar: the next trading day skips >= 1 weekday."""
    nxt = pd.Series(idx[1:], index=idx[:-1])
    pre = {d for d, n in nxt.items() if np.busday_count(d.date() + pd.Timedelta(days=1), n.date()) >= 1}
    return pd.Series(idx.isin(list(pre)), index=idx)


def signals(g):
    return {"pre-holiday": pre_holiday(g.index),
            "Connors RSI(2) < 10": connors(g, 10, px=g["close"]).astype(bool)}


def spy_open_close():
    s = load_daily("SPY")
    s = s[(s.index < END) & (s["open"] != s["close"])].copy()
    s["r"] = np.log(s["close"] / s["open"])
    s["sd"] = s["r"].shift(1).rolling(20).std()
    s = s[s["sd"] > 0]
    s["cost_r"] = MES_COST / (s["sd"] * s["open"] * 10 * H.PV["MES"])
    s["R"] = s["r"] / s["sd"] - s["cost_r"]
    return s


def dry_run():
    g = index_frame()
    sig = signals(g)
    w = (g.index >= START) & (g.index < END) & g["sd"].notna().values
    print(f"sample {g.index[w][0].date()} .. {g.index[w][-1].date()}: {w.sum()} days")
    ph = g.index[w & sig["pre-holiday"].values]
    print(f"pre-holiday days: {len(ph)}")
    print("  ", " ".join(str(d.date()) for d in ph))
    for d, want in [("1997-11-26", True), ("1998-07-02", True), ("1999-12-31", False), ("1994-04-26", True)]:
        print(f"   {d} flagged={pd.Timestamp(d) in set(ph)} (expected {want})")
    c = sig["Connors RSI(2) < 10"]
    held = g.index[w & c.values]
    entries = held[~c.shift(1, fill_value=False).reindex(held).values]
    print(f"Connors held days: {len(held)} in {len(entries)} episodes; first entries "
          f"{', '.join(str(d.date()) for d in entries[:4])}")
    from round142_batch_j import rsi2
    r = rsi2(g["close"])
    d0 = entries[0]
    i = g.index.get_loc(d0) - 1
    cl = g["close"].iloc[i - 3:i + 1]
    print(f"   RSI(2) check at {g.index[i].date()}: closes {np.round(cl.values, 2)} -> RSI {r.iloc[i]:.2f}; "
          f"close {g['close'].iloc[i]:.2f} vs 200-day {g['close'].rolling(200).mean().iloc[i]:.2f}")
    s = spy_open_close()
    print(f"SPY open->close descriptive: {len(s)} days, pre-holiday {s.index.isin(ph).sum()}, "
          f"Connors {s.index.isin(held).sum()}")


def post_hoc():
    """Added AFTER the results (descriptive, not part of any verdict): the same days
    before costs. A fixed per-contract cost is 3-7x larger in R on a 1990s index level
    (300-1,500) than on the futures sample, which the pre-registered rule did not adjust for."""
    import round135_batch_d as D
    g = index_frame()
    w = (g.index >= START) & (g.index < END) & g["sd"].notna().values
    g["G"] = g["r"] / g["sd"]
    every = g.loc[w, "G"].values
    es = D.market_frame("ES=F")
    print(f"median cost per trade: index 1990-94 {g.loc[w & (g.index < '1995'), 'cost_r'].median():.3f}R, "
          f"1995-2000 {g.loc[w & (g.index >= '1995'), 'cost_r'].median():.3f}R | ES futures 2000-12 "
          f"{es.loc[es.index < '2013', 'cost_r'].median():.3f}R, 2013-26 {es.loc[es.index >= '2013', 'cost_r'].median():.3f}R")
    for name, flag in signals(g).items():
        on = g.loc[w & flag.values, "G"].values
        st = J.edge_stats(pd.DataFrame({"pnl": on}), n_boot=40_000)
        print(f"{name}: before costs {st['exp']:+.3f}R P(>0) {st['p_pos']:.4f} | every day {every.mean():+.3f}R | "
              f"excess {on.mean() - every.mean():+.3f}R P(excess>0) {bootstrap_excess(on, every):.3f}")
        for lab, lo, hi in SUBS:
            m = (g.index >= lo) & (g.index <= hi) & w
            print(f"   {lab}: {g.loc[m & flag.values, 'G'].mean():+.3f}R vs every day {g.loc[m, 'G'].mean():+.3f}R")


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        dry_run()
        sys.exit()
    if "--post-hoc" in sys.argv:
        post_hoc()
        sys.exit()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    g = index_frame()
    w = (g.index >= START) & (g.index < END) & g["sd"].notna().values
    sig = signals(g)
    spy = spy_open_close()
    every = g.loc[w, "R"].values
    rows = []
    for name, flag in sig.items():
        on = g.loc[w & flag.values, "R"].values
        st = J.edge_stats(pd.DataFrame({"pnl": on}), n_boot=40_000)
        gross = (g.loc[w & flag.values, "r"] / g.loc[w & flag.values, "sd"]).mean()
        p_ex = bootstrap_excess(on, every)
        ex = on.mean() - every.mean()
        rep = bool(st["exp"] > 0 and st["p_pos"] >= 0.95 and ex > 0 and p_ex >= 0.90)
        print(f"\n{name}: ^GSPC close->close {g.index[w][0].date()} .. {g.index[w][-1].date()}")
        print(f"  signal days n={st['n']} mean {st['exp']:+.3f}R (gross {gross:+.3f}R)  P(edge>0) {st['p_pos']:.4f}")
        print(f"  long every day {every.mean():+.3f}R -> excess {ex:+.3f}R  P(excess>0) {p_ex:.3f}")
        for lab, lo, hi in SUBS:
            m = (g.index >= lo) & (g.index <= hi) & w
            print(f"    {lab}: signal n={int((m & flag.values).sum())} {g.loc[m & flag.values, 'R'].mean():+.3f}R "
                  f"vs every day {g.loc[m, 'R'].mean():+.3f}R")
        sd_on = spy.loc[spy.index.isin(g.index[w & flag.values]), "R"]
        print(f"    descriptive SPY open->close 1993-2000: signal n={len(sd_on)} {sd_on.mean():+.3f}R vs every day "
              f"{spy['R'].mean():+.3f}R, P(excess>0) {bootstrap_excess(sd_on.values, spy['R'].values):.3f}")
        print(f"  => {'REPLICATES' if rep else 'does NOT replicate'} (rule: P(edge>0) >= 0.95 and P(excess>0) >= 0.90)")
        rows.append(dict(name=f"{name} long, 1990-2000 S&P 500 replication (R units)", n=st["n"], exp=st["exp"],
                         exp_gross=float(gross), p_pos=st["p_pos"], excess=ex, p_excess=p_ex, replicated=rep))

    lines = [f"| {n} | 2026-09-26 | {r['name']} | Round 143 replication (pre-registered) | {commit} | {r['n']} "
             f"| {r['exp']:+.3f}R | {r['exp_gross']:+.3f}R | replication P {r['p_pos']:.3f}, excess P {r['p_excess']:.3f} | "
             f"{'replicated lead' if r['replicated'] else 'not replicated'} |"
             for n, r in enumerate(rows, start=H.ledger_count() + 1)]
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round143_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
