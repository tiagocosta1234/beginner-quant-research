"""
Round 154: a genuinely new idea class, not a re-skin of anything in the ledger
(k=195 as of this pre-registration). the trader: "keep testing new idea classes."
Checked against `IDEA_LEDGER.md`/`CURRENT_STATE.md` first so this isn't a
duplicate: Round 142's J1 tested whether CRYPTO'S OWN weekend gap fills (it
does -- fading it loses); Round 139/142's H2a/H2b tested crypto's own
momentum. Nothing has tested crypto as a LEADING indicator for something
else. That's the idea here.

Rationale, stated before any result: CME Bitcoin futures (BTC=F) trade
through the weekend while equity index futures effectively don't (Friday's
session ends near 17:00 ET, Sunday's opens 18:00 ET); a real weekend move in
crypto is therefore fresh, real information equity futures haven't priced in
yet when they reopen. Since roughly 2022's rate-hiking regime, crypto and
tech-heavy equities have been repeatedly reported as moving on the same
risk-appetite factor (both sell off together in tightening/de-risking
episodes). The pre-registered hypothesis is CO-MOVEMENT (trade the equity
index the SAME direction as BTC's weekend gap), not a fade -- that is the
economically motivated direction; if this fails, a mirror inversion is a
separate, later, honestly-labeled test (as Round 152 did for Q3), not
silently tried here too.

Step 0, pass-speed gate, stated honestly before running: a weekend gap this
size and filter (see below) fires at most once a week. Every other roughly-
weekly signal in this ledger (VIX spike/backwardation, Treasury auctions,
FOMC days) has landed at a daily Sharpe of 0.02-0.15, far under the ~0.5 the
gate needs. There's no reason to expect this one to be structurally
different in kind -- it's tested because it's a new mechanism (information
transfer from a 24/7 market to a session-bound one), not because its
plausible size looks better than the leads already measured.

Rule: reuses `round142_batch_j.with_prev_close`'s exact weekend-gap
definition -- gap = log(open / previous close), only on the first session
after a break of >= 2 calendar days, filtered to |gap| >= 0.5 x the 20-day
SD of open->close returns (Round 142's own GAP_Z). Computed on BTC=F only
(ETH=F is a second, smaller-cap coin -- correlated with BTC itself, not an
independent second observation of "crypto's weekend move", so it is not
pooled in here the way H2a pooled BTC+ETH's OWN momentum). On the SAME
calendar day, trade ES=F, NQ=F, YM=F, RTY=F open->close in BTC's gap
direction, `round135_batch_d.market_frame`/`trades_from` for R-units and
real costs.

Split: BTC=F data starts 2017-12-18. IS = 2017-12-18..2022-12-31 (pre the
regime this hypothesis is actually about); OOS = 2023-01-01 onward (matching
H2a's own crypto-era split). A 2020-26-only mean is also reported the way
every batch-D-family round does.

1 variant. Ledger k=195 -> 196; OOS bar 1 - 0.01/196.

Candidate: net AND before-cost mean R > 0; IS P(edge>0) >= 0.95 (2017-22);
OOS P(edge>0) >= the k=196 bar (2023-26); positive on at least 3 of the 4
equity markets (a 4-market analogue of J1/J2's "positive on both legs").
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
import round135_batch_d as D
import round139_batch_h as HH
from round142_batch_j import with_prev_close, GAP_Z

NAME = "BTC weekend gap -> same-direction ES/NQ/YM/RTY open->close (co-movement)"
IS_END, OOS_START = pd.Timestamp("2017-12-18"), pd.Timestamp("2023-01-01")
FINAL_START = pd.Timestamp("2020-01-01")


def btc_weekend_signal():
    cf = HH.crypto_frame("BTC=F")
    f = with_prev_close(cf, "BTC=F")
    first_after_break = f["break_days"] >= 2
    big = f["gap"].abs() >= GAP_Z * f["sd"]
    sig = pd.Series(np.where(first_after_break & big, np.sign(f["gap"]), 0), index=f.index).fillna(0)
    return sig[sig != 0]


def build_trades(dry_run=False):
    sig = btc_weekend_signal()
    if dry_run:
        return sig, None
    frames = {sym: D.market_frame(sym) for sym in D.EQUITY}
    out = []
    for sym, frame in frames.items():
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
    print(f"  {NAME:<58} n={a['n']:>5} mean {a['exp']:+.3f}R (gross {tr['gross'].mean():+.3f}R) | "
          f"IS(<2023) {i['exp']:+.3f}R P {i['p_pos']:.3f} | OOS(>=2023) {o['exp']:+.3f}R P {o['p_pos']:.4f} "
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
        print(f"BTC weekend-gap signal (|gap|>={GAP_Z}xSD, break>=2 days): {len(sig)} qualifying days")
        print(f"  first: {sig.index.min()}  last: {sig.index.max()}")
        print(f"  long days: {(sig > 0).sum()}  short days: {(sig < 0).sum()}")
        print(f"  ~{len(sig) / ((sig.index.max() - sig.index.min()).days / 7):.2f} qualifying days per week")
        print("\n--dry-run: counts only, no P&L. Hand-check a few signals before running for real.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    r = judge(tr, k)
    lines = H.ledger_rows([r], "Round 154 (pre-registered, new idea class: crypto->equity information transfer)", commit)
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round154_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
