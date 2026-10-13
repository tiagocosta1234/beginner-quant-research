"""
Round 279 (2026-10-01, PRE-REGISTERED, DESCRIPTIVE -- no ledger row): our best strategies combined across many assets, Sharpe ratio and
smoothness against buy and hold. the trader: "this underperforms the buy and hold for sure. what if we combined our most profitable strategies,
traded them in multiple assets, compare the sharpe ratio (a smooth curve is crucial)".

HONEST FRAMING (fixed now). The repo has no strategy with a demonstrated net-of-cost edge: the ledger holds 774 tested ideas and no candidate. The two
legs with the best (still unconfirmed) results are (1) multi-day time-series momentum (Round 253: positive before swap, its edge eaten by MT5 broker's swap on
the 9 instruments tested) and (2) the US100 POC leg (Round 249: +0.060 R net per trade, not significant). Diversification cannot create an edge; it can
raise a Sharpe ratio and smooth a curve only if the legs are positive and weakly correlated. This round measures exactly that, with the benchmark
the trader cares about.

SLEEVE A -- TREND, all 44 non-crypto MT5 broker instruments (12 indices, 5 metals, 4 energy, 7 agri, 15 FX, DXY; D1 bars from each instrument's first
bar, signals from 250 bars later): time-series momentum of Round 253: vote = sum of sign(close_t - close_t-L) for L in (20, 60, 120, 250), long if
> 0, short if < 0. Sizing: weight_i = sign_i / sigma_i,t / N_t (sigma = 60-day standard deviation of daily returns, annualised; N_t = instruments
with a signal), the whole book scaled each day by V_T / (trailing 63-day volatility of the unscaled book) with V_T = 8% a year and a 5x cap on the
scale. Decisions at the D1 close (17:00 New York) for the next bar. NO parameter is tuned (lookbacks, 60/63-day windows, V_T are the
published/standard values).
SLEEVE B -- the US100 POC leg (Round 249's exact trades, tick bid/ask fills, base costs) at $1,000 risk, daily P&L / $100,000, scaled to the same V_T by its
full-sample volatility (a scaling that uses no returns, only risk). The other instruments are not used: the POC leg lost on GER40 (Round 252).
PORTFOLIOS: A alone; B alone; "A + B": 50% of each (each at V_T) on the common window 2021-11-01 .. 2026-09-30.
BENCHMARKS (long only, daily): US100 buy and hold, XAUUSD buy and hold, equal-weight basket of the 12 index CFDs, each (i) as a CFD with MT5 broker's swap
(the realistic way to hold it at MT5) and (ii) with NO financing (what an ETF holder sees). Also shown scaled to the same volatility (a constant
multiplier, for drawdown and return comparison).
COSTS: MT5 broker's: swap = today's swap points per lot per night as a FRACTION of price (swap_long / swap_short by position side, charged at the 17:00
rollover that the position crosses, triple on the instrument's own weekday); half the median D1 spread per unit of turnover; commission $5 per lot round
trip on FX and metals (as Round 253). DISCLOSED BIASES: swaps are today's values applied to the whole history (interest rates, hence swaps, were lower
before 2022: this OVERSTATES the swap burden in 2000-2021); P&L is the instrument's own price return (no conversion of non-USD quote currencies); daily
bars, no intraday path; bad prints (> 10 sigma jumps) set to 0.
METRICS (daily net returns): annualised return and volatility, Sharpe (mean / sd x sqrt(252)), Sortino, maximum drawdown, Calmar, Ulcer index, share of
positive months, worst month, R-squared of the log equity curve against time (a straightness measure), longest time under water; the Sharpe
difference to US100 buy-and-hold with a 20-day moving-block bootstrap (5,000 draws, seed 2791) on the common window. WINDOWS: COMMON 2021-11-01 ..
2026-09-30; TREND-LONG 2005-01-01 .. 2026-09-30 (FX, gold, then indices as they appear); IS (before 2025-07-01) and OOS (from 2025-07-01).
DECISION RULE (fixed now): a combination is worth building only if, on the common window, its net Sharpe >= 0.8 AND its maximum drawdown <= 8% at
V_T = 8% AND its Sharpe is positive in both IS and OOS AND the bootstrap interval of its Sharpe difference to the CFD-financed US100 buy and hold
excludes zero on the positive side. Otherwise the result is "does not beat buy and hold".
POWER_NOTES: over 5 years a daily Sharpe has a standard error of ~0.45 (1/sqrt(years)); differences below ~0.6 are not distinguishable. The result is
descriptive: the trend sleeve was not selected on this sample.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round253_multiday_trend_tom as T
from mt5 import universe as U

CRYPTO = set(U.CRYPTO)
SYMS = [s for s in U.ALL if s not in CRYPTO]
INDICES = [s for s in U.INDICES if s in SYMS]
VT, SMAX = 0.08, 5.0
COMMON = (pd.Timestamp("2021-11-01"), pd.Timestamp("2026-09-30"))
LONGW = (pd.Timestamp("2005-01-01"), pd.Timestamp("2026-09-30"))
OOS = pd.Timestamp("2025-07-01")
COMM_GROUPS = ("fx", "metal")
RNG_SEED, BOOT_B, BLOCK = 2791, 5000, 20


def metrics(r):
    r = r.dropna()
    if len(r) < 60:
        return None
    mu, sd = r.mean() * 252, r.std() * np.sqrt(252)
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    mon = (1 + r).resample("ME").prod() - 1
    down = np.sqrt((np.minimum(r, 0) ** 2).mean()) * np.sqrt(252)
    t = np.arange(len(eq))
    le = np.log(eq.values)
    r2 = float(np.corrcoef(t, le)[0, 1] ** 2) if le.std() > 0 else 0.0
    under = (dd < -1e-12).values
    best = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        best = max(best, cur)
    return dict(n=len(r), ret=float(mu), vol=float(sd), sharpe=float(mu / sd) if sd > 0 else 0.0, sortino=float(mu / down) if down > 0 else 0.0,
                maxdd=float(dd.min()), calmar=float(mu / abs(dd.min())) if dd.min() < 0 else 0.0, ulcer=float(np.sqrt((dd ** 2).mean())),
                pos_months=float((mon > 0).mean()), worst_month=float(mon.min()), r2=r2, underwater_days=int(best), total=float(eq.iloc[-1] - 1))


def window(r, lo, hi):
    return r[(r.index >= lo) & (r.index <= hi)]


def boot_sharpe_diff(a, b, B=BOOT_B, block=BLOCK, seed=RNG_SEED):
    x = pd.concat([a, b], axis=1).dropna().values
    n = len(x)
    rng = np.random.default_rng(seed)
    nb = -(-n // block)
    out_a, out_d = [], []
    for _ in range(B):
        st = rng.integers(0, n - block, nb)
        idx = (st[:, None] + np.arange(block)[None, :]).ravel()[:n]
        s = x[idx]
        sa = s[:, 0].mean() / s[:, 0].std() * np.sqrt(252)
        sb = s[:, 1].mean() / s[:, 1].std() * np.sqrt(252)
        out_a.append(sa); out_d.append(sa - sb)
    return np.quantile(out_a, [0.025, 0.975]), np.quantile(out_d, [0.025, 0.5, 0.975])


def build_trend():
    D1 = {s: T.load_d1(s) for s in SYMS}
    for s in SYMS:
        T.REF_PX[s] = float(D1[s]["close"].iloc[-1])
    idx = sorted(set().union(*[set(D1[s].index) for s in SYMS]))
    idx = pd.DatetimeIndex(idx)
    close = pd.DataFrame({s: D1[s]["close"] for s in SYMS}).reindex(idx)
    ret = pd.DataFrame({s: D1[s]["close"].pct_change() for s in SYMS}).reindex(idx)
    sd60 = ret.rolling(60, min_periods=40).std().shift(1)
    bad = (ret.abs() > 10 * sd60) | (ret.abs() > 0.5)
    nbad = int(bad.sum().sum())
    ret = ret.mask(bad, 0.0)
    sig = pd.DataFrame({s: T.tsmom_state(D1[s]["close"]) for s in SYMS}).reindex(idx)
    sig = sig.ffill(limit=5)
    sigma = ret.rolling(60, min_periods=40).std() * np.sqrt(252)
    valid = sig.notna() & (sig != 0) & sigma.notna() & (sigma > 0)
    n_t = valid.sum(axis=1).replace(0, np.nan)
    A = (sig.where(valid) / sigma.where(valid)).div(n_t, axis=0).fillna(0.0)              # decided at the close of t
    gross_raw = (A.shift(1) * ret.fillna(0.0)).sum(axis=1)
    vol_raw = gross_raw.rolling(63, min_periods=40).std().shift(1) * np.sqrt(252)
    scale = (VT / vol_raw).clip(upper=SMAX)
    W = A.shift(1).mul(scale, axis=0).fillna(0.0)                                          # position held during t
    # costs
    frac_l, frac_s, trip, hs, comm = {}, {}, {}, {}, {}
    for s in SYMS:
        sp = T.spec(s)
        pt = float(sp["point"]); ref = T.REF_PX[s]
        frac_l[s] = float(sp["swap_long"]) * pt / ref
        frac_s[s] = float(sp["swap_short"]) * pt / ref
        trip[s] = T.triple_pyweekday(s)
        hs[s] = float(np.median(D1[s]["spread"])) * pt / 2.0
        comm[s] = 0.0
        if U.GROUP[s] in COMM_GROUPS:
            comm[s] = (5.0 / 2.0) / (T.usd_per_pu(s, ref) * ref)                            # half the round trip per side, as a fraction of notional
    wd_prev = pd.Series(idx.weekday, index=idx).shift(1)
    swap = pd.Series(0.0, index=idx)
    trade = pd.Series(0.0, index=idx)
    for s in SYMS:
        w = W[s]
        nights = np.where(wd_prev.values == trip[s], 3.0, 1.0)
        f = np.where(w.values > 0, frac_l[s], np.where(w.values < 0, frac_s[s], 0.0))
        swap += pd.Series(np.abs(w.values) * f * nights, index=idx)
        turn = (w - w.shift(1).fillna(0.0)).abs()
        px = close[s].shift(1).ffill()
        trade += (turn * (hs[s] / px + comm[s])).fillna(0.0)          # (before an instrument's first bar px is NaN: no position, no cost)
    gross = (W * ret.fillna(0.0)).sum(axis=1)
    net = gross + swap - trade
    first = valid.sum(axis=1).gt(0).idxmax()
    start = idx[np.searchsorted(idx, first) + 70] if np.searchsorted(idx, first) + 70 < len(idx) else idx[-1]
    lev = W.abs().sum(axis=1)
    info = dict(nbad=nbad, first=str(first.date()), start=str(start.date()), n_instr=int(valid.iloc[-1].sum()), max_lev=float(lev.max()), mean_lev=float(lev[lev > 0].mean()),
                swap_ann=float(swap[start:].mean() * 252), trade_ann=float(trade[start:].mean() * 252), gross_ann=float(gross[start:].mean() * 252))
    return net[start:], gross[start:], info, D1, ret, close, trip, frac_l


def poc_sleeve():
    import round249_mt5broker_poc_mt5 as R
    from forex.backtest import daily, run_strategy
    raw, cfd = R.load_cfd()
    _, per, _, _ = R.data_checks(raw, cfd)
    skip, _ = R.calendar_check(per)
    tr, days = run_strategy(cfd, R.BASE, skip_days=skip)
    d = daily(tr, days, 1000.0)
    r = (d["pnl"] / 100_000.0)
    r.index = pd.DatetimeIndex(r.index).normalize()
    return r


def main():
    t0 = time.time()
    net, gross, info, D1, ret, close, trip, frac_l = build_trend()
    print(f"trend sleeve: {len(SYMS)} instruments, {info['nbad']} bad prints zeroed, from {info['start']}; {info['n_instr']} active now; mean gross leverage {info['mean_lev']:.2f}x (max {info['max_lev']:.1f}x); "
          f"per year: gross {info['gross_ann']:+.1%}, swap {info['swap_ann']:+.2%}, trading costs {-info['trade_ann']:+.2%} ({time.time() - t0:.0f}s)", flush=True)
    poc = poc_sleeve()
    poc = poc * (VT / (poc.std() * np.sqrt(252)))
    # benchmarks
    def bh(sym, swap=True):
        r = ret[sym].copy()
        if swap:
            wdp = pd.Series(r.index.weekday, index=r.index).shift(1)
            r = r + frac_l[sym] * np.where(wdp.values == trip[sym], 3.0, 1.0)
        return r.where(close[sym].notna())
    basket_syms = INDICES
    def basket(swap=True):
        return pd.concat([bh(s, swap) for s in basket_syms], axis=1).mean(axis=1, skipna=True)
    series = {"Trend, 44 instruments (net)": net, "Trend (before swap and costs)": gross.reindex(net.index), "POC leg US100 (scaled)": poc,
              "Buy & hold US100, CFD with swap": bh("US100.cash", True), "Buy & hold US100, no financing": bh("US100.cash", False),
              "Buy & hold gold, CFD with swap": bh("XAUUSD", True), "Buy & hold gold, no financing": bh("XAUUSD", False),
              "Buy & hold 12 index CFDs, with swap": basket(True), "Buy & hold 12 index CFDs, no financing": basket(False)}
    common = pd.concat([net, poc], axis=1, keys=["a", "b"]).dropna()
    series["A + B (50/50), trend + POC"] = 0.5 * common["a"] + 0.5 * common["b"]
    out = {"info": info, "windows": {}}
    print("\n" + "=" * 150)
    for wname, (lo, hi) in (("COMMON 2021-11 .. 2026-09", COMMON), ("TREND-LONG 2005 .. 2026-09", LONGW), ("IS 2021-11 .. 2025-06", (COMMON[0], OOS - pd.Timedelta(days=1))), ("OOS 2025-07 .. 2026-09", (OOS, COMMON[1]))):
        print(f"\n=== {wname} ===")
        print(f"{'series':>40} {'return':>7} {'vol':>6} {'Sharpe':>7} {'Sortino':>8} {'maxDD':>7} {'Calmar':>7} {'Ulcer':>6} {'up mo.':>6} {'worst mo':>8} {'R2':>5} {'under(d)':>8}")
        out["windows"][wname] = {}
        for name, r in series.items():
            m = metrics(window(r, lo, hi))
            if m is None:
                continue
            out["windows"][wname][name] = m
            print(f"{name:>40} {m['ret']:>+7.1%} {m['vol']:>6.1%} {m['sharpe']:>7.2f} {m['sortino']:>8.2f} {m['maxdd']:>7.1%} {m['calmar']:>7.2f} {m['ulcer']:>6.1%} {m['pos_months']:>6.0%} {m['worst_month']:>8.1%} {m['r2']:>5.2f} {m['underwater_days']:>8}")
    # risk-matched buy and hold (constant multiplier to the vol of the trend sleeve on the common window)
    print("\n=== Buy and hold scaled to the same volatility as the combined portfolio (constant multiplier), COMMON window ===")
    comb = window(series["A + B (50/50), trend + POC"], *COMMON)
    tv = comb.std()
    for name in ("Buy & hold US100, CFD with swap", "Buy & hold US100, no financing", "Buy & hold gold, CFD with swap", "Buy & hold 12 index CFDs, with swap", "Buy & hold 12 index CFDs, no financing"):
        r = window(series[name], *COMMON).dropna()
        k = tv / r.std()
        m = metrics(r * k)
        out["windows"].setdefault("scaled", {})[name] = dict(m, k=float(k))
        print(f"{name:>40}: x{k:.2f} -> return {m['ret']:+.1%}, vol {m['vol']:.1%}, Sharpe {m['sharpe']:.2f}, max DD {m['maxdd']:.1%}")
    # bootstrap Sharpe CIs vs US100 CFD buy and hold
    print("\n=== Sharpe confidence (20-day block bootstrap, common window) ===")
    ref = window(series["Buy & hold US100, CFD with swap"], *COMMON)
    for name in ("Trend, 44 instruments (net)", "POC leg US100 (scaled)", "A + B (50/50), trend + POC"):
        a = window(series[name], *COMMON)
        ci, d = boot_sharpe_diff(a, ref)
        out.setdefault("boot", {})[name] = dict(ci=ci.tolist(), diff=d.tolist())
        print(f"{name:>40}: Sharpe 95% interval [{ci[0]:.2f}, {ci[1]:.2f}]; minus US100 CFD buy-and-hold: median {d[1]:+.2f}, 95% [{d[0]:+.2f}, {d[2]:+.2f}]")
    # yearly Sharpe
    print("\n=== Calendar-year Sharpe ===")
    ycols = ["Trend, 44 instruments (net)", "A + B (50/50), trend + POC", "Buy & hold US100, CFD with swap", "Buy & hold US100, no financing", "Buy & hold gold, CFD with swap"]
    print(f"{'year':>6} " + "".join(f"{c[:26]:>28}" for c in ycols))
    out["yearly"] = {}
    for y in range(2005, 2027):
        row = []
        for c in ycols:
            r = series[c][series[c].index.year == y].dropna()
            row.append(float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 100 and r.std() > 0 else None)
        out["yearly"][str(y)] = dict(zip(ycols, row))
        print(f"{y:>6} " + "".join(f"{(f'{v:+.2f}' if v is not None else '-'):>28}" for v in row))
    # decision rule
    ab = out["windows"]["COMMON 2021-11 .. 2026-09"]["A + B (50/50), trend + POC"]
    is_s = out["windows"]["IS 2021-11 .. 2025-06"]["A + B (50/50), trend + POC"]["sharpe"]
    oos_s = out["windows"]["OOS 2025-07 .. 2026-09"]["A + B (50/50), trend + POC"]["sharpe"]
    d = out["boot"]["A + B (50/50), trend + POC"]["diff"]
    ok = ab["sharpe"] >= 0.8 and ab["maxdd"] >= -0.08 and is_s > 0 and oos_s > 0 and d[0] > 0
    out["decision"] = dict(worth_building=bool(ok), sharpe=ab["sharpe"], maxdd=ab["maxdd"], is_sharpe=is_s, oos_sharpe=oos_s, diff_lo=d[0])
    print(f"\nDECISION RULE: A+B Sharpe {ab['sharpe']:.2f} (>= 0.8?), max DD {ab['maxdd']:.1%} (<= 8%?), IS {is_s:+.2f} / OOS {oos_s:+.2f}, Sharpe-difference lower bound {d[0]:+.2f} (> 0?) -> "
          f"{'WORTH BUILDING' if ok else 'does NOT beat buy and hold'}")
    # equity curves (weekly points) for the dashboard / records
    eq = {}
    for name, r in series.items():
        rr = window(r, COMMON[0], COMMON[1]).dropna()
        e = (1 + rr).cumprod()
        eq[name] = dict(dates=[str(d.date()) for d in e.index[::5]], eq=[round(float(x), 4) for x in e.values[::5]])
    out["equity"] = eq
    json.dump(out, open(os.path.join(HERE, "round279_results.json"), "w"), indent=1, default=float)
    print(f"\nSaved round279_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
