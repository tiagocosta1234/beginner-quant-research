"""
Round 164: a sixth cross-asset lead. Checked IDEA_LEDGER.md first (k=221) --
CL=F (WTI crude oil futures) has been loaded by round135_batch_d since Round
135 (its own time-series momentum) but never used as a lead for anything
else, and never checked for data quality the way HG/SI/GC/6E were -- verified
directly before building this round: CL=F has clean, complete coverage
2000-09-22 through 2026-09-21 (~250 days/year, no bad-year gaps), so unlike
SI=F (usable only in 2011, per this repo's own documented gotcha) this one
isn't a landmine.

Sixth distinct mechanism this campaign has tried (after crypto/sentiment,
dollar/currency-mechanics, copper/growth-expectations, rates/discount-rate,
all 0/5): the COST-PUSH / inflation-expectations channel. Rising oil prices
raise input costs and headline inflation expectations, which is commonly
cited as a drag on equities (higher costs, tighter Fed policy) -- the
opposite-sign hypothesis from copper's "rising copper = more growth, good
for stocks" story, even though both are commodities. Real ambiguity going
in: oil can also rise WITH growth optimism (demand-driven rallies), which
would push it the same direction as equities instead.

Step 0, honest before running: a sixth same-shaped test after 0/5 cross-asset
leads. Oil-equity co-movement is also widely discussed (oil price shocks and
recessions, 1970s-2008), so if a clean daily lead-lag existed, it would very
likely already be arbitraged away. Tested for the cost-push channel
specifically -- not because prior odds have improved.

Rule, identical convention to Rounds 142/154/155/157/162: sign of CL's
prior-day open->close return, filtered to |r| >= 0.5x its own 20-day SD,
predicts the OPPOSITE-direction next-session open->close return on
ES/NQ/YM/RTY (oil up -> cost-push/inflation drag -> equities down). Note the
sign flip from Rounds 154/155/157/162 (which all pre-registered SAME-
direction co-movement) -- this is the one cross-asset story in this batch
where the commonly-cited mechanism is itself a FADE, not a co-movement, so
the opposite sign is what's actually being pre-registered as "the
hypothesis", not an inversion of a prior result.

1 variant. Ledger k=221 -> 222; OOS bar 1 - 0.01/222 = 0.999955.

Candidate: net AND before-cost mean R > 0; IS P(edge>0) >= 0.95 (pre-2013);
OOS P(edge>0) >= the k=222 bar (2013-26); positive on at least 3 of 4 equity
markets (same cross-market consistency check as Rounds 154/157/162).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
import round135_batch_d as D

NAME = "Crude oil (CL) prior-day move -> OPPOSITE-direction ES/NQ/YM/RTY open->close (cost-push channel)"
GAP_Z = 0.5
OOS_START = pd.Timestamp("2013-01-01")
FINAL_START = pd.Timestamp("2020-01-01")


def oil_signal():
    cl = D.market_frame("CL=F")
    r_prev = cl["r"].shift(1)
    big = r_prev.abs() >= GAP_Z * cl["sd"]
    sig = pd.Series(np.where(big, -np.sign(r_prev), 0), index=cl.index).fillna(0)  # opposite direction
    return sig[sig != 0]


def build_trades(dry_run=False):
    sig = oil_signal()
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
        print(f"CL qualifying days (|prior r|>={GAP_Z}xSD): {len(sig)}")
        print(f"  first: {sig.index.min()}  last: {sig.index.max()}")
        print(f"  fade-long(oil fell) days: {(sig > 0).sum()}  fade-short(oil rose) days: {(sig < 0).sum()}")
        span_years = (sig.index.max() - sig.index.min()).days / 365.25
        print(f"  ~{len(sig) / span_years:.1f} qualifying days per year")
        print("\n--dry-run: counts only, no P&L. Hand-check a few signals before running for real.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    r = judge(tr, k)
    lines = H.ledger_rows([r], "Round 164 (pre-registered, new idea class: oil cost-push channel leading equities)",
                           commit, date="2026-09-27")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round164_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
