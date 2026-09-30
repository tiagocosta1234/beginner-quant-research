"""
Round 231 (2026-09-30): Round 192's disciplined bracket re-run NET of costs.
PRE-REGISTRATION -- design and reporting fixed before any net number is computed.

WHY. Found while building Round 229: `round192_intraday_disciplined_bracket.
simulate_day()` computes realized P&L as direction * (exit - entry) * PV *
contracts and never deducts commission or slippage, although its docstring
says "real costs" (round178/round184 add a cost column in their own pipelines;
Round 192's day simulator does not). Every Round 192-derived figure is
therefore gross, and eleven later scripts import its `build_daily()` series
(listed at the end of this run's output).

METHOD. Round 192 is imported, never edited. This script walks the same days
with Round 192's own signal tables, `size_leg()` and `simulate_day()`, checks
that the gross daily series it gets is IDENTICAL to `build_daily()` (and that
the headline stats reproduce round192_results.json -- if either fails, stop),
then subtracts, for each day, cost_per_contract x (contracts of every leg that
was opened that day). Every opened leg is closed the same day (stop, target,
day-cap flatten or the 16:00 flat), so each costs exactly one round trip.

COST MODEL. The repo convention, idea_harness.cost_per_contract("NQ") =
COMMISSION_RT $1.24 + 2 ticks x $5 slippage = $11.24 per NQ contract round
trip. The $1.24 commission was verified for MICRO contracts only
(Knowledge_Base/BROKER_RULES_MASTER_STANDARD_TIERS.md); no full-size NQ fee is
verified in this repo, so it is likely understated. Sensitivity, reported
alongside and not as findings: slippage only ($10.00) and double the
convention ($22.48).

KNOWN LIMIT. Round 192's day caps (+$1,650 / -$850) trigger on GROSS running
P&L. A cap that watched net P&L would flatten marginally earlier on cap days.
Not re-simulated here (that needs a modified simulate_day); bounded by one
day's cost per cap-triggered day, and the count of such days is reported.

REPORTED, gross vs net: active days, win rate (share of active days > 0),
daily Sharpe, max drawdown, final P&L, bootstrap P(mean active-day P&L > 0),
IS (< 2025-07-01) / OOS split, and the chained $50K Test replay Round 192
itself used (round190.chained_attempts: $3,000 target, $2,000 MLL, 55%
consistency). Also exposes `build_daily_net()` with the same return shape as
Round 192's `build_daily()`, so a downstream script can be re-run net by
changing one import.

Not a new signal, no ledger row; journal either way.

POWER NOTES (--dry-run, no P&L printed): parity check passes -- this script's
gross daily series is identical to round192.build_daily(). 1,806 days, 1,452
active; contracts opened per active day mean 1.98 (1: 428 days, 2: 948, 3+:
76, max 51 -- Round 192 sizes each leg as min(max(1, $300 // stop$), 50), so a
very tight stop can put on dozens of NQ contracts). Cap-triggered days: 492
cap_loss, 386 cap_win (878 days where the gross-vs-net cap limit above applies).
"""
import os, sys, json, argparse, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import pandas as pd
import round192_intraday_disciplined_bracket as R192
import idea_harness as H
import pass_speed_gate as G
from round190_disciplined_daily_bracket import chained_attempts

COST_CONV = H.cost_per_contract("NQ")          # $11.24 after round171 registers NQ
COSTS = {"slippage_only": 2 * H.TK["NQ"] * H.PV["NQ"], "repo_convention": COST_CONV, "double": 2 * COST_CONV}
OOS_START = pd.Timestamp("2025-07-01")
N_BOOT = 4000


def daily_with_contracts():
    """Round 192's build_daily() loop, plus the day's total opened contracts."""
    days = R192.load_days_databento("NQ")
    poc_sig = R192.poc_signals(days, R192.TK).set_index("ts")
    va_sig = R192.va_signals(days, R192.TK, False).set_index("ts")
    rows = []
    for d in days:
        s = d["session"]
        if s.empty:
            rows.append((d["tday"], 0.0, "none", 0))
            continue
        t0 = s.index[0]
        poc_row = poc_sig.loc[t0] if t0 in poc_sig.index else None
        va_row = va_sig.loc[t0] if t0 in va_sig.index else None
        contracts = sum(leg["contracts"] for leg in (R192.size_leg(poc_row), R192.size_leg(va_row)) if leg is not None)
        pnl, trig = R192.simulate_day(s, poc_row, va_row)
        rows.append((d["tday"], pnl, trig, contracts))
    idx = pd.DatetimeIndex([r[0] for r in rows])
    return (pd.Series([r[1] for r in rows], index=idx), pd.Series([r[2] for r in rows], index=idx),
            pd.Series([r[3] for r in rows], index=idx))


