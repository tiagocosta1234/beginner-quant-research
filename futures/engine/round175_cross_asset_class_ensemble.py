"""
Round 175: the last of the trader's four smoothing levers. Round 166 combined
four signals from ONE family (equities, daily-close, "buy weakness in an
uptrend") and found real but small diversification (Connors-IBS correlate
at 0.38; the ceiling from more of the same family is proven, not assumed:
inverse-variance reweighting only reached 0.050). This tries genuine
cross-ASSET-CLASS combination instead: two legs that don't share a market,
a timeframe, or a mechanism, so their correlation should plausibly be much
lower than anything combined so far in this campaign.

Leg A: the Round 166 dip-buy-family union ensemble (Connors RSI(2) + IBS +
       month-end rebalancing + pre-holiday), ES/NQ/YM/RTY, DAILY close-to-
       close holds, calendar/momentum-driven, 2000-2026.
Leg B: the Round 171 GC opening-range breakout (>=2.5x volume, 2R target),
       INTRADAY (flat by 16:00 ET), metals, participation-driven,
       2019-2026 (Databento). Chosen over NQ's ORB cell specifically
       because GC's OOS P (0.81) reflects real signal, however unconfirmed;
       NQ's ORB cell (OOS P 0.52) is indistinguishable from noise and would
       only dilute, not diversify.

Both converted to R-units (leg A already is, via round135's convention;
leg B's dollar P&L divided by idea_harness.RISK=$300) before combining, so
they're on the same scale. Summed per calendar day (0 on days neither
fires) -- the same "signed sum reproduces same-contract netting" logic
Round 166 used, just now across genuinely different underlying instruments
where there's no netting to model in the first place (different contracts).

Step 0, honest before running: cross-asset diversification is a real,
well-established portfolio principle (it's the reason funds hold multiple
asset classes at all) -- more likely to show a REAL correlation reduction
than Round 166's within-family attempt did. But GC's own leg has an
unconfirmed OOS P of 0.81, so this combination is built partly on a signal
that hasn't itself cleared this ledger's bar -- the combined result could
look better only because GC's own point estimate is optimistic, not because
diversification created something new. Reported with both the correlation
and each leg's own standing disclosed, not just the combined number.

Diagnostic report: leg correlation (over GC's real 2019-2026 window), full-
calendar combined daily Sharpe, and the same real pass-speed-gate numbers
this ledger always uses to separate "statistically real" from "fast
enough" -- not forced into a single ledger candidate row, since the two
legs use different IS/OOS split conventions (round135's 2013 split vs
idea_harness's 2025-07 split) and combining them into one artificial split
would misrepresent what was actually tested. `round166_results.json` and
`round171_results.json` already carry each leg's own formal ledger entry;
this round is the cross-asset combination check on top of both.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round135_batch_d as D
import pass_speed_gate as G
from round166_dip_family_ensemble import build_legs as build_equity_legs, combine as combine_equity
from round171_databento_orb_replication import build_trades as build_gc_trades

if __name__ == "__main__":
    equity_legs = build_equity_legs()
    equity_combined, _, _ = combine_equity(equity_legs)
    equity_daily = equity_combined.groupby("date")["pnl"].sum()  # already R-units (round135 convention)

    gc_tr, gc_days = build_gc_trades("GC", 2.5, 2.0)
    gc_cal = pd.DatetimeIndex(sorted(d["tday"] for d in gc_days))
    gc_daily_dollars = gc_tr.groupby(pd.to_datetime(gc_tr["entry_ts"]).dt.normalize())["pnl"].sum()
    gc_daily = (gc_daily_dollars.reindex(gc_cal, fill_value=0.0) / H.RISK)  # convert to R-units

    full_cal = pd.DatetimeIndex(sorted(set(equity_daily.index) | set(gc_daily.index)))
    a = equity_daily.reindex(full_cal, fill_value=0.0)
    b = gc_daily.reindex(full_cal, fill_value=0.0)

    overlap = full_cal[(full_cal >= gc_cal.min()) & (full_cal <= gc_cal.max())]
    corr = np.corrcoef(a.reindex(overlap).values, b.reindex(overlap).values)[0, 1]
    print(f"Leg A (equity dip-buy union): {equity_daily.index.min().date()} -> {equity_daily.index.max().date()}, "
          f"active days {(equity_daily != 0).sum()}")
    print(f"Leg B (GC ORB, >=2.5x vol): {gc_daily.index.min().date()} -> {gc_daily.index.max().date()}, "
          f"active days {(gc_daily != 0).sum()}")
    print(f"\nDaily-R correlation over the overlap window ({overlap.min().date()} -> {overlap.max().date()}, "
          f"n={len(overlap)}): {corr:+.4f}")

    combined = a + b
    for label, series in [("Leg A alone (full calendar)", a), ("Leg B alone (full calendar)", b),
                          ("A + B combined (full calendar)", combined)]:
        sh = series.mean() / series.std() if series.std() > 0 else float("nan")
        print(f"\n{label}: daily Sharpe {sh:+.4f}")
        if label.startswith("A + B"):
            g = G.gate(series.values)
            print(f"  pass-speed gate: best size ${g['dollars_per_R']}/R | pass<=5d {g['pass_5d']:.2%} | "
                  f"pass<=10d {g['pass_10d']:.2%} | pass<=21d {g['pass_21d']:.2%} | fail by 21d {g['fail_21d']:.2%}")
            # bootstrap P(edge>0) on the daily combined series, same methodology as everywhere else
            import round120_goal_judge as J
            synth = pd.DataFrame({"pnl": series[series != 0].values})
            st_all = J.edge_stats(synth, n_boot=40_000)
            print(f"  bootstrap P(edge>0) on active days: {st_all['p_pos']:.4f} (n={st_all['n']})")

    with open(os.path.join(H.HERE, "round175_results.json"), "w") as f:
        json.dump(dict(correlation=float(corr), leg_a_sharpe=float(a.mean() / a.std()),
                       leg_b_sharpe=float(b.mean() / b.std()), combined_sharpe=float(combined.mean() / combined.std())),
                  f, indent=1)
    print("\nDiagnostic round -- see docstring for why this isn't forced into a single ledger candidate row.")
