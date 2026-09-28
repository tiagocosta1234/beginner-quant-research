"""
Round 182: a seventh cross-asset lead. Checked IDEA_LEDGER.md first (k=300):
crypto (154), dollar (155), copper (157/158), rates (162), and oil (164)
have all been tested as leads for equities -- gold itself never has. GC's
OWN price patterns have been tested extensively (ORB, POC reversion, gap,
harmonic patterns), but never as a LEADING indicator for something else.
"Gold as a fear gauge": gold is the classic flight-to-safety asset --
rising gold on a given day is commonly read as rising risk-aversion, which
should predict equities falling the next session. Different channel again
from every other lead tried: not sentiment-correlation (crypto), currency-
mechanics (dollar), growth-expectations (copper), discount-rate (rates),
or cost-push (oil) -- this is a genuine flight-to-safety/risk-aversion
story, the most commonly cited one in financial media for gold specifically.

Step 0, honest before running: a seventh same-shaped test after 0/6 cross-
asset leads (Round 158's copper fade is the same family, an inversion of
157, not a new base hypothesis). Gold-equity co-movement is discussed
constantly in financial media -- if a clean daily lead-lag existed, it
would likely be arbitraged away already, same caveat as every other lead
in this batch. Tested for the flight-to-safety channel specifically, not
because prior odds have improved from 0/6.

Rule, identical convention to Rounds 142/154/155/157/162/164: sign of GC's
prior-day open->close return, filtered to |r| >= 0.5x its own 20-day SD,
predicts the OPPOSITE-direction next-session open->close return on
ES/NQ/YM/RTY (gold up -> flight to safety -> equities down). round135_batch_d's
market_frame/trades_from/edge_stats machinery, unmodified.

1 variant. Ledger k=300 -> 301; OOS bar 1 - 0.01/301.

Candidate: net AND before-cost mean R > 0; IS P(edge>0) >= 0.95 (pre-2013);
OOS P(edge>0) >= the k=301 bar (2013-26); positive on at least 3 of 4 equity
markets (same cross-market consistency check as every prior lead in this batch).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
import round135_batch_d as D

NAME = "Gold (GC) prior-day move -> OPPOSITE-direction ES/NQ/YM/RTY open->close (flight-to-safety channel)"
GAP_Z = 0.5
OOS_START = pd.Timestamp("2013-01-01")
FINAL_START = pd.Timestamp("2020-01-01")


def gold_signal():
    gc = D.market_frame("GC=F")
    r_prev = gc["r"].shift(1)
    big = r_prev.abs() >= GAP_Z * gc["sd"]
    sig = pd.Series(np.where(big, -np.sign(r_prev), 0), index=gc.index).fillna(0)  # opposite direction
    return sig[sig != 0]


def build_trades(dry_run=False):
    sig = gold_signal()
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
    print(f"  {NAME:<75} n={a['n']:>5} mean {a['exp']:+.3f}R (gross {tr['gross'].mean():+.3f}R) | "
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
        print(f"GC qualifying days (|prior r|>={GAP_Z}xSD): {len(sig)}")
        print(f"  first: {sig.index.min()}  last: {sig.index.max()}")
        print(f"  fade-long(gold fell) days: {(sig > 0).sum()}  fade-short(gold rose) days: {(sig < 0).sum()}")
        span_years = (sig.index.max() - sig.index.min()).days / 365.25
        print(f"  ~{len(sig) / span_years:.1f} qualifying days per year")
        print("\n--dry-run: counts only, no P&L. Hand-check a few signals before running for real.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    r = judge(tr, k)
    lines = H.ledger_rows([r], "Round 182 (pre-registered, new idea class: gold as a flight-to-safety leader)",
                           commit, date="2026-09-28")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round182_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