def build_daily_net(cost_per_contract=COST_CONV):
    """Same return shape as round192.build_daily(): (daily P&L, triggers), net of costs."""
    gross, trig, n = daily_with_contracts()
    return gross - n * cost_per_contract, trig


def stats(daily):
    active = daily[daily != 0]
    rng = np.random.default_rng(0)
    a = active.to_numpy(float)
    att = chained_attempts(daily.values, list(daily.index))
    outc = pd.Series([x["outcome"] for x in att]).value_counts().to_dict()
    n_att, p = len(att), outc.get("pass", 0)
    return dict(n=int(len(active)), win_rate=float((active > 0).mean()), sharpe=float(daily.mean() / daily.std()),
                max_dd=float(G.max_drawdown(daily.values)), final=float(daily.sum()),
                mean_active_day=float(a.mean()),
                p_mean_pos=float((rng.choice(a, (N_BOOT, len(a))).mean(1) > 0).mean()),
                chained_n=n_att, chained_pass=int(p), chained_rate=p / n_att,
                chained_median_days=float(np.median([x["days"] for x in att])))


def downstream_importers():
    out = subprocess.run(["git", "-C", HERE, "grep", "-l", "from round192_intraday_disciplined_bracket import"],
                         capture_output=True, text=True).stdout.split()
    return sorted(os.path.basename(p) for p in out if not os.path.basename(p).startswith(("round192_", "round231_")))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    gross, trig, contracts = daily_with_contracts()
    ref_daily, _ = R192.build_daily()
    identical = bool(np.array_equal(gross.values, ref_daily.values) and gross.index.equals(ref_daily.index))
    ref = json.load(open(os.path.join(HERE, "round192_results.json")))
    print(f"Parity: gross series identical to round192.build_daily(): {identical}")
    if not identical:
        sys.exit("STOP: gross series does not match round192.build_daily()")

    active = contracts[gross != 0]
    print(f"Days {len(gross)}, active {int((gross != 0).sum())}; contracts per active day: "
          f"mean {active.mean():.2f}, max {int(active.max())}; distribution {active.value_counts().sort_index().to_dict()}")
    print(f"Cap-triggered days: {trig.value_counts().to_dict()}")
    print(f"Cost per NQ contract RT (repo convention): ${COST_CONV:.2f}; sensitivity {COSTS}")
    if args.dry_run:
        sys.exit(0)

    g = stats(gross)
    repro = {k: (g[k], ref[k]) for k in ("n", "win_rate", "sharpe", "max_dd", "final", "chained_n", "chained_pass", "chained_median_days")}
    ok = all(abs(a - b) < 1e-6 * max(1, abs(b)) for a, b in repro.values())
    print(f"Reproduces round192_results.json: {ok}")
    if not ok:
        print(repro)
        sys.exit("STOP: gross stats do not reproduce Round 192's published results")

    results = dict(parity_identical=identical, reproduces_published=ok, cost_models=COSTS, gross=g, net={}, net_is_oos={})
    print(f"\n{'':<18}{'n':>6}{'win':>8}{'Sharpe/d':>10}{'maxDD':>11}{'final':>12}{'P(mean>0)':>11}{'chained pass':>15}{'med days':>10}")
    def row(label, s):
        print(f"{label:<18}{s['n']:>6}{s['win_rate']:>8.3f}{s['sharpe']:>10.4f}{s['max_dd']:>11,.0f}{s['final']:>12,.0f}"
              f"{s['p_mean_pos']:>11.3f}{s['chained_pass']:>6}/{s['chained_n']:<4} {s['chained_rate']:>5.1%}{s['chained_median_days']:>8.1f}")
    row("gross (Round 192)", g)
    for name, c in COSTS.items():
        net = gross - contracts * c
        results["net"][name] = stats(net)
        row(f"net {name}", results["net"][name])
    net = gross - contracts * COST_CONV
    for label, mask in (("IS", net.index < OOS_START), ("OOS", net.index >= OOS_START)):
        results["net_is_oos"][label] = dict(gross=stats(gross[mask]), net=stats(net[mask]))
        print(f"  {label}: gross Sharpe {results['net_is_oos'][label]['gross']['sharpe']:+.4f} "
              f"P(mean>0) {results['net_is_oos'][label]['gross']['p_mean_pos']:.3f} | net Sharpe "
              f"{results['net_is_oos'][label]['net']['sharpe']:+.4f} P(mean>0) {results['net_is_oos'][label]['net']['p_mean_pos']:.3f}")
    cost_total = float((contracts * COST_CONV).sum())
    print(f"\nTotal cost at repo convention: ${cost_total:,.0f} = {cost_total / g['final']:.1%} of Round 192's gross final P&L")
    results["total_cost_repo_convention"] = cost_total
    results["downstream_importers"] = downstream_importers()
    print("Scripts importing round192.build_daily (gross series):", ", ".join(results["downstream_importers"]))
    with open(os.path.join(HERE, "round231_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print("Saved round231_results.json")
