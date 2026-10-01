
"""
Round 285 (2026-10-01, PRE-REGISTERED): MULTI-DAY DIP REVERSAL on index CFDs (idea 3 of the brainstorm the trader approved: "go ahead with idea 3").
Hypothesis: after an index falls unusually over three days, the next one to three days tend to rebound (short-term reversal, the logic of the old "RSI(2)"
dip buys), and after an unusual rise they tend to give back; held 1-3 nights with MT5 broker's real swap and spreads, with every position FLAT BEFORE THE WEEKEND (so the
rule also works on a live Standard account). Prior (stated now): the effect was strong in 2000-2020 equity data and has decayed; the 2021-26 window is a bull
market, so any long entry looks good against zero. THEREFORE a cell must beat the UNCONDITIONAL baseline (same instrument, side, hold, weekday rule and window, no signal),
not just zero. The honest expectation is no survivor.
CORRECTION to what was said when this was proposed ("20 years of daily data"): the index CFD D1 history starts 2017-12-28 (SPN35 2020-11), ~2,200 bars, i.e. 9 years.

DATA: D1 closes (17:00-17:00 NY) of 11 index CFDs: US100, US500, US30, US2000, GER40, FRA40, EU50, JP225, HK50, AUS200, SPN35. UK100 is EXCLUDED, decided from the swap table before any
return was looked at: its current swap (long +12%/yr, short -20%/yr) is anomalous and applying it to history would spuriously credit longs. Bad prints (> 10 sigma or > 50%) zeroed as in
Round 279. The 12 -> 11 instruments are pooled; every instrument is traded separately and the daily mean across instruments with a trade is the unit of inference.
SIGNAL (causal at the close of day t): z3 = ln(close_t / close_t-3) / (sigma60_t x sqrt(3)), sigma60 = 60-day standard deviation of daily returns (Round 279's, includes day t).
  LONG after a DIP: z3 <= -Z (and, with the trend filter, close_t > SMA200_t). SHORT after a RIP: z3 >= +Z (and, with the trend filter, close_t < SMA200_t).
TRADE: enter at the close of day t, exit at the close of day t + H trading days, H in (1, 3). WEEKEND RULE: the exit must fall on a later weekday of the same week (exit weekday > entry
weekday and at most H + 2 calendar days after entry), so H = 1 allows entries Monday-Thursday and H = 3 Monday-Tuesday (holidays shift this slightly). One position per instrument at a time.
NET RETURN of a trade = side x (sum of the clean daily returns over the held days) + swap (the side's swap fraction per night x nights, 3 nights across the instrument's triple weekday,
Round 279's convention) - (half the median D1 spread at entry + the same at exit, as a fraction of price). MT5 broker's swap values are today's (disclosed: they overstate the long-side burden
before 2022); the 2021-11+ out-of-sample window uses a near-realistic swap.
CELLS: side (long dip, short rip) x Z (1.0, 1.5, 2.0) x trend filter (none, SMA200) x H (1, 3) = 24; ledger k = 870 + 24 = 894. IS = trades dated 2018-01-01 .. 2021-10-31 (SMA200 and sigma warm-up
cost the first year), OOS = 2021-11-01 .. 2026-09-30.
BASELINE: for each (instrument, side, H, window) the mean net return of the unconditional trade over every eligible entry day. EXCESS of a trade = its net return minus that baseline mean.
STATISTICS per cell and window: trades, win rate, mean net bps, mean excess bps, day-level bootstrap (dates as the unit, daily mean across instruments, 4,000 draws, seed 2851) P(mean net > 0) and
P(mean excess > 0). CANDIDATE (the repo's rule plus the baseline, fixed now): IS P(net > 0) >= 0.95 AND OOS P(net > 0) >= 1 - 0.01/894 AND OOS P(excess > 0) >= 0.95 AND OOS mean net > 0 AND OOS
trades >= 150; also Benjamini-Hochberg q = 0.10 over the 24 OOS one-sided p-values of the excess, reported separately from the net p-values.
PLACEBO (dry-run): random entry days with the same count and weekday rule must give an excess near zero.
POWER_NOTES: a 1-3 day index move has a standard deviation of ~1-3%; ~150-400 OOS trades give a standard error of the mean of ~10-25 bps (day-level less), so only a per-trade excess of
~30 bps or more is detectable; per-trade swap and spread costs are ~1-3 bps.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round280_swap_aware_long_short as R8

INDEX = [s for s in R8.INDICES if s != "UK100.cash"]
ZS, FILTERS, HS, SIDES = (1.0, 1.5, 2.0), ("none", "sma200"), (1, 3), (1, -1)
IS_FROM, OOS_FROM, LAST = pd.Timestamp("2018-01-01"), pd.Timestamp("2021-11-01"), pd.Timestamp("2026-09-30")
K_TOTAL = 870 + len(ZS) * len(FILTERS) * len(HS) * len(SIDES)
SEED, BOOT = 2851, 4000


def prep_series(P):
    S = {}
    for s in INDEX:
        c = P["close"][s].dropna()
        d = c.index
        r = P["ret"][s].reindex(d).fillna(0.0).values
        sd = (P["sigma"][s].reindex(d) / np.sqrt(252)).values
        lp = np.log(c.values)
        z3 = np.full(len(c), np.nan)
        z3[3:] = (lp[3:] - lp[:-3]) / (sd[3:] * np.sqrt(3))
        sma = c.rolling(200).mean().values
        nights = np.ones(len(c))
        wd = d.weekday.values
        nights[1:] = np.where((wd[:-1] == P["trip"][s]), 3.0, 1.0)
        S[s] = dict(d=d, c=c.values, r=r, z3=z3, sma=sma, nights=nights, wd=wd, hs=P["hs"][s], fl=P["frac_l"][s], fs=P["frac_s"][s])
    return S


def eligible(S, i, H):
    d = S["d"]
    if i + H >= len(d):
        return False
    return S["wd"][i + H] > S["wd"][i] and (d[i + H] - d[i]).days <= H + 2


def trade_net(S, i, H, side):
    held = slice(i + 1, i + H + 1)
    gross = side * float(S["r"][held].sum())
    f = S["fl"] if side > 0 else S["fs"]
    swap = f * float(S["nights"][held].sum())
    cost = S["hs"] / S["c"][i] + S["hs"] / S["c"][i + H]
    return (gross + swap - cost) * 1e4


def baseline(Ss, H, side, lo, hi):
    out = {}
    for s, S in Ss.items():
        v = [trade_net(S, i, H, side) for i in range(len(S["d"])) if lo <= S["d"][i] <= hi and not np.isnan(S["sma"][i]) and eligible(S, i, H)]
        out[s] = float(np.mean(v)) if v else np.nan
    return out


def cell_trades(Ss, Z, flt, H, side):
    rows = []
    for s, S in Ss.items():
        i = 200
        n = len(S["d"])
        while i < n - H:
            ok = eligible(S, i, H) and np.isfinite(S["z3"][i]) and np.isfinite(S["sma"][i])
            if ok:
                if side > 0:
                    ok = S["z3"][i] <= -Z and (flt == "none" or S["c"][i] > S["sma"][i])
                else:
                    ok = S["z3"][i] >= Z and (flt == "none" or S["c"][i] < S["sma"][i])
            if ok:
                rows.append((s, S["d"][i], trade_net(S, i, H, side)))
                i += H
            else:
                i += 1
    return pd.DataFrame(rows, columns=["inst", "date", "net"])


def boot_p(x, seed=SEED):
    x = np.asarray(x, float)
    if len(x) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), (BOOT, len(x)))
    return float(np.mean(x[idx].mean(axis=1) > 0))


def window_stats(tr, base, lo, hi):
    y = tr[(tr["date"] >= lo) & (tr["date"] <= hi)].copy()
    if len(y) < 5:
        return dict(n=int(len(y)), mean=float("nan"), excess=float("nan"), win=float("nan"), P=float("nan"), Pex=float("nan"))
    y["ex"] = y["net"] - y["inst"].map(base)
    d = y.groupby("date")[["net", "ex"]].mean()
    return dict(n=int(len(y)), mean=float(y["net"].mean()), excess=float(y["ex"].mean()), win=float((y["net"] > 0).mean()), P=boot_p(d["net"].values), Pex=boot_p(d["ex"].values))


def bh(ps, q=0.10):
    p = np.array(ps, float); o = np.argsort(p); m = len(p); ok = np.zeros(m, bool); thr = -1
    for r, i in enumerate(o, 1):
        if p[i] <= q * r / m:
            thr = r
    if thr > 0:
        ok[o[:thr]] = True
    return ok


def dry_run():
    P = R8.prep(); Ss = prep_series(P)
    print(f"{len(Ss)} instruments; first signal dates " + ", ".join(f"{s[:6]} {S['d'][200].date()}" for s, S in list(Ss.items())[:4]))
    isb, oob = (IS_FROM, OOS_FROM - pd.Timedelta(days=1)), (OOS_FROM, LAST)
    for H in HS:
        for side in SIDES:
            b1, b2 = baseline(Ss, H, side, *isb), baseline(Ss, H, side, *oob)
            print(f"baseline H {H} {'long' if side > 0 else 'short'}: IS mean net per trade {np.nanmean(list(b1.values())):+.1f} bps, OOS {np.nanmean(list(b2.values())):+.1f} bps (unconditional, all eligible days)")
    # weekend rule and placebo
    S = Ss["US100.cash"]
    assert all(S["wd"][i + 3] > S["wd"][i] for i in range(200, len(S["d"]) - 3) if eligible(S, i, 3))
    print("weekend-rule assertion passed (no eligible H=3 trade crosses a weekend)")
    rng = np.random.default_rng(4)
    tr = cell_trades(Ss, 1.5, "none", 1, 1)
    base = baseline(Ss, 1, 1, OOS_FROM, LAST)
    allrows = []
    for s, Sx in Ss.items():
        el = [i for i in range(200, len(Sx["d"]) - 1) if eligible(Sx, i, 1) and Sx["d"][i] >= OOS_FROM]
        allrows += [(s, Sx["d"][i]) for i in el]
    pick = rng.choice(len(allrows), size=int((tr["date"] >= OOS_FROM).sum()), replace=False)
    ex = [trade_net(Ss[allrows[j][0]], int(np.searchsorted(Ss[allrows[j][0]]["d"], allrows[j][1])), 1, 1) - base[allrows[j][0]] for j in pick]
    print(f"placebo: {len(ex)} random OOS long entries (H 1) have mean excess {np.mean(ex):+.1f} bps (should be near 0)")
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    P = R8.prep(); Ss = prep_series(P)
    isb, oob = (IS_FROM, OOS_FROM - pd.Timedelta(days=1)), (OOS_FROM, LAST)
    bases = {(H, side, w): baseline(Ss, H, side, *rng_) for H in HS for side in SIDES for w, rng_ in (("IS", isb), ("OOS", oob))}
    rows = []
    print(f"{'side':>5} {'Z':>4} {'filter':>6} {'H':>2} | {'IS n':>5} {'mean':>7} {'exc':>7} {'P':>5} | {'OOS n':>5} {'mean':>7} {'exc':>7} {'win':>5} {'P':>5} {'Pex':>5}")
    for side in SIDES:
        for Z in ZS:
            for flt in FILTERS:
                for H in HS:
                    tr = cell_trades(Ss, Z, flt, H, side)
                    i = window_stats(tr, bases[(H, side, "IS")], *isb); o = window_stats(tr, bases[(H, side, "OOS")], *oob)
                    rows.append(dict(side=side, Z=Z, flt=flt, H=H, IS=i, OOS=o))
                    print(f"{'long' if side > 0 else 'short':>5} {Z:>4.1f} {flt:>6} {H:>2} | {i['n']:>5} {i['mean']:>+7.1f} {i['excess']:>+7.1f} {i['P']:>5.2f} | {o['n']:>5} {o['mean']:>+7.1f} {o['excess']:>+7.1f} {o['win']:>5.1%} {o['P']:>5.2f} {o['Pex']:>5.2f}", flush=True)
    cand = [r for r in rows if r["IS"]["P"] >= 0.95 and r["OOS"]["P"] >= 1 - 0.01 / K_TOTAL and r["OOS"]["Pex"] >= 0.95 and r["OOS"]["mean"] > 0 and r["OOS"]["n"] >= 150]
    elig = [r for r in rows if r["OOS"]["n"] >= 150]
    okx = bh([1 - r["OOS"]["Pex"] for r in elig], 0.10); okn = bh([1 - r["OOS"]["P"] for r in elig], 0.10)
    print(f"\nCANDIDATES (IS P >= 0.95, OOS P(net) >= {1 - 0.01 / K_TOTAL:.6f}, OOS P(excess) >= 0.95, OOS mean > 0, n >= 150): {len(cand)} of {len(rows)}; "
          f"Benjamini-Hochberg q=0.10 over {len(elig)} cells: excess {int(okx.sum())}, net {int(okn.sum())}")
    ex = np.array([r["OOS"]["excess"] for r in rows if np.isfinite(r["OOS"]["excess"])])
    print(f"OOS mean excess over the unconditional baseline across all {len(ex)} cells: mean {ex.mean():+.1f} bps, positive in {np.mean(ex > 0):.0%}")
    for side in SIDES:
        e = np.array([r["OOS"]["excess"] for r in rows if r["side"] == side and np.isfinite(r["OOS"]["excess"])])
        print(f"   {'long dips' if side > 0 else 'short rips'}: mean OOS excess {e.mean():+.1f} bps, positive in {np.mean(e > 0):.0%}")
    json.dump(dict(rows=rows, n_candidates=len(cand), bh_excess=int(okx.sum()), bh_net=int(okn.sum()), k_total=K_TOTAL), open(os.path.join(HERE, "round285_results.json"), "w"), indent=1, default=float)
    print(f"Saved round285_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
