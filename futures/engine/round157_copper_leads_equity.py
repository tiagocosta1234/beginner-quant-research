"""
Round 157: a fourth new mechanism today. Checked against `IDEA_LEDGER.md`
first (k=198) -- HG=F (copper) has never appeared in any test in this
ledger. "Dr. Copper" is a real, decades-old market narrative: copper demand
tracks industrial activity and global growth expectations, so copper is
widely used as a leading indicator for the broader economy and, by
extension, equities. Different channel again from Round 154 (crypto,
risk-sentiment) and Round 155 (dollar, currency-denomination): this one is
a GROWTH-EXPECTATIONS/fundamental-leading-indicator story, not a
sentiment-correlation or mechanical-pricing one.

Step 0, honest before running: like Rounds 154/155, this is a roughly-daily
(not high-frequency) cross-asset signal, and both of those failed. "Dr.
Copper" is also a widely known, often-repeated narrative -- if it were a
clean, exploitable lead-lag, it's exactly the kind of thing that would have
been arbitraged away already. Tested for the different economic channel,
not because prior odds have improved.

Rule: sign of copper's (HG=F) prior-day open->close return, filtered to
|r| >= 0.5 x its 20-day SD (same convention as Rounds 142/154/155). Trades
ES/NQ/YM/RTY open->close the SAME direction next session (copper up ->
growth optimism -> equities up). `round135_batch_d`'s
market_frame/trades_from/judge_variant-style stats, standard 2013/2020
splits (HG=F's own quality filter drops 2000-04, 2009-10 and 2026, per
Knowledge_Base/CURRENT_STATE.md's own gotcha note -- confirmed directly:
usable range is 2005-02-01 .. 2025-12-31).

1 variant. Ledger k=198 -> 199; OOS bar 1 - 0.01/199.

Candidate: net AND before-cost mean R > 0; IS P(edge>0) >= 0.95 (pre-2013);
OOS P(edge>0) >= the k=199 bar (2013-26); positive on at least 3 of 4
equity markets (same cross-market consistency check as Round 154).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
import round135_batch_d as D

NAME = "Copper (HG) prior-day move -> same-direction ES/NQ/YM/RTY open->close (Dr. Copper)"
GAP_Z = 0.5
OOS_START = pd.Timestamp("2013-01-01")
FINAL_START = pd.Timestamp("2020-01-01")


def copper_signal():
    hg = D.market_frame("HG=F")
    r_prev = hg["r"].shift(1)
    big = r_prev.abs() >= GAP_Z * hg["sd"]
    sig = pd.Series(np.where(big, np.sign(r_prev), 0), index=hg.index).fillna(0)
    return sig[sig != 0]


def build_trades(dry_run=False):
    sig = copper_signal()
    if dry_run:
        return sig, None
    out = []
    for sym in D.EQUITY:
        frame = D.market_frame(sym)
        direction = sig.reindex(frame.index).fillna(0)
        out.append(D.trades_from(frame, direction, sym))
    return sig, pd.concat(out, ignore_index=True)


def judge(tr, k):
    st = lambda x: J.edge_stats(x, n_boot=40_000) if len(x) else dict(n=0, exp=np.nan, p_pos=np.nan)
    a, i, o = st(tr), st(tr[tr["date"] < OOS_START]), st(tr[tr["date"] >= OOS_START])
    f20 = st(tr[tr["date"] >= FINAL_START])
    per = tr.groupby("market")["pnl"].mean()
    bar = H.oos_bar(k)
    n_pos = int((per > 0).sum())
    daily = tr.groupby("date")["pnl"].sum()
    cand = bool(a["exp"] > 0 and tr["gross"].mean() > 0 and i["p_pos"] >= 0.95 and o["p_pos"] >= bar and n_pos >= 3)
    print(f"  {NAME:<62} n={a['n']:>5} mean {a['exp']:+.3f}R (gross {tr['gross'].mean():+.3f}R) | "
          f"IS(<2013) {i['exp']:+.3f}R P {i['p_pos']:.3f} | OOS(>=2013) {o['exp']:+.3f}R P {o['p_pos']:.4f} "
          f"(bar {bar:.5f}) | 2020-26 {f20['exp']:+.3f}R | "
          f"{', '.join(f'{m} {v:+.3f}' for m, v in per.items())} ({n_pos}/4 positive) | "
          f"Sharpe/day {daily.mean() / daily.std():+.3f} | {'CANDIDATE' if cand else 'no'}", flush=True)
    return dict(name=NAME, n=a["n"], exp=a["exp"], exp_gross=float(tr["gross"].mean()), p_is=i["p_pos"],
                p_oos=o["p_pos"], exp_is=i["exp"], exp_oos=o["exp"], exp_2020_26=f20["exp"], k=k, bar=bar,
                per_market={m: float(v) for m, v in per.items()}, n_markets_positive=n_pos,
                trade_sharpe_daily=float(daily.mean() / daily.std()) if daily.std() > 0 else np.nan, candidate=cand)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    k = H.ledger_count() + 1
    print(f"k = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)

    sig, tr = build_trades(dry_run=dry)
    if dry:
        print(f"Copper qualifying days (|prior r|>={GAP_Z}xSD): {len(sig)}")
        print(f"  first: {sig.index.min()}  last: {sig.index.max()}")
        print(f"  long days: {(sig > 0).sum()}  short days: {(sig < 0).sum()}")
        span_years = (sig.index.max() - sig.index.min()).days / 365.25
        print(f"  ~{len(sig) / span_years:.1f} qualifying days per year")
        print("\n--dry-run: counts only, no P&L. Hand-check a few signals before running for real.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    r = judge(tr, k)
    lines = H.ledger_rows([r], "Round 157 (pre-registered, new idea class: Dr. Copper as a growth-expectations leader)",
                           commit, date="2026-09-27")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round157_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
