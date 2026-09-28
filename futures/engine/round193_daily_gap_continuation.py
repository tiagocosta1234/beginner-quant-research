"""
Round 193: asked directly to stop optimizing/combining the existing NQ Market
Profile family and go find a genuinely NEW trading idea -- the 361-row ledger's
best signal (POC+VA 2-leg combo) is already established to top out at ~52-53%
fresh-start pass rate even with 8 parallel accounts, well short of 70%/2-weeks,
and every lever tried on it (risk filtering, overlap halving, wider stops,
confluence-only, delayed entry, dynamic sizing) has been exhausted.

Rule: the OPPOSITE of Round 187's gap fade -- daily gap CONTINUATION. Same gap
definition (today's RTH open minus yesterday's RTH close), same trigger
(|gap| >= 0.5x the 20-day rolling SD of the gap series, shifted 1, no
look-ahead), same stop sizing (0.15x the 20-day average session range beyond
the open), same exits (no target, flat by 16:00 ET, Broker-legal), same 4
symbols, same clean Databento 1-minute data. The ONLY thing that changes is
the trade direction: long a gap-up, short a gap-down (trade WITH the gap,
on the idea that an unusually large overnight move reflects real information
flow that continues intraday, rather than an overreaction that reverts).

Why this is a genuinely new, previously-untested construction and not a
relabel of Round 187 or Round 39: Round 187 (fade) and this round (continuation)
are the two mutually exclusive hypotheses about the SAME trigger -- only one
direction can be right, and Round 187 already falsified the fade side, so the
continuation side has never actually been checked with this ledger's honest
methodology. Round 39 tested a continuation-shaped idea long ago, but with a
pre-Round-120c ATR-trailing overnight-hold resolver that does not respect
Broker's flat-by-close rule and was never re-validated on Databento data or
folded into this ledger -- it does not stand in for this test.

Step 0, honest before running: Round 187's own fade hypothesis lost cleanly
across all 4 symbols, and gap effects at the daily-open level are folk-known
and heavily arbitraged in both directions -- there is no strong prior that
flipping the sign turns a loser into a winner (the honest base rate for "the
other side of an already-failed simple rule" is not much better than 50/50).
Tested anyway because it is the one adjacent hypothesis this ledger has not
yet checked, and it costs one round to rule out or confirm.

4 variants (one per symbol, same as Round 187). Ledger k=361 -> 365; OOS bar
1 - 0.01/365 at the last variant.

Candidate: idea_harness.test_idea's own rule (positive net and gross; IS
P(edge>0) >= 0.95; OOS P(edge>0) >= the bar at that variant's k).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round171_databento_orb_replication import load_days_databento

FLAT_TIME = dt.time(16, 0)
RANGE_WINDOW = 20
GAP_Z = 0.5
STOP_MULT = 0.15


def build_signals(days, tick):
    ranges = pd.Series({d["tday"]: (d["session"]["high"].max() - d["session"]["low"].min())
                        for d in days if not d["session"].empty})
    avg_range = ranges.rolling(RANGE_WINDOW, min_periods=10).mean().shift(1)

    opens = pd.Series({d["tday"]: d["session"]["open"].iloc[0] for d in days if not d["session"].empty})
    closes = pd.Series({d["tday"]: d["session"]["close"].iloc[-1] for d in days if not d["session"].empty})
    gap = opens - closes.shift(1)
    gap_sd = gap.rolling(RANGE_WINDOW, min_periods=10).std().shift(1)

    out = []
    for d in days:
        s = d["session"]
        tday = d["tday"]
        if s.empty:
            continue
        S = avg_range.get(tday, np.nan)
        g = gap.get(tday, np.nan)
        sd = gap_sd.get(tday, np.nan)
        if not (S > 0) or not (sd > 0) or pd.isna(g):
            continue
        if abs(g) >= GAP_Z * sd:
            direction = int(np.sign(g))  # continuation: trade WITH the gap (only sign flip vs Round 187)
            open_px = s["open"].iloc[0]
            sl = open_px - direction * STOP_MULT * S
            out.append((s.index[0], direction, open_px, sl, np.nan))
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


def build_trades(sym):
    days = load_days_databento(sym)
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    sig = build_signals(days, H.TK[sym])
    tr = H.resolve_bracket(sig, bars, sym, flat_time=FLAT_TIME)
    tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
    return tr, days


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv

    if dry:
        for sym in ("ES", "NQ", "GC", "SI"):
            tr, days = build_trades(sym)
            print(f"{sym}: {len(tr)} trades of {len(days)} days")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rows = []
    for sym in ("ES", "NQ", "GC", "SI"):
        k = H.ledger_count() + 1
        tr, days = build_trades(sym)
        all_days = [d["tday"] for d in days]
        name = f"Daily overnight gap continuation, {sym}, Databento"
        r = H.test_idea(name, tr, all_days, sym, k)
        rows.append(r)
        lines = H.ledger_rows([r], "Round 193 (pre-registered, new idea class: daily gap continuation, opposite of Round 187's fade)",
                               commit, date="2026-09-28")
        with open(H.LEDGER, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round193_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n{sum(r['candidate'] for r in rows)} of {len(rows)} meet the bar; ledger now k={H.ledger_count()}")
