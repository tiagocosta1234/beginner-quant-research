"""
Round 291 (2026-10-01, PRE-REGISTERED): does the CONFIRMED dip-reversal rule work OUTSIDE equity indices -- FX, metals, energy? (the trader: "sure" to "run the same rule across FX, gold, silver and oil to look for a second or
third independent edge", the Dalio "holy grail" logic: several uncorrelated real edges lift the Sharpe.) The rule is Round 285/286's, copied exactly and NOT re-tuned: z3_t = ln(close_t / close_t-3) / (sigma60_t x sqrt(3)),
sigma60 = SD of the previous 60 daily simple returns including day t (>= 40 observations); LONG at the close of day t when z3 <= -Z, exit at the close of the next trading day (H = 1), weekend rule (exit weekday later than the
entry weekday and <= 3 calendar days after: entries Monday-Thursday), one position per instrument. The mirror SHORT (z3 >= +Z) is tested too. Bad prints (> 50% or > 10 sigma) are zeroed as in Rounds 279/285.
DATA: MT5 D1 closes (17:00 NY) already in the repo (Round 280's `prep`): FX 15 pairs (EURUSD, GBPUSD, USDCHF, USDJPY, USDCAD, AUDUSD, NZDUSD, AUDNZD, AUDCAD, AUDCHF, AUDJPY, CHFJPY, EURGBP, EURJPY, GBPJPY) from 2000-03; METALS
XAUUSD (2004-06), XAGUSD (2008-11), XPTUSD and XPDUSD (2015-01); ENERGY UKOIL (2016-04) and USOIL (2020-12). EXCLUDED before any return was looked at: the agricultural, natural-gas, heating-oil, copper and DXY CFDs (history starts
2023-01 to 2024-12, i.e. under 4 years: no power), and nothing else. NO download is needed or made.
COSTS per trade: the instrument's one night of swap (today's MT5 broker swap fraction x nights, 3 nights across the triple-swap weekday: the repo's convention; disclosed: applying today's swaps to 2000-2012 is a distortion of a
few tenths of a bp for FX) plus the entry and exit half-spreads, with a FLOOR on the half-spread because the D1 spread field is blank for some old bars: 0.5 bp of price for FX, 1.0 bp for metals, 2.5 bp for energy (round trip 1 / 2 / 5 bp).
CELLS: group (FX, METALS, ENERGY) x side (long dip, short rip) x Z (1.0, 1.5, 2.0) = 18; ledger rows 1036-1053 (k = 1035 + 18 = 1053). Unit of inference: the date (daily mean over the group's instruments with a trade), 4,000-draw bootstrap, seed 2911.
BASELINE: per instrument and side, the mean net return of the unconditional trade (every eligible day) over the full sample; EXCESS = net - baseline (removes carry/drift: it asks whether the dip itself adds anything).
PRIMARY HYPOTHESES (6): each group x side at Z = 2.0 (the rule as confirmed); the Bonferroni level is BONF = 1 - 0.01/6 = 0.99833. A PRIMARY hypothesis is CONFIRMED only if (a) mean net > 0 and P(net > 0) >= BONF, (b) P(excess > 0) >= BONF,
(c) mean excess > 0 in BOTH halves (split 2013-01-01; each half needs >= 20 trades, else the half is "not testable" and the hypothesis is NOT confirmed), (d) mean net rises with the move size Z = 1.0 < 1.5 < 2.0, and
(e) mean excess is positive in at least two thirds of the group's instruments that have >= 20 Z = 2 trades. Otherwise NOT CONFIRMED. The Z = 1.0 and 1.5 cells are the dose-response, not separate hypotheses.
DESCRIPTIVE (not part of the rule): by instrument; the daily correlation of a group's Z = 2 long-dip stream (mean net bps on trade days, zero otherwise) with the Round 286 cash-index stream (8 indices, 1990-2017, cost 5 bp) over 2000-2017, and the
number of days on which both have a trade; the 2018-2026 half only. PRIOR (stated now): short-term reversal is documented in equity indices but is weak or absent in FX (a market of macro flows and carry), and metals/energy trend more than
they revert at one-day horizons; the honest expectation is no confirmed hypothesis. POWER_NOTES: FX at Z = 2 should have several thousand trades (SE of the mean ~1-2 bp against a per-trade SD of ~50-60 bp); metals a few hundred (SE ~5-8 bp);
energy tens (SE ~30 bp or more: it can only reject a very large effect).
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round280_swap_aware_long_short as R8
import round285_multi_day_dip_reversal as R5

GROUPS = {
    "FX": ["EURUSD", "GBPUSD", "USDCHF", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD", "AUDNZD", "AUDCAD", "AUDCHF", "AUDJPY", "CHFJPY", "EURGBP", "EURJPY", "GBPJPY"],
    "METALS": ["XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD"],
    "ENERGY": ["UKOIL.cash", "USOIL.cash"],
}
FLOOR_BP = {"FX": 0.5, "METALS": 1.0, "ENERGY": 2.5}                 # half-spread floor, bp of price
ZS, SIDES, H = (1.0, 1.5, 2.0), (1, -1), 1
SPLIT = pd.Timestamp("2013-01-01")
FROM, LAST = pd.Timestamp("2000-01-01"), pd.Timestamp("2026-09-30")
K_BASE = 1035
K_TOTAL = K_BASE + len(GROUPS) * len(SIDES) * len(ZS)
BONF = 1 - 0.01 / 6
SEED, BOOT = 2911, 4000


def resolve(P, sym):
    if sym in P["close"]:
        return sym
    for s in P["close"]:
        if s.split(".")[0] == sym.split(".")[0]:
            return s
    raise KeyError(sym)


def prep_group(P, g):
    S = {}
    for name in GROUPS[g]:
        s = resolve(P, name)
        c = P["close"][s].dropna()
        d = c.index
        r = P["ret"][s].reindex(d).fillna(0.0).values
        r = np.where(np.abs(r) > 0.5, 0.0, r)
        sd = (P["sigma"][s].reindex(d) / np.sqrt(252)).values
        lp = np.log(c.values)
        z3 = np.full(len(c), np.nan)
        z3[3:] = (lp[3:] - lp[:-3]) / (sd[3:] * np.sqrt(3))
        wd = d.weekday.values
        nights = np.ones(len(c))
        nights[1:] = np.where((wd[:-1] == P["trip"][s]), 3.0, 1.0)
        hs = max(float(P["hs"][s]), FLOOR_BP[g] * 1e-4 * float(np.median(c.values)))
        S[s] = dict(d=d, c=c.values, r=r, z3=z3, sma=np.zeros(len(c)), nights=nights, wd=wd, hs=hs, fl=P["frac_l"][s], fs=P["frac_s"][s])
    return S


def window_mask(S, lo, hi):
    return (S["d"] >= lo) & (S["d"] <= hi)


def baseline_one(S, side, lo, hi):
    v = [R5.trade_net(S, i, H, side) for i in range(70, len(S["d"]) - H) if lo <= S["d"][i] <= hi and R5.eligible(S, i, H)]
    return float(np.mean(v)) if v else float("nan")


def trades(Ss, Z, side, lo, hi, bases):
    rows = []
    for s, S in Ss.items():
        n = len(S["d"])
        for i in range(70, n - H):
            d = S["d"][i]
            if not (lo <= d <= hi) or not R5.eligible(S, i, H) or not np.isfinite(S["z3"][i]):
                continue
            hit = S["z3"][i] <= -Z if side > 0 else S["z3"][i] >= Z
            if hit:
                v = R5.trade_net(S, i, H, side)
                rows.append((s, d, v, v - bases[s]))
    return pd.DataFrame(rows, columns=["inst", "date", "net", "ex"])


def boot_p(x, seed=SEED):
    x = np.asarray(x, float)
    if len(x) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), (BOOT, len(x)))
    return float(np.mean(x[idx].mean(axis=1) > 0))


def summarize(tr):
    if len(tr) < 5:
        return dict(n=int(len(tr)), mean=float("nan"), excess=float("nan"), win=float("nan"), P=float("nan"), Pex=float("nan"))
    d = tr.groupby("date")[["net", "ex"]].mean()
    return dict(n=int(len(tr)), mean=float(tr["net"].mean()), excess=float(tr["ex"].mean()), win=float((tr["net"] > 0).mean()), P=boot_p(d["net"].values), Pex=boot_p(d["ex"].values))


def dry_run():
    P = R8.prep()
    rng = np.random.default_rng(3)
    for g in GROUPS:
        Ss = prep_group(P, g)
        print(f"{g}: {len(Ss)} instruments; first dates " + ", ".join(f"{s[:7]} {S['d'][0].date()}" for s, S in Ss.items()) + f"; half-spread used (bp of price): " + ", ".join(f"{s[:6]} {S['hs'] / np.median(S['c']) * 1e4:.2f}" for s, S in Ss.items()))
        bases = {s: baseline_one(S, 1, FROM, LAST) for s, S in Ss.items()}
        for side in SIDES:
            counts = {Z: len(trades(Ss, Z, side, FROM, LAST, {s: 0.0 for s in Ss})) for Z in ZS}
            print(f"   {'long ' if side > 0 else 'short'} trade counts (all sample, no returns shown): " + ", ".join(f"Z {Z}: {n}" for Z, n in counts.items()))
        for S in Ss.values():
            assert all(S["wd"][i + 1] > S["wd"][i] for i in range(70, len(S["d"]) - 1) if R5.eligible(S, i, 1))
        # placebo: random eligible long entries must have an excess near zero
        allr = [(s, i) for s, S in Ss.items() for i in range(70, len(S["d"]) - 1) if R5.eligible(S, i, 1)]
        pick = rng.choice(len(allr), size=min(2000, len(allr)), replace=False)
        ex = [R5.trade_net(Ss[allr[j][0]], allr[j][1], 1, 1) - bases[allr[j][0]] for j in pick]
        print(f"   placebo: {len(ex)} random long entries, mean excess {np.mean(ex):+.2f} bp (should be near 0)")
    print("weekend-rule assertions passed")
    print("DRY RUN OK")


def cash_index_stream():
    """Round 286's primary cell, 8 cash indices 1990-2017, cost 5 bp: daily mean net bps on trade days."""
    import round286_dip_reversal_independent_confirmation as R6
    Ss = {n: R6.load(n) for n in R6.NAMES}
    tr = R6.run_window(Ss, R6.FROM, R6.TO, 2.0)
    return tr.groupby("date")["net"].mean()


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    P = R8.prep()
    out = {"cells": {}, "per_inst": {}}
    bases = {}
    allS = {}
    for g in GROUPS:
        Ss = prep_group(P, g)
        allS[g] = Ss
        bases[g] = {side: {s: baseline_one(S, side, FROM, LAST) for s, S in Ss.items()} for side in SIDES}
    print(f"{'group':>7} {'side':>5} {'Z':>4} | {'window':>10} {'n':>6} {'net':>7} {'excess':>7} {'win':>6} {'P(net)':>7} {'P(exc)':>7}")
    streams = {}
    for g in GROUPS:
        for side in SIDES:
            for Z in ZS:
                tr = trades(allS[g], Z, side, FROM, LAST, bases[g][side])
                for wname, lo, hi in (("all", FROM, LAST), ("2000-2012", FROM, SPLIT - pd.Timedelta(days=1)), ("2013-2026", SPLIT, LAST)):
                    t = tr[(tr["date"] >= lo) & (tr["date"] <= hi)]
                    s = summarize(t)
                    out["cells"][f"{g}|{side}|{Z}|{wname}"] = s
                    if wname == "all":
                        print(f"{g:>7} {'long' if side > 0 else 'short':>5} {Z:>4.1f} | {wname:>10} {s['n']:>6} {s['mean']:>+7.2f} {s['excess']:>+7.2f} {s['win']:>6.1%} {s['P']:>7.3f} {s['Pex']:>7.3f}", flush=True)
                if Z == 2.0:
                    streams[(g, side)] = tr
    # primary hypotheses
    verdicts = {}
    print(f"\nPRIMARY HYPOTHESES (Z = 2, BONF {BONF:.5f}):")
    for g in GROUPS:
        for side in SIDES:
            c = lambda Z, w: out["cells"][f"{g}|{side}|{Z}|{w}"]
            a = c(2.0, "all")["mean"] > 0 and c(2.0, "all")["P"] >= BONF
            b = c(2.0, "all")["Pex"] >= BONF
            h1, h2 = c(2.0, "2000-2012"), c(2.0, "2013-2026")
            cc = h1["n"] >= 20 and h2["n"] >= 20 and h1["excess"] > 0 and h2["excess"] > 0
            d = c(1.0, "all")["mean"] < c(1.5, "all")["mean"] < c(2.0, "all")["mean"]
            tr = streams[(g, side)]
            per = {}
            for s in allS[g]:
                t = tr[tr["inst"] == s]
                if len(t) >= 20:
                    per[s] = dict(n=int(len(t)), net=float(t["net"].mean()), excess=float(t["ex"].mean()))
            out["per_inst"][f"{g}|{side}"] = per
            e = len(per) > 0 and sum(1 for v in per.values() if v["excess"] > 0) >= 2.0 / 3.0 * len(per)
            ok = bool(a and b and cc and d and e)
            verdicts[f"{g}|{side}"] = dict(a=bool(a), b=bool(b), c=bool(cc), d=bool(d), e=bool(e), instruments_tested=len(per), confirmed=ok)
            print(f"  {g:>7} {'long' if side > 0 else 'short':>5}: (a) net>0 & P {a}, (b) P(excess) {b}, (c) both halves {cc} [n {h1['n']}/{h2['n']}], (d) dose-response {d}, (e) 2/3 of {len(per)} instruments {e} -> {'CONFIRMED' if ok else 'NOT CONFIRMED'}")
    out["verdicts"] = verdicts
    print("\nPer instrument (Z = 2 long dips, instruments with >= 20 trades): net / excess bp")
    for g in GROUPS:
        for s, v in out["per_inst"][f"{g}|1"].items():
            print(f"   {g:>7} {s:>11}: {v['n']:>4} trades, net {v['net']:+7.2f}, excess {v['excess']:+7.2f}")
    # descriptive: correlation with the cash-index stream
    idx = cash_index_stream()
    out["corr"] = {}
    print("\nDESCRIPTIVE: daily correlation of the Z = 2 long-dip stream with the Round 286 cash-index stream, 2000-2017 (zero on no-trade days):")
    for g in GROUPS:
        tr = streams[(g, 1)]
        s = tr.groupby("date")["net"].mean()
        lo, hi = pd.Timestamp("2000-01-01"), pd.Timestamp("2017-12-27")
        days = pd.bdate_range(lo, hi)
        a_ = s.reindex(days).fillna(0.0); b_ = idx.reindex(days).fillna(0.0)
        both = int(((s.reindex(days).notna()) & (idx.reindex(days).notna())).sum())
        cor = float(np.corrcoef(a_.values, b_.values)[0, 1])
        out["corr"][g] = dict(corr=cor, both_days=both, group_days=int(s.reindex(days).notna().sum()), index_days=int(idx.reindex(days).notna().sum()))
        print(f"   {g:>7}: correlation {cor:+.3f}; trade days group {out['corr'][g]['group_days']}, index {out['corr'][g]['index_days']}, both {both}")
    json.dump(out, open(os.path.join(HERE, "round291_results.json"), "w"), indent=1, default=float)
    print(f"Saved round291_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
