"""
Round 158: the inverse of Round 157 -- FADE copper's prior-day move instead
of following it. Pre-registered 2026-09-27, committed before this variant
is run.

Selection warning, stated before the run (same convention as Round 152's
inversion of Round 151's Q3): this variant was chosen BECAUSE Round 157's
co-movement hypothesis leaned significantly the other way (IS P 0.000,
OOS P 0.019 -- equivalently P 0.981 for the fade, since these are
complementary under the same bootstrap). Its result here is therefore
expected to look better than a fresh, untargeted idea would, and is weaker
evidence even if it clears the bar; a real pass would need genuinely new
(forward) days to confirm, not just the same history read the other way.
Rounds 154 (crypto) and 155 (dollar) leaned the same direction (fade over
co-movement) but less strongly (equivalent fade P 0.971 IS-only for crypto,
0.60 OOS; 0.90 OOS for dollar) -- not tested here; a real inversion of
those would need its own separate, later round if this one is worth
following up on the class.

Rule: Round 157's exact signal (sign of copper's prior-day return, |r| >=
0.5x its 20-day SD), traded the OTHER way: SHORT ES/NQ/YM/RTY when copper
gapped up, LONG when it gapped down. Same data, costs, splits
(round135_batch_d, 2013/2020) as Round 157.

1 variant. Ledger k=199 -> 200; OOS bar 1 - 0.01/200.

Candidate (as Round 152): net AND before-cost mean R > 0; IS P(edge>0) >=
0.95; OOS P(edge>0) >= the k=200 bar; positive on at least 3 of 4 equity
markets.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round135_batch_d as D
from round157_copper_leads_equity import copper_signal, judge as judge157, OOS_START

NAME = "Round 157 inverse: fade copper's prior-day move, ES/NQ/YM/RTY (chosen after Round 157's fade lean)"


def build_trades():
    sig = -copper_signal()  # the only change from Round 157: flip the sign
    out = []
    for sym in D.EQUITY:
        frame = D.market_frame(sym)
        direction = sig.reindex(frame.index).fillna(0)
        out.append(D.trades_from(frame, direction, sym))
    return pd.concat(out, ignore_index=True)


if __name__ == "__main__":
    k = H.ledger_count() + 1
    print(f"k = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)

    tr = build_trades()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    r = judge157(tr, k)  # identical stats/candidate logic to Round 157, just relabeled
    r["name"] = NAME
    print(f"  (relabeled: {NAME})", flush=True)
    lines = H.ledger_rows([r], "Round 158 inversion of Round 157 (pre-registered; selected after Round 157's fade lean)",
                           commit, date="2026-09-27")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round158_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
