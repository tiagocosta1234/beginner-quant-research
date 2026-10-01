"""
Round 284 (2026-10-01, PRE-REGISTERED): CROSS-SECTIONAL LONG-SHORT across MT5 broker instruments (idea 4 of the brainstorm the trader approved).
Hypothesis: within an asset class, last month's winners keep outperforming losers (cross-sectional momentum, a documented but modest factor), 12-1 month
momentum likewise, and last week's losers rebound against last week's winners (short-term reversal). A long-top-third / short-bottom-third book is roughly
market-neutral, so it does not simply ride the 2021-26 equity rally, and its short leg is swap-free on indices/metals. Prior (stated now): Round 253 found trend
real before swap and erased by MT5 broker's swap; Round 257 found 0 confirmed daily-direction signals; cross-sectional factors are weak recently and the swap on the long
leg (indices -7% to -8% a year) is a hard hurdle. The honest expectation is no survivor; this round measures the factor honestly with MT5 broker's costs.

DATA: D1 closes of the non-crypto MT5 broker universe (Round 279 machinery: bad prints > 10 sigma zeroed, D1 bar = 17:00-17:00 NY, from each instrument's first bar).
UNIVERSES (4): IDX = the 12 index CFDs; FXU = the 15 FX pairs; CMD = 5 metals + 4 energy + 7 agri (16); ALL = all 44 non-crypto instruments.
SIGNALS (3), all causal at the close of day t: MOM21 = 21-day return; MOM12_1 = return from t-252 to t-21; REV5 = minus the 5-day return (long the last week's losers).
REBALANCE: every H trading days, H in (5, 21) (a global schedule); at each rebalance, among instruments with a valid signal and volatility, if >= 6 are valid: LONG the top third by
signal, SHORT the bottom third (ties by order), flat otherwise; held until the next rebalance. Weights = direction / (60-day volatility) / N, the whole book scaled to 8% annual
volatility by its trailing 63-day volatility (cap 5x), decided at the close for the next bar -- exactly Round 279/280's book() (a verified, shared function).
COSTS (MT5 broker's, as Round 279): swap = today's swap per side as a fraction of price (charged at the 17:00 rollover, triple on each instrument's own weekday); half the median D1 spread per unit of
turnover; $5 per lot round trip on FX and metals. DISCLOSED BIASES: swaps are today's values applied to the whole history (this OVERSTATES the swap burden before 2022 and is the largest
single hurdle); positions are held across weekends, so this book is usable in the EVALUATION only (the live Standard account must be flat before the weekend); bad-print rule as before.
CELLS: 4 universes x 3 signals x 2 holds = 24; ledger k = 846 + 24 = 870. IS = each cell's start .. 2021-10-31 (indices only from ~2017), OOS = 2021-11-01 .. 2026-09-30.
Per cell: net and gross-of-swap-and-costs annualised return, volatility, Sharpe, maximum drawdown, the mean net exposure; block-bootstrap (20-day blocks, 3,000 draws, seed 2841)
P(mean daily net return > 0) for IS and OOS. CANDIDATE (the repo's rule, fixed now): IS P >= 0.95 AND OOS P >= 1 - 0.01/870 AND OOS net Sharpe > 0 AND OOS days >= 500; also
Benjamini-Hochberg q = 0.10 over the 24 OOS one-sided p-values.
PLACEBO (dry-run): a random permutation of the ranks at every rebalance must give a negative net Sharpe of the size of the costs; the mean net exposure of the real book must be near zero.
POWER_NOTES: 5 years of daily returns give a Sharpe standard error of ~0.45; only a net Sharpe above ~1 is distinguishable from zero in the OOS window alone.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round280_swap_aware_long_short as R8
from mt5broker import universe as U

SYMS = R8.SYMS
UNIV = {"IDX": [s for s in U.INDICES if s in SYMS], "FXU": [s for s in U.FX if s in SYMS and s != "DXY.cash"],
        "CMD": [s for s in U.METALS + U.ENERGY + U.AGRI if s in SYMS], "ALL": list(SYMS)}
SIGS, HOLDS = ("MOM21", "MOM12_1", "REV5"), (5, 21)
OOS_FROM, LAST = pd.Timestamp("2021-11-01"), pd.Timestamp("2026-09-30")
K_TOTAL = 846 + len(UNIV) * len(SIGS) * len(HOLDS)
SEED, B, BLOCK = 2841, 3000, 20


def signals(P):
    ret = P["ret"].fillna(0.0)
    lp = np.log1p(ret).cumsum()
    cl = P["close"].notna()
    out = {}
    out["MOM21"] = ((lp - lp.shift(21)).where(cl & cl.shift(21).fillna(False)))
    out["MOM12_1"] = ((lp.shift(21) - lp.shift(252)).where(cl & cl.shift(252).fillna(False)))
    out["REV5"] = (-(lp - lp.shift(5)).where(cl & cl.shift(5).fillna(False)))
    return out


def make_direction(P, sig, cols, hold, rng=None):
    idx = P["idx"]
    ok = sig[cols].notna() & P["sigma"][cols].notna() & (P["sigma"][cols] > 0) & P["close"][cols].notna()
    D = pd.DataFrame(np.nan, index=idx, columns=SYMS)
    for i in range(260, len(idx), hold):
        row = sig[cols].iloc[i].where(ok.iloc[i])
        n = int(row.notna().sum())
        D.iloc[i] = 0.0
        if n >= 6:
            if rng is not None:
                row = pd.Series(rng.random(len(row)), index=row.index).where(row.notna())
            k = n // 3
            rk = row.rank(method="first")
            D.loc[idx[i], row.index[(rk > n - k).values]] = 1.0
            D.loc[idx[i], row.index[(rk <= k).values]] = -1.0
    D = D.ffill().fillna(0.0)
    valid = (D != 0) & P["sigma"].notna() & (P["sigma"] > 0) & P["close"].notna()
    return D, valid


def block_boot_p(r, seed=SEED):
    x = r.dropna().values
    n = len(x)
    if n < 100:
        return float("nan")
    rng = np.random.default_rng(seed)
    nb = -(-n // BLOCK)
    st = rng.integers(0, n - BLOCK, (B, nb))
    idx = (st[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(B, -1)[:, :n]
    return float(np.mean(x[idx].mean(axis=1) > 0))


def stats(r, lo, hi):
    y = r[(r.index >= lo) & (r.index <= hi)].dropna()
    if len(y) < 100 or y.std() == 0:
        return None
    eq = (1 + y).cumprod()
    return dict(n=int(len(y)), ret=float(y.mean() * 252), vol=float(y.std() * np.sqrt(252)), sharpe=float(y.mean() / y.std() * np.sqrt(252)), maxdd=float((eq / eq.cummax() - 1).min()), P=block_boot_p(y))


def bh(ps, q=0.10):
    p = np.array(ps, float); o = np.argsort(p); m = len(p); ok = np.zeros(m, bool); thr = -1
    for r, i in enumerate(o, 1):
        if p[i] <= q * r / m:
            thr = r
    if thr > 0:
        ok[o[:thr]] = True
    return ok


def run_cell(P, SG, uname, sname, hold, rng=None):
    D, valid = make_direction(P, SG[sname], UNIV[uname], hold, rng)
    net, gross, info = R8.book(P, D, valid)
    w_exp = info["mean_net_exposure"]
    return net, gross, info


def dry_run():
    t0 = time.time()
    P = R8.prep(); SG = signals(P)
    print(f"prepared ({time.time() - t0:.0f}s); universes: " + ", ".join(f"{k} {len(v)}" for k, v in UNIV.items()))
    rng = np.random.default_rng(9)
    for u in ("IDX", "FXU", "ALL"):
        net, gross, info = run_cell(P, SG, u, "MOM21", 5)
        pn, pg, pi = run_cell(P, SG, u, "MOM21", 5, rng)
        s = stats(net, OOS_FROM, LAST); ps = stats(pn, OOS_FROM, LAST)
        print(f"{u}: real MOM21/5d net from {net.index[0].date()}, mean net exposure {info['mean_net_exposure']:+.2f}, mean lev {info['mean_lev']:.2f}x, swap {info['swap_ann_common']:+.2%}/yr, trading cost {-info['trade_ann']:+.2%}/yr; "
              f"placebo (random ranks) OOS net Sharpe {ps['sharpe'] if ps else float('nan'):+.2f} (swap {pi['swap_ann_common']:+.2%}/yr)")
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    P = R8.prep(); SG = signals(P)
    rows = []
    print(f"{'universe':>4} {'signal':>8} {'H':>3} | {'IS Sharpe':>9} {'P':>5} | {'OOS days':>8} {'ret':>6} {'vol':>5} {'net Sh':>6} {'maxDD':>6} {'P':>5} | {'gross Sh':>8} {'expo':>5}")
    for u in UNIV:
        for sname in SIGS:
            for hold in HOLDS:
                net, gross, info = run_cell(P, SG, u, sname, hold)
                i = stats(net, net.index[0], OOS_FROM - pd.Timedelta(days=1)); o = stats(net, OOS_FROM, LAST); g = stats(gross, OOS_FROM, LAST)
                rows.append(dict(u=u, sig=sname, H=hold, IS=i, OOS=o, gross_oos_sharpe=(g["sharpe"] if g else None), expo=info["mean_net_exposure"], info=info))
                print(f"{u:>4} {sname:>8} {hold:>3} | {(i['sharpe'] if i else float('nan')):>+9.2f} {(i['P'] if i else float('nan')):>5.2f} | {(o['n'] if o else 0):>8} {(o['ret'] if o else float('nan')):>+6.1%} "
                      f"{(o['vol'] if o else float('nan')):>5.1%} {(o['sharpe'] if o else float('nan')):>+6.2f} {(o['maxdd'] if o else float('nan')):>6.1%} {(o['P'] if o else float('nan')):>5.2f} | "
                      f"{(g['sharpe'] if g else float('nan')):>+8.2f} {info['mean_net_exposure']:>+5.2f}", flush=True)
    cand = [r for r in rows if r["IS"] and r["OOS"] and r["IS"]["P"] >= 0.95 and r["OOS"]["P"] >= 1 - 0.01 / K_TOTAL and r["OOS"]["sharpe"] > 0 and r["OOS"]["n"] >= 500]
    elig = [r for r in rows if r["OOS"] and r["OOS"]["n"] >= 500]
    ok = bh([1 - r["OOS"]["P"] for r in elig], 0.10)
    print(f"\nCANDIDATES (IS P >= 0.95, OOS P >= {1 - 0.01 / K_TOTAL:.6f}, OOS net Sharpe > 0, OOS days >= 500): {len(cand)} of {len(rows)}; Benjamini-Hochberg q=0.10 over {len(elig)} cells: {int(ok.sum())}")
    sh = np.array([r["OOS"]["sharpe"] for r in rows if r["OOS"]]); gs = np.array([r["gross_oos_sharpe"] for r in rows if r["gross_oos_sharpe"] is not None])
    print(f"OOS net Sharpe over all {len(sh)} cells: mean {sh.mean():+.2f}, best {sh.max():+.2f}, positive in {np.mean(sh > 0):.0%}; gross-of-swap-and-costs OOS Sharpe mean {gs.mean():+.2f}, positive in {np.mean(gs > 0):.0%}")
    json.dump(dict(rows=rows, n_candidates=len(cand), n_bh=int(ok.sum()), k_total=K_TOTAL), open(os.path.join(HERE, "round284_results.json"), "w"), indent=1, default=float)
    print(f"Saved round284_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
