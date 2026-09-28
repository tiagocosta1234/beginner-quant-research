"""
Round 181: the regular, every-trading-day overnight gap, never tested in
this ledger. Checked first: Round 142's `gap_fade` only fires after
`break_days >= 3` -- weekends and holidays only. The ordinary Monday-to-
Tuesday (or any regular day-to-day) overnight gap between yesterday's RTH
close and today's RTH open has never been tested, on any symbol, in any
direction. One of the oldest, simplest day-trading ideas ("gaps fill") and
its opposite ("gaps that hold tend to run") -- surprisingly absent from
224 prior rounds' worth of level/breakout/mean-reversion tests, all of
which used PRIOR-DAY levels (high/low/round numbers) or overnight RANGE
extremes (Round 148's N3), never the plain close-to-open gap itself.

Uses Round 179's genuine RTH-only daily frame (real 09:30 ET open, real
16:00 ET close, same day, zero overnight exposure -- already verified not
to be an overnight-hold artifact for the dip-buy family in that round) on
all 4 Databento symbols: ES, NQ, GC, SI.

Rule: gap = log(today's RTH open / yesterday's RTH close), sized in units
of yesterday's own 20-day trailing volatility (same normalization as every
round135-style test). When |gap| >= a threshold, trade RTH open->close
(one trade a day, flat by 16:00 ET, Broker-legal by construction):
  Fade:   direction = -sign(gap) (bet the gap closes back toward yesterday)
  Follow: direction = +sign(gap) (bet the gap's move continues)
Both directions pre-registered and tested -- gap behavior is genuinely
ambiguous a priori (retail lore says "gaps fill"; momentum/information-
based theories say a gap on real news continues), so this isn't a case
where one direction is the obvious hypothesis and the other an inversion.

Step 0, honest before running: "gaps fill" is one of the most repeated
claims in retail trading education -- if it were this simply true, it
would already be arbitraged into the RTH open price itself. Tested for
completeness (every basic level/gap concept this campaign hasn't yet
covered), not because prior odds are good.

Threshold in {0.5, 1.0} (sigma multiples, matching this ledger's usual
gap-filter convention e.g. Round 142's GAP_Z=0.5, not picked after seeing
anything here). Each variant combines all 4 symbols (ES+NQ+GC+SI), matching
this ledger's established multi-symbol convention (Rounds 147/148/159/160).
2 thresholds x 2 directions = 4 variants. Ledger k=296 -> 300; OOS bar
1 - 0.01/300 at the last variant.

Candidate: idea_harness.test_idea's own rule, adapted to R-unit trades
(positive net and gross; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the bar).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round179_rth_only_dip_family import rth_daily_frame, trades_from

OOS_START = pd.Timestamp("2025-07-01")
THRESHOLDS = [0.5, 1.0]
SYMBOLS = ["ES", "NQ", "GC", "SI"]


def gap_signal(d, threshold, fade):
    gap = np.log(d["open"] / d["close"].shift(1))
    gap_z = (gap / d["sd"]).fillna(0)
    big = gap_z.abs() >= threshold
    sign = -np.sign(gap_z) if fade else np.sign(gap_z)
    return pd.Series(np.where(big, sign, 0), index=d.index)


def judge(name, tr, k):
    st = lambda x: J.edge_stats(x, n_boot=40_000) if len(x) else dict(n=0, exp=np.nan, p_pos=np.nan)
    a, i, o = st(tr), st(tr[tr["date"] < OOS_START]), st(tr[tr["date"] >= OOS_START])
    bar = H.oos_bar(k)
    daily = tr.groupby("date")["pnl"].sum()
    cand = bool(a["exp"] > 0 and tr["gross"].mean() > 0 and i["p_pos"] >= 0.95 and o["p_pos"] >= bar)
    print(f"  {name:<55} n={a['n']:>5} mean {a['exp']:+.3f}R (gross {tr['gross'].mean():+.3f}R) | "
          f"IS {i['exp']:+.3f}R P {i['p_pos']:.3f} | OOS {o['exp']:+.3f}R P {o['p_pos']:.4f} (bar {bar:.5f}) | "
          f"Sharpe/day {daily.mean() / daily.std():+.3f} | {'CANDIDATE' if cand else 'no'}", flush=True)
    return dict(name=name, n=a["n"], exp=a["exp"], p_is=i["p_pos"], p_oos=o["p_pos"], k=k, bar=bar,
                exp_gross=float(tr["gross"].mean()), candidate=cand,
                sharpe=float(daily.mean() / daily.std()) if daily.std() > 0 else np.nan)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    frames = {s: rth_daily_frame(s) for s in SYMBOLS}
    grid = [(thresh, fade) for thresh in THRESHOLDS for fade in (True, False)]

    if dry:
        for thresh, fade in grid:
            n = sum(int((gap_signal(frames[s], thresh, fade) != 0).sum()) for s in SYMBOLS)
            print(f"threshold={thresh}, {'fade' if fade else 'follow'}: {n} signals across 4 symbols")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for thresh, fade in grid:
        k = H.ledger_count() + 1
        tr = pd.concat([trades_from(frames[s], gap_signal(frames[s], thresh, fade), s) for s in SYMBOLS],
                       ignore_index=True)
        label = "fade" if fade else "follow"
        name = f"Daily RTH gap {label}, |gap|>={thresh}x vol, ES+NQ+GC+SI"
        r = judge(name, tr, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 181 (pre-registered, new idea class: the ordinary daily overnight gap)",
                               commit, date="2026-09-28")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round181_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
