"""
Round 135, batch D: 25 years of daily futures, inside Broker's trading day.
Pre-registered 2026-09-26 -- rules, variants and verdict rules committed before
any result is run.

Why daily data now: our intraday files cover 3.8 years, too short to confirm a
modest edge. Yahoo daily futures bars go back to 2000, and their open is exactly
the 18:00 ET Globex reopen (checked against the hourly bars: 0.0000% median gap)
while the close is the settlement (ES: 16:00 ET, 0.015% from the hourly 16:00
close; metals and energy settle earlier). Broker's trading day runs 18:00 ->
16:10 ET, so a trade from the daily open to the daily close is a LEGAL hold --
unlike the RTH-close -> next-open holds that inflated Rounds 69-119.

Markets (10, each tradable on Broker; micro where one exists): ES, NQ, YM, RTY
(from 2017), GC, SI, CL, HG, 6E, ZN. Data: round122b.load_daily (open/close).

Units: every trade is measured in risk units R = the market's 20-day standard
deviation of open->close log returns (known before the day) -- an equal-risk
portfolio. Cost per trade in R = (commission + 2 ticks) per contract divided by
one contract's dollar SD (the micro's point value; fractional sizing assumed, so
markets whose single micro exceeds the risk budget are slightly understated).
Days whose open->close move exceeds 10 SD are dropped as bad prints. Data quality
rule (found in the dry run, fixed before any result): days with open == close (a
missing open) are dropped, and so is every market-year with more than 5% of them --
this leaves silver (SI) only 2011 (222 days), gold 13 clean years from 2008,
copper from 2005.

Hypotheses (published evidence, fixed parameters):
 D1  Time-series momentum (Moskowitz, Ooi & Pedersen 2012), applied to the legal
     window: each day, go long if the sum of the previous N days' open->close log
     returns is positive, short if negative; enter at the open, exit at the close.
     All 10 markets. Variants: N in {20, 120, 250}.
 D2  Short-term reversal in equity index futures: if yesterday's open->close
     return was <= -z SD, go long today open->close; if >= +z SD, go short.
     ES, NQ, YM, RTY. Variants: z in {1.0, 1.5}.
 D3  Pre-holiday effect (Ariel 1990): long open->close on the last trading day
     before a US market holiday (a weekday with no NYSE session, from SPY's
     trading dates). ES, NQ, YM, RTY. 1 variant.

Periods: discovery 2000-2012 ("IS"), confirmation 2013-2026-09 ("OOS"), and the
final stretch 2020-2026 on its own.
Candidate (6 variants take the ledger from k=126 to k=132): net and before-cost
mean R > 0 overall; IS P(edge>0) >= 0.95; OOS P(edge>0) >= 1 - 0.01/132; AND the
2020-2026 mean R > 0. Only a candidate goes on to the exact 18:00 -> 16:00
legal-window check on the hourly and 1-minute data and then the goal judge.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round122b_tom_long_history import load_daily

H.PV.update({"MHG": 2500.0, "M6E": 12500.0, "ZN": 1000.0})
H.TK.update({"MHG": 0.0005, "M6E": 0.0001, "ZN": 1 / 64})
MARKETS = {"ES=F": "MES", "NQ=F": "MNQ", "YM=F": "MYM", "RTY=F": "M2K", "GC=F": "MGC",
           "SI=F": "SIL", "CL=F": "MCL", "HG=F": "MHG", "6E=F": "M6E", "ZN=F": "ZN"}
EQUITY = ["ES=F", "NQ=F", "YM=F", "RTY=F"]
IS_END, FINAL_START = pd.Timestamp("2013-01-01"), pd.Timestamp("2020-01-01")
N_VARIANTS = 6


def market_frame(sym):
    d = load_daily(sym)
    d = d[(d["open"] > 0) & (d["close"] > 0)].copy()
    # data quality (fixed before any result): Yahoo's daily futures have days with a
    # missing open (open == close). Drop those days, and drop every market-year in
    # which more than 5% of days are like that (SI all but 2011; GC 2000-2010 and some
    # later years; HG 2000-04, 2009-10, 2026; 6E 2000).
    stale = d["open"] == d["close"]
    bad_years = stale.groupby(d.index.year).mean()
    bad_years = set(bad_years[bad_years > 0.05].index)
    d = d[~stale & ~d.index.year.isin(bad_years)].copy()
    d["r"] = np.log(d["close"] / d["open"])
    d["sd"] = d["r"].shift(1).rolling(20).std()
    d = d[~(d["r"].abs() > 10 * d["sd"])]  # bad prints
    d["sd"] = d["r"].shift(1).rolling(20).std()
    d = d[d["sd"] > 0]
    micro = MARKETS[sym]
    d["cost_r"] = H.cost_per_contract(micro) / (d["sd"] * d["open"] * H.PV[micro])
    return d.dropna(subset=["sd"])


def trades_from(d, direction, sym):
    t = d[direction != 0].copy()
    dd = direction[direction != 0]
    gross = dd * t["r"] / t["sd"]
    return pd.DataFrame({"date": t.index, "market": sym, "gross": gross.values,
                         "pnl": (gross - t["cost_r"]).values})


def d1(frames, n):
    out = []
    for sym, d in frames.items():
        trend = d["r"].shift(1).rolling(n, min_periods=int(0.9 * n)).sum()
        out.append(trades_from(d, np.sign(trend).fillna(0), sym))
    return pd.concat(out, ignore_index=True)


def d2(frames, z):
    out = []
    for sym in EQUITY:
        d = frames[sym]
        x = (d["r"] / d["sd"]).shift(1)
        out.append(trades_from(d, pd.Series(np.where(x <= -z, 1, np.where(x >= z, -1, 0)), index=d.index), sym))
    return pd.concat(out, ignore_index=True)


def d3(frames):
    nyse = load_daily("SPY").index
    nxt = pd.Series(nyse[1:], index=nyse[:-1])
    pre = {day for day, n in nxt.items() if np.busday_count(day.date() + pd.Timedelta(days=1), n.date()) >= 1}
    out = []
    for sym in EQUITY:
        d = frames[sym]
        out.append(trades_from(d, pd.Series(np.where(d.index.isin(list(pre)), 1, 0), index=d.index), sym))
    return pd.concat(out, ignore_index=True)


def judge_variant(name, tr, k):
    st = lambda x: J.edge_stats(x, n_boot=40_000) if len(x) else dict(n=0, exp=np.nan, p_pos=np.nan)
    a, i, o, f = st(tr), st(tr[tr["date"] < IS_END]), st(tr[tr["date"] >= IS_END]), st(tr[tr["date"] >= FINAL_START])
    daily = tr.groupby("date")["pnl"].sum()
    bar = H.oos_bar(k)
    cand = bool(a["exp"] > 0 and tr["gross"].mean() > 0 and i["p_pos"] >= 0.95 and o["p_pos"] >= bar and f["exp"] > 0)
    print(f"  {name:<46} n={a['n']:>6} mean {a['exp']:+.3f}R (gross {tr['gross'].mean():+.3f}R) | "
          f"2000-12 {i['exp']:+.3f}R P {i['p_pos']:.3f} | 2013-26 {o['exp']:+.3f}R P {o['p_pos']:.5f} (bar {bar:.5f}) | "
          f"2020-26 {f['exp']:+.3f}R | portfolio Sharpe/day {daily.mean() / daily.std():+.3f} | "
          f"{'CANDIDATE' if cand else 'no'}", flush=True)
    per = tr.groupby("market")["pnl"].agg(["count", "mean"])
    print("      by market: " + ", ".join(f"{m} {r['mean']:+.3f}" for m, r in per.iterrows()))
    return dict(name=name, n=a["n"], exp=a["exp"], exp_gross=float(tr["gross"].mean()), p_is=i["p_pos"],
                p_oos=o["p_pos"], exp_is=i["exp"], exp_oos=o["exp"], exp_final=f["exp"], k=k, bar=bar,
                sharpe=float(daily.mean() / daily.std()), candidate=cand)


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + N_VARIANTS
    frames = {s: market_frame(s) for s in MARKETS}
    for s, d in frames.items():
        print(f"{s:<6} {d.index[0].date()}..{d.index[-1].date()} days={len(d)} median cost {d['cost_r'].median():.3f}R")
    print(f"\nk after batch D = {k}; OOS bar {H.oos_bar(k):.5f}\n")
    rows = []
    print("D1 time-series momentum, open->close, 10 markets")
    for n in [20, 120, 250]:
        rows.append(judge_variant(f"D1 TSMOM {n}-day, 10 markets", d1(frames, n), k))
    print("\nD2 short-term reversal, equity indices")
    for z in [1.0, 1.5]:
        rows.append(judge_variant(f"D2 reversal after a {z} SD day, 4 indices", d2(frames, z), k))
    print("\nD3 pre-holiday long, equity indices")
    rows.append(judge_variant("D3 pre-holiday long, 4 indices", d3(frames), k))

    lines = [f"| {n} | 2026-09-26 | {r['name']} (R units) | Round 135 batch D (pre-registered) | {commit} | {r['n']} "
             f"| {r['exp']:+.3f}R | {r['exp_gross']:+.3f}R | {r['p_is']:.2f} / {r['p_oos']:.3f} | "
             f"{'CANDIDATE' if r['candidate'] else 'no edge'} |" for n, r in enumerate(rows, start=H.ledger_count() + 1)]
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round135_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()} ====")
