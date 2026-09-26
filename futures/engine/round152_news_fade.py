"""
Round 152: the inverse of Round 151's Q3 -- FADE the first break of the 08:30 news
range. Pre-registered 2026-09-26, committed before this variant is run.

Why this one: the trader asked to invert the losing edges and see if any converges to a real
edge. inversion_screen.py applies "inverse net = net - 2 x gross" to the whole ledger:
of batches M-Q only Q3 comes out positive (Q3 lost -$21.2 a trade before costs, costs
$6.7 -> inverse ~ +$14.5). Every other recent loser lost mostly to costs, which an
inverse pays too. Of the 27 ledger ideas positive by that arithmetic, 17 were
already inverted for real (Round 131) or are themselves inverses; the rest are older,
thin (136-894 trades) and far from the gate (see the journal).

Selection warning, stated before the run: this variant was chosen BECAUSE Q3 lost on
this same data (IS -$18.4, OOS -$72.6 a trade). Its results here are therefore
expected to look good and are weak evidence even if they clear the bar; any pass would
need new days to count. Independent data was checked and is unusable for this: the
BrokerAPI pulls (MES/MYM/M2K/SIL, 53 days) have start-stamped bars, platform-only
volumes (e.g. 70 MES contracts in the 2026-08-07 jobs-report minute) and 8-10 release
days.

Rules: Round 151's Q3 signal unchanged (MNQ + MGC 1-minute, end-stamped bars; release
= the bar stamped 08:31 with volume >= 5 x the average 08:01-08:30 bar; range = the
bars stamped 08:31-08:35; the first bar stamped 08:36-10:30 that closes outside it),
traded the other way: a close above the range -> SHORT at that close, target = the
range's low (Q3's stop), stop = Q3's target (same distance above the entry). 1:1,
idea_harness.resolve_bracket (stop first on a tie, flat at 16:00), $300 risk, whole
contracts, commission + 2 ticks; skipped if cost > 0.10R. Split 2025-07-01.
1 variant takes the ledger from k=190 to k=191.

Candidate (as batches M-Q): net and before-cost mean > 0; IS P(edge>0) >= 0.95; OOS
P(edge>0) >= 1 - 0.01/191; net mean > 0 on MNQ and on MGC; pass-speed gate
P(pass within 10 trading days) >= 0.50. At Q3's 0.47 trades a day the gate needs a
per-trade mean/SD >= 0.52 (about 74% wins at 1:1) -- out of reach unless the fade is
far stronger than Q3's loss implies (~+0.06 per-trade Sharpe).
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round147_batch_m import RISK, full, load, gate_row
from round151_batch_q import NEWS_T, NEWS_END, MAX_COST_R

NAME = "Q3 inverse: fade the 08:30 news break, 1:1, MNQ + MGC (chosen after Q3 lost)"


def news_fade(data):
    parts = []
    for sym, (days, bars) in data.items():
        sig = []
        for d in days:
            b = full(d)
            t = b.index.time
            pre = np.flatnonzero([dt.time(8, 0) < x <= NEWS_T for x in t])
            at = np.flatnonzero([x == dt.time(8, 31) for x in t])
            if len(pre) < 20 or len(at) != 1 or b["vol"].values[at[0]] < 5 * b["vol"].values[pre].mean():
                continue
            rng = np.flatnonzero([dt.time(8, 31) <= x <= dt.time(8, 35) for x in t])
            hi, lo = b["high"].values[rng].max(), b["low"].values[rng].min()
            if hi - lo <= 0 or H.cost_per_contract(sym) / ((hi - lo) * H.PV[sym]) > MAX_COST_R:
                continue
            for i in np.flatnonzero([dt.time(8, 36) <= x <= NEWS_END for x in t]):
                cl = b["close"].values[i]
                if cl > hi or cl < lo:
                    q3_dir = 1 if cl > hi else -1
                    q3_stop = lo if q3_dir == 1 else hi
                    dist = abs(cl - q3_stop)
                    # inverse: opposite side; target = Q3's stop, stop = Q3's target
                    sig.append((b.index[i], -q3_dir, cl, cl + q3_dir * dist, q3_stop))
                    break
        s = pd.DataFrame(sig, columns=["ts", "direction", "entry", "sl", "tp"])
        tr = H.resolve_bracket(s, bars, sym, risk=RISK)
        tr["cost"] = tr["contracts"] * H.cost_per_contract(sym)
        tr["sym"] = sym
        parts.append(tr)
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + 1
    print(f"k = {k}; OOS bar {H.oos_bar(k):.5f}\n", flush=True)
    data = load()
    all_days = sorted({d["tday"] for days, _ in data.values() for d in days})
    tr = news_fade(data)
    r = H.test_idea(NAME, tr, all_days, "MNQ", k, risk=RISK)
    per = tr.groupby("sym")["pnl"].mean()
    g, _ = gate_row(tr, all_days)
    per_day = len(tr) / len(all_days)
    both = bool(len(per) == 2 and (per > 0).all())
    r.update(gate=g, both_positive=both, per_market={s: float(v) for s, v in per.items()},
             trade_sharpe=float(tr["pnl"].mean() / tr["pnl"].std()), trade_sharpe_needed=0.36 / np.sqrt(per_day))
    r["candidate"] = bool(r["candidate"] and both and g["pass_10d"] >= 0.50)
    e = pd.to_datetime(tr["entry_ts"])
    print(f"      win {r['win']:.1%} (IS {(tr.loc[e < J.OOS_START, 'pnl'] > 0).mean():.1%}, OOS "
          f"{(tr.loc[e >= J.OOS_START, 'pnl'] > 0).mean():.1%}) | per-trade mean/SD {r['trade_sharpe']:+.3f} "
          f"(gate needs {r['trade_sharpe_needed']:.3f}) | " + ", ".join(f"{s} ${v:+.1f}" for s, v in per.items())
          + f" | gate: pass <= 10d {g['pass_10d']:.2f}, <= 21d {g['pass_21d']:.2f} | "
          f"{'CANDIDATE' if r['candidate'] else 'no'}", flush=True)
    lines = H.ledger_rows([r], "Round 152 inversion of Q3 (pre-registered; selected after Q3's result)", commit)
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round152_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
