"""
Round 162: "keep testing new idea classes." Checked IDEA_LEDGER.md first
(k=218) -- ZN=F (10-Year Treasury note futures) has never appeared in any
test in this ledger, even though it's already loaded by round135_batch_d
(MARKETS/PV/TK all defined for it; only ever used there for its OWN
time-series momentum, never as a cross-asset lead for something else).

A fifth new mechanism, distinct from the four already tried this campaign
(Rounds 154 crypto/sentiment, 155 dollar/currency-mechanics, 157/158
copper/growth-expectations): the DISCOUNT-RATE channel. Falling yields
(rising bond prices) lower the rate used to discount future corporate
earnings, which is one of the most commonly cited drivers of equity
valuations -- "bad news is good news" / risk-on-risk-off commentary leans on
this constantly. But it's a real two-sided hypothesis, not a one-way bet:
falling yields can also mean investors are fleeing to safety on a growth
scare (flight-to-quality), which would make bonds lead equities the OPPOSITE
way -- exactly the pattern Rounds 154 (crypto) and 157 (copper) actually
found once tested (both leaned toward the opposite of their pre-registered
co-movement story). Pre-registering the discount-rate (co-movement) direction
here, same as those two did, and letting the data show which channel wins.

Step 0, honest before running: like every cross-asset test this campaign has
run (Rounds 139, 154, 155, 157), this is a roughly-daily, not high-frequency,
signal, and none of the prior four passed the pass-speed gate even before
the significance bar. Bond-equity co-movement is also one of the most
discussed cross-asset relationships in finance -- if a clean daily lead-lag
existed, it would be arbitraged away already. Tested for a new, distinct
transmission channel, not because prior odds have improved from 0/4.

Rule, identical convention to Rounds 142/154/155/157: sign of ZN's prior-day
open->close return, filtered to |r| >= 0.5x its own 20-day SD (only
meaningfully large rate moves), predicts the SAME-direction next-session
open->close return on ES/NQ/YM/RTY (rates up/yields down -> equities up).
`round135_batch_d`'s market_frame/trades_from/edge_stats machinery, reused
unmodified; ZN's PV/TK were already added there (Round 135) and never used
outside that file's own momentum test.

1 variant. Ledger k=218 -> 219; OOS bar 1 - 0.01/219 = 0.999954.

Candidate: net AND before-cost mean R > 0; IS P(edge>0) >= 0.95 (pre-2013);
OOS P(edge>0) >= the k=219 bar (2013-26); positive on at least 3 of 4 equity
markets (same cross-market consistency check as Rounds 154/157).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
import round135_batch_d as D

NAME = "10Y note (ZN) prior-day move -> same-direction ES/NQ/YM/RTY open->close (discount-rate channel)"
GAP_Z = 0.5
OOS_START = pd.Timestamp("2013-01-01")
FINAL_START = pd.Timestamp("2020-01-01")


def rates_signal():
    zn = D.market_frame("ZN=F")
    r_prev = zn["r"].shift(1)
    big = r_prev.abs() >= GAP_Z * zn["sd"]
    sig = pd.Series(np.where(big, np.sign(r_prev), 0), index=zn.index).fillna(0)
    return sig[sig != 0]


def build_trades(dry_run=False):
    sig = rates_signal()
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
    print(f"  {NAME:<70} n={a['n']:>5} mean {a['exp']:+.3f}R (gross {tr['gross'].mean():+.3f}R) | "
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
        print(f"ZN qualifying days (|prior r|>={GAP_Z}xSD): {len(sig)}")
        print(f"  first: {sig.index.min()}  last: {sig.index.max()}")
        print(f"  long(rates up) days: {(sig > 0).sum()}  short(rates down) days: {(sig < 0).sum()}")
        span_years = (sig.index.max() - sig.index.min()).days / 365.25
        print(f"  ~{len(sig) / span_years:.1f} qualifying days per year")
        print("\n--dry-run: counts only, no P&L. Hand-check a few signals before running for real.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    r = judge(tr, k)
    lines = H.ledger_rows([r], "Round 162 (pre-registered, new idea class: rates/discount-rate channel leading equities)",
                           commit, date="2026-09-27")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round162_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
