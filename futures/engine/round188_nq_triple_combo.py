"""
Round 188: asked directly whether combining ALL of NQ's tested intraday
leads and letting it trade would work. Checked the correlation FIRST, same
discipline as Round 186 -- and it's the same story again: the POC
reversion + Value Area rejection combo (Round 186) correlates 0.61 with the
overnight gap fade (Round 187), and 972 of the combo's 1,452 active days
(67%) also carry a gap-fade signal. Mechanistically expected: all three
fire on some version of "today opened unusually far from a reference
point" (yesterday's POC, yesterday's value area, or yesterday's own
close) -- not three independent phenomena.

Honest before running: the gap fade ALREADY FAILED its own out-of-sample
check on its own (Round 187: OOS P=0.619 against a bar of ~1.0000). Adding
a rule that isn't itself a validated signal into an ensemble doesn't
average toward something real; at best it dilutes the two real legs
further with the same kind of correlated noise Round 186 already found
limits the benefit of combining. Tested anyway because it was asked for
directly and the campaign's rule is to compute, not assume.

Rule: identical netting convention to Round 186 -- sum POC-reversion's,
Value-Area-rejection's and gap-fade's signed $ pnl per (date, NQ) (same
same-contract-netting model: one account, three rules, net position each
day). All three already Broker-legal (flat by 16:00 ET), one trade a day
per leg by construction.

1 variant, NQ only. Ledger k=326 -> 327; OOS bar 1 - 0.01/327.

Candidate: idea_harness.test_idea's own rule, applied via round120_goal_judge's
edge_stats directly (as Round 186 did, since idea_harness.test_idea's automatic
gross reconstruction doesn't fit a pre-netted combined daily series): positive net
and gross; IS P(edge>0) >= 0.95; OOS P(edge>0) >= the bar.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round178_volume_profile_poc import build_trades as poc_trades
from round184_value_area_breakout import build_trades as va_trades
from round187_daily_gap_fade import build_trades as gap_trades

OOS_START = pd.Timestamp("2025-07-01")


def combined_daily():
    poc_tr, poc_days = poc_trades("NQ")
    va_tr, va_days = va_trades("NQ", False)  # rejection
    gap_tr, gap_days = gap_trades("NQ")
    poc_daily = poc_tr.groupby(pd.to_datetime(poc_tr["entry_ts"]).dt.normalize())["pnl"].sum()
    va_daily = va_tr.groupby(pd.to_datetime(va_tr["entry_ts"]).dt.normalize())["pnl"].sum()
    gap_daily = gap_tr.groupby(pd.to_datetime(gap_tr["entry_ts"]).dt.normalize())["pnl"].sum()
    all_days = pd.DatetimeIndex(sorted(d["tday"] for d in poc_days))
    combined = (poc_daily.reindex(all_days, fill_value=0.0) + va_daily.reindex(all_days, fill_value=0.0)
                + gap_daily.reindex(all_days, fill_value=0.0))
    return combined, all_days


def judge(daily, k):
    tr = pd.DataFrame({"date": daily.index, "pnl": daily.values})
    tr = tr[tr["pnl"] != 0]
    st = lambda x: J.edge_stats(x, n_boot=40_000) if len(x) else dict(n=0, exp=np.nan, p_pos=np.nan)
    a, i, o = st(tr), st(tr[tr["date"] < OOS_START]), st(tr[tr["date"] >= OOS_START])
    bar = H.oos_bar(k)
    cand = bool(a["exp"] > 0 and i["p_pos"] >= 0.95 and o["p_pos"] >= bar)
    print(f"  NQ POC + Value Area rejection + gap fade, netted per day, Databento  n={a['n']:>5} "
          f"mean ${a['exp']:+.1f} | IS ${i['exp']:+.1f} P {i['p_pos']:.3f} | OOS ${o['exp']:+.1f} P {o['p_pos']:.4f} "
          f"(bar {bar:.5f}) | full-cal Sharpe/day {daily.mean() / daily.std():+.4f} | "
          f"{'CANDIDATE' if cand else 'no'}", flush=True)
    return dict(name="NQ POC + Value Area rejection + gap fade, netted per day, Databento", n=a["n"], exp=a["exp"],
               p_is=i["p_pos"], p_oos=o["p_pos"], k=k, bar=bar,
               full_cal_sharpe=float(daily.mean() / daily.std()), candidate=cand)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    daily, all_days = combined_daily()

    if dry:
        print(f"Combined NQ POC+VA+gap: {int((daily != 0).sum())} active days of {len(daily)}")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + 1
    r = judge(daily, k)
    line = (f"| {k} | 2026-09-28 | {r['name']} | Round 188 (pre-registered, does combining all of NQ's leads help?) "
           f"| {commit} | {r['n']} | {r['exp']:+.1f} | n/a | {r['p_is']:.2f} / {r['p_oos']:.3f} | "
           f"{'CANDIDATE' if r['candidate'] else 'no edge'} |")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    with open(os.path.join(H.HERE, "round188_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
