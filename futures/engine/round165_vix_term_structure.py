"""
Round 165: a seventh new mechanism, and a different KIND of signal than any
cross-asset lead tried so far. Checked IDEA_LEDGER.md first (k=222) -- VIX
has been tested twice (Rounds 139/140, both on the raw LEVEL: "VIX jumped
X% above its own average -> buy the dip next day", both short of the bar).
Never tested: the SHAPE of the volatility term structure across maturities,
independent of whether VIX itself is elevated. VIX/VIX3M (30-day vs 93-day
implied vol) inverting into backwardation is a distinct, well-known signal
in vol-trading commentary -- it says near-term fear is priced ABOVE
longer-term fear, which is read as "the market expects the current stress to
matter, not just a one-day wobble", separate from whether the absolute VIX
level is unusually high. Verified data first: Yahoo has ^VIX 1990-,
^VIX3M 2006-07-17-2026-09-21 (the binding constraint), ^VIX9D only from
2011 -- used VIX/VIX3M for the longer usable history.

This tests CONTINUATION, not the mean-reversion story Rounds 139/140 already
covered: backwardation (z-score of the ratio unusually high) -> short
equities next session, on the theory that an inverted curve signals
sustained stress, not a one-off spike to fade. Mirror variant: extreme
contango (unusually low ratio) -> long equities (complacency persists,
low-vol grind). Both novel relative to the existing VIX-level tests, and to
each other.

Step 0, honest before running: term-structure signals are widely followed by
vol-desk commentary and in retail vol-ETN trading (XIV/SVXY-style products
literally harvest contango) -- if a clean next-day equity signal existed
here, the vol-trading community would likely have priced it into VIX futures
already. Tested as a genuinely different signal TYPE (relative pricing across
maturities, not a level or a lead from another asset class), not because
prior odds have improved from 0/6.

Rule: z = 60-day z-score of the VIX/VIX3M ratio (close-to-close), using only
the PRIOR day's close (causal). z >= 1.5 (backwardation extreme) -> short
ES/NQ/YM/RTY next session open->close. z <= -1.5 (contango extreme) -> long
the same, next session. `round135_batch_d`'s frames/costs/splits reused
(2013/2020 splits, ^VIX3M's own 2006 start pushes the "IS" window to
2006-13).

2 variants. Ledger k=222 -> 224; OOS bar 1 - 0.01/224 at the second variant.

Candidate (each variant separately): net AND before-cost mean R > 0; IS
P(edge>0) >= 0.95 (2006-13); OOS P(edge>0) >= the bar at that variant's k
(2013-26); positive on at least 3 of 4 equity markets.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
import round122b_tom_long_history as R122
import round135_batch_d as D

OOS_START = pd.Timestamp("2013-01-01")
FINAL_START = pd.Timestamp("2020-01-01")
Z_THRESH, WINDOW = 1.5, 60


def term_structure_z():
    vix = R122.load_daily("^VIX")["close"]
    vix3m = R122.load_daily("^VIX3M")["close"]
    ratio = (vix / vix3m).dropna()
    z = (ratio - ratio.rolling(WINDOW).mean()) / ratio.rolling(WINDOW).std()
    return z.shift(1).dropna()  # yesterday's close-of-day term structure, causal


def build_trades(direction_sign, dry_run=False):
    """direction_sign: +1 tests the backwardation-extreme->short/contango-extreme->long
    pair as coded; the sign is baked into the z thresholds below, this arg only
    selects which of the two pre-registered variants to build."""
    z = term_structure_z()
    sig = pd.Series(0, index=z.index)
    if direction_sign == "backwardation_short":
        sig[z >= Z_THRESH] = -1
    else:
        sig[z <= -Z_THRESH] = 1
    sig = sig[sig != 0]
    if dry_run:
        return sig, None
    out = []
    for sym in D.EQUITY:
        frame = D.market_frame(sym)
        direction = sig.reindex(frame.index).fillna(0)
        out.append(D.trades_from(frame, direction, sym))
    return sig, pd.concat(out, ignore_index=True)


def judge(name, tr, k):
    st = lambda x: J.edge_stats(x, n_boot=40_000) if len(x) else dict(n=0, exp=np.nan, p_pos=np.nan)
    a, i, o = st(tr), st(tr[tr["date"] < OOS_START]), st(tr[tr["date"] >= OOS_START])
    f20 = st(tr[tr["date"] >= FINAL_START])
    per = tr.groupby("market")["pnl"].mean()
    bar = H.oos_bar(k)
    n_pos = int((per > 0).sum())
    daily = tr.groupby("date")["pnl"].sum()
    cand = bool(a["exp"] > 0 and tr["gross"].mean() > 0 and i["p_pos"] >= 0.95 and o["p_pos"] >= bar and n_pos >= 3)
    print(f"  {name:<68} n={a['n']:>5} mean {a['exp']:+.3f}R (gross {tr['gross'].mean():+.3f}R) | "
          f"IS(<2013) {i['exp']:+.3f}R P {i['p_pos']:.3f} | OOS(>=2013) {o['exp']:+.3f}R P {o['p_pos']:.4f} "
          f"(bar {bar:.5f}) | 2020-26 {f20['exp']:+.3f}R | "
          f"{', '.join(f'{m} {v:+.3f}' for m, v in per.items())} ({n_pos}/4 positive) | "
          f"Sharpe/day {daily.mean() / daily.std():+.3f} | {'CANDIDATE' if cand else 'no'}", flush=True)
    return dict(name=name, n=a["n"], exp=a["exp"], exp_gross=float(tr["gross"].mean()), p_is=i["p_pos"],
                p_oos=o["p_pos"], exp_is=i["exp"], exp_oos=o["exp"], exp_2020_26=f20["exp"], k=k, bar=bar,
                per_market={m: float(v) for m, v in per.items()}, n_markets_positive=n_pos,
                trade_sharpe_daily=float(daily.mean() / daily.std()) if daily.std() > 0 else np.nan, candidate=cand)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    k0 = H.ledger_count()

    if dry:
        z = term_structure_z()
        print(f"VIX/VIX3M z-score: {z.index.min().date()} -> {z.index.max().date()}, n={len(z)}")
        print(f"  backwardation extreme (z>={Z_THRESH}) days: {(z >= Z_THRESH).sum()}")
        print(f"  contango extreme (z<=-{Z_THRESH}) days: {(z <= -Z_THRESH).sum()}")
        print("\n--dry-run: counts only, no P&L. Hand-check a few dates before running for real.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"k0 = {k0}\n", flush=True)

    _, tr1 = build_trades("backwardation_short")
    r1 = judge("VIX/VIX3M backwardation extreme (z>=1.5) -> short ES/NQ/YM/RTY next session", tr1, k0 + 1)

    _, tr2 = build_trades("contango_long")
    r2 = judge("VIX/VIX3M contango extreme (z<=-1.5) -> long ES/NQ/YM/RTY next session", tr2, k0 + 2)

    lines = H.ledger_rows([r1, r2], "Round 165 (pre-registered, new idea class: VIX term-structure shape)",
                           commit, date="2026-09-27")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round165_results.json"), "w") as f:
        json.dump([r1, r2], f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
