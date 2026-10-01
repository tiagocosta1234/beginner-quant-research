"""
Round 292 (2026-10-01, PRE-REGISTERED): LONGER HOLDING PERIODS for the confirmed dip-reversal lead (the trader: "try the 2-5 day holding periods on the indices"). Round 286 confirmed "long after a 3-day fall of >= 2 sigma, held ONE day" on
8 cash indices 1990-2017 (+30.2 bp net per trade). Round 285 tried H = 3 on the CFD window only with a weekend-flat rule and found nothing that passed; this round asks the question on the LONG independent sample, with H = 2, 3, 4, 5
trading days and, separately, with and without the weekend-flat rule (an TEST account may hold over a weekend, a live Standard account may not).
SIGNAL (unchanged from Rounds 285/286): z3_t = ln(close_t / close_t-3) / (sigma60_t x sqrt(3)), sigma60 = SD of the previous 60 simple daily returns including day t (>= 40 observations), bad prints (> 50%) zeroed; LONG at the close of day t when z3 <= -Z;
exit at the close of day t + H (trading days). DATA: the Round 286 cash-index files (S&P 500, Nasdaq-100, DJIA, DAX, FTSE 100, CAC 40, Nikkei 225, Hang Seng), 1990-01-01 .. 2017-12-27. One position per index at a time (after an entry the next entry is allowed from day t + H).
ENTRY RULES: WEEKEND-FLAT ("flat"): exit weekday later than the entry weekday and at most H + 2 calendar days after entry (H = 2: entries Monday-Wednesday; H = 3: Monday-Tuesday; H = 4: Monday; H = 5 is impossible and is not run); ANY ("any"): every day, with the exit at most H + 4 calendar days after entry
(drops holiday gaps).
COST per trade (fixed now): 1.7 bp of spread and slippage + 3.3 bp per calendar night held (the index CFD's long swap, about -8% a year; Round 286's 5.0 bp for one night is 1.7 + 3.3), nights = calendar days between the entry and exit dates.
CELLS: (H, rule) in {2, 3, 4} x flat plus {2, 3, 4, 5} x any = 7 combinations, x Z in (1.0, 1.5, 2.0) = 21; ledger rows 1054-1074 (k = 1053 + 21 = 1074). PRIMARY HYPOTHESES: the 7 cells at Z = 2.0; Bonferroni BONF = 1 - 0.01/7 = 0.99857. Unit of inference: the date (daily mean over the
indices with a trade), 4,000-draw bootstrap, seed 2921. BASELINE: per index, the mean net of the unconditional trade (every eligible entry day, same H, rule and window); EXCESS = net - baseline. Sub-periods: 1990-2003 and 2004-2017.
CONFIRMATION RULE for a primary cell (fixed now): (a) mean net > 0 and P(net > 0) >= BONF, (b) P(excess > 0) >= BONF, (c) mean excess > 0 in BOTH sub-periods, (d) mean net rises with the move size, Z = 1.0 < 1.5 < 2.0, (e) mean excess positive in at least 6 of 8 indices.
SECOND VERDICT (practical, for confirmed cells only): the longer hold is WORTH USING over the one-day rule if its mean net per trade is higher than the one-day rule's on the same sample and cost model (the H = 1 control is recomputed here) AND its mean net per calendar day in the market is >= 50% of the
one-day rule's (the capital is tied up longer, so a longer hold has to earn its time). DESCRIPTIVE (not part of the rule): (i) the reversal profile: the mean excess return of each day 1..5 after a Z >= 2 signal (no overlap restriction, minus the unconditional mean of that day), to see where the rebound happens; (ii) the same cells on the 2018-2025 MT5 broker index CFD window (Round 285's 11
CFDs, MT5 broker swap and spreads, weekend-flat only), Z = 2, H = 1..4.
DRY-RUN CHECK: the H = 1 control must reproduce Round 286's primary cell (1,216 trades, +30.2 bp net) up to the difference between the fixed 5.0 bp and the calendar-night cost model (holidays); trade counts per cell are printed, no cell means are.
PRIOR (stated now): short-term reversal is concentrated in the first day or two; the rebound after day 1 is likely already harvested, so a longer hold probably adds risk and swap cost faster than return; the honest expectation is that H = 2 may be confirmed and H >= 3 not, with a lower return per day in the market than H = 1.
POWER_NOTES: ~1,200 trades at H = 1, fewer with the weekend-flat rule at longer holds (H = 4 flat: Monday entries only, a few hundred trades); the standard error of the mean grows with sqrt(H) (per-trade SD ~200-400 bp), so cells with only a few hundred trades can only confirm effects of ~30 bp or more.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round286_dip_reversal_independent_confirmation as R6
import round280_swap_aware_long_short as R8
import round285_multi_day_dip_reversal as R5

CELLS = [(2, "flat"), (3, "flat"), (4, "flat"), (2, "any"), (3, "any"), (4, "any"), (5, "any")]
ZS = (1.0, 1.5, 2.0)
FROM, TO, SPLIT = R6.FROM, R6.TO, R6.SPLIT
SPREAD_BP, NIGHT_BP = 1.7, 3.3
K_BASE = 1053
K_TOTAL = K_BASE + len(CELLS) * len(ZS)
BONF = 1 - 0.01 / len(CELLS)
SEED, BOOT = 2921, 4000


def eligible(S, i, H, rule):
    d = S["d"]
    if i + H >= len(d):
        return False
    span = (d[i + H] - d[i]).days
    if rule == "flat":
        return S["wd"][i + H] > S["wd"][i] and span <= H + 2
    return span <= H + 4


def net(S, i, H):
    span = (S["d"][i + H] - S["d"][i]).days
    return float(S["r"][i + 1:i + H + 1].sum()) * 1e4 - (SPREAD_BP + NIGHT_BP * span)


def entries(S, lo, hi, H, rule, Z=None):
    out = []
    i = 70
    n = len(S["d"])
    while i < n - H:
        ok = lo <= S["d"][i] <= hi and eligible(S, i, H, rule) and np.isfinite(S["z3"][i])
        if ok and Z is not None:
            ok = S["z3"][i] <= -Z
        if ok:
            out.append((S["d"][i], net(S, i, H)))
            i += H
        else:
            i += 1
    return out


def run_window(Ss, lo, hi, H, rule, Z):
    rows = []
    for name, S in Ss.items():
        base = entries(S, lo, hi, H, rule, None)
        b = float(np.mean([v for _, v in base])) if base else np.nan
        for d, v in entries(S, lo, hi, H, rule, Z):
            rows.append((name, d, v, v - b))
    return pd.DataFrame(rows, columns=["idx", "date", "net", "ex"])


def boot_p(x, seed=SEED):
    x = np.asarray(x, float)
    if len(x) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), (BOOT, len(x)))
    return float(np.mean(x[idx].mean(axis=1) > 0))


def summarize(tr, H):
    if len(tr) < 5:
        return dict(n=int(len(tr)), mean=float("nan"), excess=float("nan"), win=float("nan"), P=float("nan"), Pex=float("nan"), per_day=float("nan"), worst=float("nan"))
    d = tr.groupby("date")[["net", "ex"]].mean()
    return dict(n=int(len(tr)), mean=float(tr["net"].mean()), excess=float(tr["ex"].mean()), win=float((tr["net"] > 0).mean()), P=boot_p(d["net"].values), Pex=boot_p(d["ex"].values),
                per_day=float(tr["net"].mean() / H), worst=float(tr["net"].min()))


def dry_run():
    Ss = {n: R6.load(n) for n in R6.NAMES}
    # H = 1 control vs Round 286
    tr = run_window(Ss, FROM, TO, 1, "flat", 2.0)
    print(f"H = 1 control: {len(tr)} trades, mean net {tr['net'].mean():+.1f} bp (Round 286: 1,216 trades, +30.2 bp at a fixed 5.0 bp cost)")
    assert len(tr) == 1216, len(tr)
    assert abs(tr["net"].mean() - 30.2) < 1.5, tr["net"].mean()
    for H, rule in CELLS:
        cnt = {Z: len(run_window(Ss, FROM, TO, H, rule, Z)) for Z in ZS}
        print(f"   H {H} {rule:>4}: trades " + ", ".join(f"Z {Z}: {n}" for Z, n in cnt.items()))
    for S in Ss.values():
        assert all(S["wd"][i + H] > S["wd"][i] for H in (2, 3, 4) for i in range(70, len(S["d"]) - H) if eligible(S, i, H, "flat"))
    print("weekend-rule assertions passed")
    rng = np.random.default_rng(2)
    for H, rule in ((2, "flat"), (4, "any")):
        allb = [(n, d, v) for n, S in Ss.items() for d, v in entries(S, FROM, TO, H, rule, None)]
        pick = rng.choice(len(allb), size=1200, replace=False)
        print(f"placebo H {H} {rule}: 1,200 random entries, mean net {np.mean([allb[j][2] for j in pick]):+.1f} bp vs unconditional {np.mean([v for _, _, v in allb]):+.1f} bp")
    print("DRY RUN OK")


def profile(Ss):
    """mean excess return (bp) of day k after the signal, k = 1..5, all signal days (no overlap restriction), minus the unconditional mean of that day."""
    out = {}
    for k in range(1, 6):
        ex = []
        for n, S in Ss.items():
            m = (S["d"] >= FROM) & (S["d"] <= TO)
            idx = np.flatnonzero(m)
            idx = idx[(idx >= 70) & (idx + k < len(S["d"]))]
            allr = S["r"][idx + k] * 1e4
            sig = idx[np.isfinite(S["z3"][idx]) & (S["z3"][idx] <= -2.0)]
            ex.append(((S["r"][sig + k] * 1e4).sum() - len(sig) * allr.mean(), len(sig)))
        out[k] = float(sum(e for e, _ in ex) / sum(n for _, n in ex))
    return out


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    Ss = {n: R6.load(n) for n in R6.NAMES}
    out = {"cells": {}, "per_index": {}}
    ctrl = {}
    print(f"{'H':>2} {'rule':>5} {'Z':>4} | {'window':>9} {'n':>6} {'net':>7} {'excess':>7} {'/day':>6} {'win':>6} {'worst':>7} {'P(net)':>7} {'P(exc)':>7}")
    for H, rule in [(1, "flat")] + CELLS:
        for Z in ZS:
            for wname, lo, hi in (("all", FROM, TO), ("1990-2003", FROM, SPLIT - pd.Timedelta(days=1)), ("2004-2017", SPLIT, TO)):
                tr = run_window(Ss, lo, hi, H, rule, Z)
                s = summarize(tr, H)
                out["cells"][f"{H}|{rule}|{Z}|{wname}"] = s
                if wname == "all":
                    print(f"{H:>2} {rule:>5} {Z:>4.1f} | {wname:>9} {s['n']:>6} {s['mean']:>+7.1f} {s['excess']:>+7.1f} {s['per_day']:>+6.1f} {s['win']:>6.1%} {s['worst']:>+7.0f} {s['P']:>7.3f} {s['Pex']:>7.3f}", flush=True)
                    if Z == 2.0:
                        out["per_index"][f"{H}|{rule}"] = {n: dict(n=int((tr['idx'] == n).sum()), excess=float(tr[tr['idx'] == n]['ex'].mean()) if (tr['idx'] == n).any() else float('nan')) for n in R6.NAMES}
    verdicts = {}
    c1 = out["cells"]["1|flat|2.0|all"]
    print(f"\nPRIMARY HYPOTHESES (Z = 2, BONF {BONF:.5f}); H = 1 control: net {c1['mean']:+.1f} bp per trade, {c1['per_day']:+.1f} per day in the market")
    for H, rule in CELLS:
        c = lambda Z, w: out["cells"][f"{H}|{rule}|{Z}|{w}"]
        a = c(2.0, "all")["mean"] > 0 and c(2.0, "all")["P"] >= BONF
        b = c(2.0, "all")["Pex"] >= BONF
        cc = c(2.0, "1990-2003")["excess"] > 0 and c(2.0, "2004-2017")["excess"] > 0
        d = c(1.0, "all")["mean"] < c(1.5, "all")["mean"] < c(2.0, "all")["mean"]
        e = sum(1 for v in out["per_index"][f"{H}|{rule}"].values() if v["excess"] > 0) >= 6
        ok = bool(a and b and cc and d and e)
        worth = ok and c(2.0, "all")["mean"] > c1["mean"] and c(2.0, "all")["per_day"] >= 0.5 * c1["per_day"]
        verdicts[f"{H}|{rule}"] = dict(a=bool(a), b=bool(b), c=bool(cc), d=bool(d), e=bool(e), confirmed=ok, worth_over_h1=bool(worth))
        print(f"  H {H} {rule:>4}: (a) net>0 & P {a}, (b) P(excess) {b}, (c) both halves {cc}, (d) dose-response {d}, (e) >= 6 of 8 indices {e} -> {'CONFIRMED' if ok else 'NOT CONFIRMED'}" + (f"; worth using over H = 1: {worth}" if ok else ""))
    out["verdicts"] = verdicts
    prof = profile(Ss)
    out["profile"] = prof
    print("\nREVERSAL PROFILE (mean excess bp of day k after a Z >= 2 signal, all signal days, 1990-2017): " + ", ".join(f"day {k}: {v:+.1f}" for k, v in prof.items()))
    # CFD descriptive
    P = R8.prep(); Sc = R5.prep_series(P)
    out["cfd"] = {}
    print("\nDESCRIPTIVE 2018-2025 MT5 broker index CFDs (11), Z = 2 long, weekend-flat, MT5 broker swap and spread:")
    lo, hi = pd.Timestamp("2018-01-01"), pd.Timestamp("2025-09-30")
    for H in (1, 2, 3, 4):
        base = R5.baseline(Sc, H, 1, lo, hi)
        tr = R5.cell_trades(Sc, 2.0, "none", H, 1)
        s = R5.window_stats(tr, base, lo, hi)
        out["cfd"][str(H)] = s
        print(f"   H {H}: {s['n']} trades, net {s['mean']:+.1f} bp, excess {s['excess']:+.1f} bp, win {s['win']:.1%}, P(net) {s['P']:.2f}, P(excess) {s['Pex']:.2f}")
    json.dump(out, open(os.path.join(HERE, "round292_results.json"), "w"), indent=1, default=float)
    print(f"Saved round292_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
