"""
Round 186: does combining NQ's two Market Profile leads (POC reversion,
Round 178/183; Value Area rejection, Round 184/185) produce something
stronger, the same diversification check Round 166/175 ran on other
combinations? Checked the correlation first, before assuming independence:
0.59 (daily $ correlation, full calendar) -- these are NOT the
near-independent legs Round 175's cross-asset combo had (0.018). 995 of
POC's 1,348 active days also have a Value Area rejection signal the same
day (74% overlap). Mechanistically this makes sense and is worth stating
plainly: POC sits INSIDE the value area, so a big gap from POC often
coincides with also being near or beyond the value-area edge -- both leads
are triggered by variations of "today opened unusually far from yesterday's
volume-weighted reference distribution," not two independent phenomena.
This tempers, a little, the "two independent confirmations" framing from
Round 184/185 -- they're related re-expressions of one underlying
observation about NQ, not fully separate evidence.

Rule: sum POC-reversion's and Value-Area-rejection's signed R contribution
per (date, NQ) -- the same signed-sum convention Round 166 used for the
dip-buy ensemble (correct model of running both on one account with same-
contract netting: on the 995 overlap days, if both agree in direction they
combine into a bigger position; if they disagree they net down). Both legs
already Broker-legal (flat by 16:00 ET) and one-trade-a-day per leg by
construction.

Step 0, honest before running: given the real 0.59 correlation, this is
NOT expected to produce a clean diversification win the way Round 175's
near-zero-correlation combo did -- tested to quantify the actual, likely
modest benefit, not because a big lift is expected.

1 variant, NQ only. Ledger k=321 -> 322; OOS bar 1 - 0.01/322.

Candidate: idea_harness.test_idea's own rule (positive net and gross; IS
P(edge>0) >= 0.95; OOS P(edge>0) >= the bar).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round178_volume_profile_poc import build_trades as poc_trades
from round184_value_area_breakout import build_trades as va_trades

OOS_START = pd.Timestamp("2025-07-01")


def combined_daily():
    """Each leg's own $ pnl already has its own real costs netted in (via
    idea_harness.resolve_bracket); summed per (date, NQ) -- the correct model
    of running both on one account with same-contract netting on overlap days."""
    poc_tr, poc_days = poc_trades("NQ")
    va_tr, va_days = va_trades("NQ", False)  # rejection
    poc_daily = poc_tr.groupby(pd.to_datetime(poc_tr["entry_ts"]).dt.normalize())["pnl"].sum()
    va_daily = va_tr.groupby(pd.to_datetime(va_tr["entry_ts"]).dt.normalize())["pnl"].sum()
    all_days = pd.DatetimeIndex(sorted(d["tday"] for d in poc_days))
    combined = poc_daily.reindex(all_days, fill_value=0.0) + va_daily.reindex(all_days, fill_value=0.0)
    return combined, all_days


def judge(daily, k):
    tr = pd.DataFrame({"date": daily.index, "pnl": daily.values})
    tr = tr[tr["pnl"] != 0]
    st = lambda x: J.edge_stats(x, n_boot=40_000) if len(x) else dict(n=0, exp=np.nan, p_pos=np.nan)
    a, i, o = st(tr), st(tr[tr["date"] < OOS_START]), st(tr[tr["date"] >= OOS_START])
    bar = H.oos_bar(k)
    active = daily[daily != 0]
    cand = bool(a["exp"] > 0 and i["p_pos"] >= 0.95 and o["p_pos"] >= bar)
    print(f"  NQ POC reversion + Value Area rejection, netted per day, Databento  n={a['n']:>5} "
          f"mean ${a['exp']:+.1f} | IS ${i['exp']:+.1f} P {i['p_pos']:.3f} | OOS ${o['exp']:+.1f} P {o['p_pos']:.4f} "
          f"(bar {bar:.5f}) | full-cal Sharpe/day {daily.mean() / daily.std():+.4f} | "
          f"{'CANDIDATE' if cand else 'no'}", flush=True)
    return dict(name="NQ POC reversion + Value Area rejection, netted per day, Databento", n=a["n"], exp=a["exp"],
               p_is=i["p_pos"], p_oos=o["p_pos"], k=k, bar=bar,
               full_cal_sharpe=float(daily.mean() / daily.std()), candidate=cand)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    daily, all_days = combined_daily()

    if dry:
        print(f"Combined NQ POC+VA-rejection: {int((daily != 0).sum())} active days of {len(daily)}")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + 1
    r = judge(daily, k)
    line = (f"| {k} | 2026-09-28 | {r['name']} | Round 186 (pre-registered, does combining NQ's two Market "
           f"Profile leads help?) | {commit} | {r['n']} | {r['exp']:+.1f} | n/a | {r['p_is']:.2f} / "
           f"{r['p_oos']:.3f} | {'CANDIDATE' if r['candidate'] else 'no edge'} |")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    with open(os.path.join(H.HERE, "round186_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
