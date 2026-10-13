"""
Round 280 (2026-10-01, PRE-REGISTERED, DESCRIPTIVE -- no ledger row): a SWAP-AWARE long-short version of the Round 279 multi-asset portfolio.
the trader: "go ahead with the swap-aware long-short version" (after Round 279 showed MT5 broker's swap, about -4.3% a year on the trend sleeve, eats more
than all of the +2.7% a year the trend sleeve earns before costs).

WHAT THE SWAP TABLE SAYS (looked at before writing this, no returns involved): MT5 broker's swap is asymmetric. Indices and metals: the LONG side costs
-5% to -17% a year, the SHORT side about 0 (+0.6% .. -4.6%). Oil/heating oil: long earns +17..+21% a year, short costs -76..-95%; natural gas the
reverse; most agri: short earns +1..+6%, long costs -8..-28%; FX: one side earns up to +2% (AUD crosses, USDJPY, USDCHF long), the other pays up to -8%.
So the realistic way to trade long-short at MT5 broker is to hold, in each instrument, the side that does not bleed. This round tests that, and nothing else.

VARIANTS (each a vol-targeted book exactly as in Round 279: weights sign/sigma_60/N, whole book scaled to V_T = 8% a year from its own trailing
63-day volatility, 5x cap, decided at the D1 close for the next bar; same costs; same windows):
  A0  Round 279 trend, unchanged (the baseline; the dry-run requires that it reproduces Round 279's net series to 1e-12).
  A1  GATED trend: the trend vote of Round 253 (20/60/120/250 days) as before, but a side may be held only if its swap, as an annual fraction of price,
      is >= -G (G = 2% a year, fixed now). A vote on a gated side means FLAT (the instrument is dropped from N_t that day). Informational
      sensitivity, NOT selected from: G = 0% and G = 5%.
  A2  CARRY HARVEST: in every instrument whose better side earns >= +1% a year, hold that side all the time (inverse-vol, same scaling), no trend
      signal. Pure swap harvesting; price moves are the risk.
  A3  A1 and A2 at 50/50 (each at V_T).
  B   the US100 POC leg of Round 279 scaled to V_T (unchanged).
CANDIDATE PORTFOLIOS (two, fixed now): P1 = 50% A1 + 50% B; P2 = 1/3 A1 + 1/3 A2 + 1/3 B. All on the common window 2021-11-01 .. 2026-09-30.
BENCHMARKS and METRICS: unchanged from Round 279 (US100, gold, 12-index basket buy and hold, with swap and without financing; also scaled to the
candidate's volatility; Sharpe, Sortino, maximum drawdown, Calmar, Ulcer, positive months, worst month, R-squared of log equity, days under water;
20-day block bootstrap, 5,000 draws, seed 2801, of each candidate's Sharpe and of its difference to US100 buy and hold with swap). Also reported: the
share of days each book is net long, its mean net exposure, and the swap actually earned or paid per year.
DECISION RULE (fixed now, same as Round 279): a candidate is worth building only if its common-window net Sharpe >= 0.8 AND its maximum drawdown
<= 8% at V_T = 8% AND its Sharpe is positive in both IS (to 2025-06) and OOS (from 2025-07) AND the bootstrap 95% interval of its Sharpe difference to
the CFD-financed US100 buy and hold excludes zero on the positive side. Two candidates are tested; the 95% interval is NOT widened for that, which is
lenient (stated). Otherwise "does not beat buy and hold".
DISCLOSED BIASES (all in Round 279, plus these): (1) swaps are today's values applied to the whole history, so the choice of the cheap side uses
information the 2005 trader did not have (the index long/short asymmetry is structural, the commodity one reflects today's curve shape: backwardated
oil, contango natgas/agri) and the carry book A2 is partly a static bet on the direction of those markets over the sample; (2) cash CFDs on futures
embed roll costs in price AND swap, so the swap credit on oil may double-count; (3) shorting indices over 2021-26 (a bull market) is hurt by
direction, which is the honest cost of avoiding the long-side swap. POWER_NOTES: a 5-year daily Sharpe has a standard error of ~0.45; differences
below ~0.6 are not distinguishable. Descriptive: nothing here is selected on this sample except through the fixed G.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round253_multiday_trend_tom as T
import round279_multi_asset_portfolio_vs_buy_hold as R9
from mt5 import universe as U

SYMS, INDICES, VT, SMAX = R9.SYMS, R9.INDICES, R9.VT, R9.SMAX
COMMON, LONGW, OOS = R9.COMMON, R9.LONGW, R9.OOS
metrics, window = R9.metrics, R9.window
G_MAIN, G_SENS, CARRY_MIN = 0.02, (0.0, 0.05), 0.01
SEED, B, BLOCK = 2801, 5000, 20


def prep():
    """Everything shared by every variant (loaded once)."""
    D1 = {s: T.load_d1(s) for s in SYMS}
    for s in SYMS:
        T.REF_PX[s] = float(D1[s]["close"].iloc[-1])
    idx = pd.DatetimeIndex(sorted(set().union(*[set(D1[s].index) for s in SYMS])))
    close = pd.DataFrame({s: D1[s]["close"] for s in SYMS}).reindex(idx)
    ret = pd.DataFrame({s: D1[s]["close"].pct_change() for s in SYMS}).reindex(idx)
    sd60 = ret.rolling(60, min_periods=40).std().shift(1)
    bad = (ret.abs() > 10 * sd60) | (ret.abs() > 0.5)
    ret = ret.mask(bad, 0.0)
    sig = pd.DataFrame({s: T.tsmom_state(D1[s]["close"]) for s in SYMS}).reindex(idx).ffill(limit=5)
    sigma = ret.rolling(60, min_periods=40).std() * np.sqrt(252)
    frac_l, frac_s, trip, hs, comm = {}, {}, {}, {}, {}
    for s in SYMS:
        sp = T.spec(s)
        pt = float(sp["point"]); ref = T.REF_PX[s]
        frac_l[s] = float(sp["swap_long"]) * pt / ref
        frac_s[s] = float(sp["swap_short"]) * pt / ref
        trip[s] = T.triple_pyweekday(s)
        hs[s] = float(np.median(D1[s]["spread"])) * pt / 2.0
        comm[s] = (5.0 / 2.0) / (T.usd_per_pu(s, ref) * ref) if U.GROUP[s] in R9.COMM_GROUPS else 0.0
    return dict(D1=D1, idx=idx, close=close, ret=ret, sig=sig, sigma=sigma, frac_l=frac_l, frac_s=frac_s, trip=trip, hs=hs, comm=comm)


def book(P, direction, valid):
    """Vol-targeted book from a direction matrix (+1/-1 decided at the close of t) and a validity mask; returns net, gross, swap, trade, info."""
    idx, ret, close, sigma = P["idx"], P["ret"], P["close"], P["sigma"]
    n_t = valid.sum(axis=1).replace(0, np.nan)
    A = (direction.where(valid) / sigma.where(valid)).div(n_t, axis=0).fillna(0.0)
    gross_raw = (A.shift(1) * ret.fillna(0.0)).sum(axis=1)
    vol_raw = gross_raw.rolling(63, min_periods=40).std().shift(1) * np.sqrt(252)
    scale = (VT / vol_raw).clip(upper=SMAX)
    W = A.shift(1).mul(scale, axis=0).fillna(0.0)
    wd_prev = pd.Series(idx.weekday, index=idx).shift(1)
    swap = pd.Series(0.0, index=idx)
    trade = pd.Series(0.0, index=idx)
    for s in SYMS:
        w = W[s]
        nights = np.where(wd_prev.values == P["trip"][s], 3.0, 1.0)
        f = np.where(w.values > 0, P["frac_l"][s], np.where(w.values < 0, P["frac_s"][s], 0.0))
        swap += pd.Series(np.abs(w.values) * f * nights, index=idx)
        turn = (w - w.shift(1).fillna(0.0)).abs()
        px = close[s].shift(1).ffill()
        trade += (turn * (P["hs"][s] / px + P["comm"][s])).fillna(0.0)
    gross = (W * ret.fillna(0.0)).sum(axis=1)
    net = gross + swap - trade
    first = valid.sum(axis=1).gt(0).idxmax()
    start = idx[np.searchsorted(idx, first) + 70] if np.searchsorted(idx, first) + 70 < len(idx) else idx[-1]
    lev = W.abs().sum(axis=1)
    netexp = W.sum(axis=1)
    c = (idx >= COMMON[0]) & (idx <= COMMON[1])
    info = dict(start=str(start.date()), mean_lev=float(lev[lev > 0].mean()), max_lev=float(lev.max()), net_long_share=float((netexp[c] > 0).mean()),
                mean_net_exposure=float(netexp[c].mean()), swap_ann=float(swap[start:].mean() * 252), trade_ann=float(trade[start:].mean() * 252),
                gross_ann=float(gross[start:].mean() * 252), swap_ann_common=float(swap[c].mean() * 252), gross_ann_common=float(gross[c].mean() * 252))
    return net[start:], gross[start:], info


def sides(P, G):
    yl = {s: P["frac_l"][s] * 365 for s in SYMS}
    ys = {s: P["frac_s"][s] * 365 for s in SYMS}
    allowL = pd.Series({s: (G is None) or yl[s] >= -G for s in SYMS})
    allowS = pd.Series({s: (G is None) or ys[s] >= -G for s in SYMS})
    return allowL, allowS, yl, ys


def trend_book(P, G):
    allowL, allowS, _, _ = sides(P, G)
    sig = P["sig"]
    ok = (sig.gt(0) & allowL.reindex(sig.columns).values[None, :]) | (sig.lt(0) & allowS.reindex(sig.columns).values[None, :])
    valid = sig.notna() & (sig != 0) & P["sigma"].notna() & (P["sigma"] > 0) & ok
    return book(P, np.sign(sig), valid)


def carry_book(P):
    _, _, yl, ys = sides(P, None)
    d, keep = {}, []
    for s in SYMS:
        best = max(yl[s], ys[s])
        if best >= CARRY_MIN:
            d[s] = 1.0 if yl[s] >= ys[s] else -1.0
            keep.append(s)
    idx = P["idx"]
    direction = pd.DataFrame({s: d.get(s, np.nan) for s in SYMS}, index=idx)
    have = P["close"].notna() & P["sigma"].notna() & (P["sigma"] > 0)
    valid = have & direction.notna()
    # a book needs 250 bars of history like the trend books, for a comparable start; use the same first-signal rule via sig availability
    valid = valid & P["sig"].notna()
    return book(P, direction.fillna(0.0), valid), keep, d


def dry_run():
    """Sanity checks that must pass before the run: A0 reproduces Round 279 exactly; gating can only drop signals; carry sides are what the table says."""
    P = prep()
    n9, g9, i9, *_ = R9.build_trend()
    n0, g0, i0 = trend_book(P, None)
    common = n9.index.intersection(n0.index)
    diff = float((n9.reindex(common) - n0.reindex(common)).abs().max())
    print(f"A0 vs Round 279 trend net: max abs daily difference {diff:.2e} over {len(common)} days (must be < 1e-12)")
    assert diff < 1e-12, "A0 does not reproduce Round 279"
    n1, g1, i1 = trend_book(P, G_MAIN)
    allowL, allowS, yl, ys = sides(P, G_MAIN)
    print(f"G=2%: long allowed in {int(allowL.sum())}/{len(SYMS)} instruments, short allowed in {int(allowS.sum())}/{len(SYMS)}; index longs allowed: "
          f"{[s for s in INDICES if allowL[s]]}")
    (nc, gc, ic), keep, d = carry_book(P)
    print(f"carry book: {len(keep)} instruments: " + ", ".join(f"{s}{'+' if d[s] > 0 else '-'}" for s in keep))
    print(f"A1 mean lev {i1['mean_lev']:.2f}, net long share {i1['net_long_share']:.0%}, swap {i1['swap_ann']:+.2%}/yr; carry book swap {ic['swap_ann']:+.2%}/yr, mean lev {ic['mean_lev']:.2f}")
    assert i1["swap_ann"] > i0["swap_ann"], "gating must improve the swap line"
    assert ic["swap_ann"] > 0, "carry book must earn swap"
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    P = prep()
    books = {}
    for name, G in (("A0 trend (Round 279)", None), ("A1 gated trend (G=2%)", G_MAIN), ("A1 gated, G=0% (sens.)", 0.0), ("A1 gated, G=5% (sens.)", 0.05)):
        n, g, info = trend_book(P, G)
        books[name] = (n, g, info)
        print(f"{name:>26}: from {info['start']}; mean lev {info['mean_lev']:.2f}x; gross {info['gross_ann']:+.2%}, swap {info['swap_ann']:+.2%}, costs {-info['trade_ann']:+.2%} per year; "
              f"COMMON window: net long {info['net_long_share']:.0%} of days, mean net exposure {info['mean_net_exposure']:+.2f}, swap {info['swap_ann_common']:+.2%}", flush=True)
    (nc, gc, ic), keep, d = carry_book(P)
    books["A2 carry harvest"] = (nc, gc, ic)
    print(f"{'A2 carry harvest':>26}: {len(keep)} instruments ({', '.join(s + ('+' if d[s] > 0 else '-') for s in keep)}); mean lev {ic['mean_lev']:.2f}x; gross {ic['gross_ann']:+.2%}, "
          f"swap {ic['swap_ann']:+.2%}, costs {-ic['trade_ann']:+.2%} per year; COMMON: net long {ic['net_long_share']:.0%} of days, swap {ic['swap_ann_common']:+.2%}  ({time.time() - t0:.0f}s)", flush=True)
    ser = {k: v[0] for k, v in books.items()}
    a1, a2 = ser["A1 gated trend (G=2%)"], ser["A2 carry harvest"]
    poc = R9.poc_sleeve(); poc = poc * (VT / (poc.std() * np.sqrt(252)))
    ser["B POC leg US100 (scaled)"] = poc
    cc = pd.concat([a1, a2], axis=1, keys=["a", "c"]).dropna()
    ser["A3 gated trend + carry (50/50)"] = 0.5 * cc["a"] + 0.5 * cc["c"]
    c3 = pd.concat([a1, a2, poc], axis=1, keys=["a", "c", "b"]).dropna()
    ser["P1 gated trend + POC (50/50)"] = 0.5 * c3["a"] + 0.5 * c3["b"]
    ser["P2 gated trend + carry + POC (1/3 each)"] = (c3["a"] + c3["c"] + c3["b"]) / 3.0
    ser["(R279) A0 trend + POC (50/50)"] = 0.5 * pd.concat([ser["A0 trend (Round 279)"], poc], axis=1, keys=["a", "b"]).dropna()["a"] + 0.5 * pd.concat([ser["A0 trend (Round 279)"], poc], axis=1, keys=["a", "b"]).dropna()["b"]
    # benchmarks
    ret, close = P["ret"], P["close"]
    def bh(sym, swap=True):
        r = ret[sym].copy()
        if swap:
            wdp = pd.Series(r.index.weekday, index=r.index).shift(1)
            r = r + P["frac_l"][sym] * np.where(wdp.values == P["trip"][sym], 3.0, 1.0)
        return r.where(close[sym].notna())
    ser["Buy & hold US100, CFD with swap"] = bh("US100.cash", True)
    ser["Buy & hold US100, no financing"] = bh("US100.cash", False)
    ser["Buy & hold gold, CFD with swap"] = bh("XAUUSD", True)
    ser["Buy & hold 12 index CFDs, with swap"] = pd.concat([bh(s, True) for s in INDICES], axis=1).mean(axis=1, skipna=True)
    out = {"books": {k: v[2] for k, v in books.items()}, "windows": {}}
    print("\n" + "=" * 150)
    for wname, (lo, hi) in (("COMMON 2021-11 .. 2026-09", COMMON), ("TREND-LONG 2005 .. 2026-09", LONGW), ("IS 2021-11 .. 2025-06", (COMMON[0], OOS - pd.Timedelta(days=1))), ("OOS 2025-07 .. 2026-09", (OOS, COMMON[1]))):
        print(f"\n=== {wname} ===")
        print(f"{'series':>42} {'return':>7} {'vol':>6} {'Sharpe':>7} {'Sortino':>8} {'maxDD':>7} {'Calmar':>7} {'Ulcer':>6} {'up mo.':>6} {'worst mo':>8} {'R2':>5} {'under(d)':>8}")
        out["windows"][wname] = {}
        for name, r in ser.items():
            m = metrics(window(r, lo, hi))
            if m is None:
                continue
            out["windows"][wname][name] = m
            print(f"{name:>42} {m['ret']:>+7.1%} {m['vol']:>6.1%} {m['sharpe']:>7.2f} {m['sortino']:>8.2f} {m['maxdd']:>7.1%} {m['calmar']:>7.2f} {m['ulcer']:>6.1%} {m['pos_months']:>6.0%} {m['worst_month']:>8.1%} {m['r2']:>5.2f} {m['underwater_days']:>8}")
    print("\n=== Buy and hold scaled to each candidate's volatility, COMMON window ===")
    cands = ("P1 gated trend + POC (50/50)", "P2 gated trend + carry + POC (1/3 each)")
    for cname in cands:
        tv = window(ser[cname], *COMMON).std()
        for name in ("Buy & hold US100, CFD with swap", "Buy & hold gold, CFD with swap", "Buy & hold 12 index CFDs, with swap"):
            r = window(ser[name], *COMMON).dropna(); k = tv / r.std(); m = metrics(r * k)
            out["windows"].setdefault("scaled_" + cname, {})[name] = dict(m, k=float(k))
            print(f"{cname[:26]:>26} | {name:>38}: x{k:.2f} -> return {m['ret']:+.1%}, Sharpe {m['sharpe']:.2f}, max DD {m['maxdd']:.1%}")
    print("\n=== Sharpe confidence (20-day block bootstrap, COMMON window) vs US100 CFD buy and hold ===")
    ref = window(ser["Buy & hold US100, CFD with swap"], *COMMON)
    R9.RNG_SEED, R9.BOOT_B = SEED, B
    out["boot"] = {}
    for name in ("A1 gated trend (G=2%)", "A2 carry harvest", "B POC leg US100 (scaled)") + cands:
        ci, dd = R9.boot_sharpe_diff(window(ser[name], *COMMON), ref, B=B, block=BLOCK, seed=SEED)
        out["boot"][name] = dict(ci=ci.tolist(), diff=dd.tolist())
        print(f"{name:>42}: Sharpe 95% [{ci[0]:.2f}, {ci[1]:.2f}]; minus US100 CFD B&H: median {dd[1]:+.2f}, 95% [{dd[0]:+.2f}, {dd[2]:+.2f}]")
    print("\n=== Calendar-year Sharpe ===")
    ycols = ["A0 trend (Round 279)", "A1 gated trend (G=2%)", "A2 carry harvest", "P1 gated trend + POC (50/50)", "Buy & hold US100, CFD with swap"]
    print(f"{'year':>6} " + "".join(f"{c[:26]:>28}" for c in ycols))
    out["yearly"] = {}
    for y in range(2005, 2027):
        row = []
        for c in ycols:
            r = ser[c][ser[c].index.year == y].dropna()
            row.append(float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 100 and r.std() > 0 else None)
        out["yearly"][str(y)] = dict(zip(ycols, row))
        print(f"{y:>6} " + "".join(f"{(f'{v:+.2f}' if v is not None else '-'):>28}" for v in row))
    out["decision"] = {}
    for cname in cands:
        ab = out["windows"]["COMMON 2021-11 .. 2026-09"][cname]
        is_s = out["windows"]["IS 2021-11 .. 2025-06"][cname]["sharpe"]; oos_s = out["windows"]["OOS 2025-07 .. 2026-09"][cname]["sharpe"]
        dd = out["boot"][cname]["diff"]
        ok = ab["sharpe"] >= 0.8 and ab["maxdd"] >= -0.08 and is_s > 0 and oos_s > 0 and dd[0] > 0
        out["decision"][cname] = dict(worth_building=bool(ok), sharpe=ab["sharpe"], maxdd=ab["maxdd"], is_sharpe=is_s, oos_sharpe=oos_s, diff_lo=dd[0])
        print(f"DECISION {cname}: Sharpe {ab['sharpe']:.2f} (>= 0.8?), max DD {ab['maxdd']:.1%} (<= 8%?), IS {is_s:+.2f} / OOS {oos_s:+.2f}, diff lower bound {dd[0]:+.2f} (> 0?) -> "
              f"{'WORTH BUILDING' if ok else 'does NOT beat buy and hold'}")
    eq = {}
    for name, r in ser.items():
        rr = window(r, COMMON[0], COMMON[1]).dropna(); e = (1 + rr).cumprod()
        eq[name] = dict(dates=[str(x.date()) for x in e.index[::5]], eq=[round(float(x), 4) for x in e.values[::5]])
    out["equity"] = eq
    json.dump(out, open(os.path.join(HERE, "round280_results.json"), "w"), indent=1, default=float)
    print(f"\nSaved round280_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
