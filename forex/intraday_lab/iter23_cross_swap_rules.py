"""Iteration 23 (pre-registered in lab/PREREG.md): the synthetic-cross fade net of swap, by year, and on the MT5 2-Step rules.   python -m forex.intraday_lab.iter23_cross_swap_rules"""
from __future__ import annotations

from itertools import combinations, product

import numpy as np
import pandas as pd

from forex.ea_batch import pair_stress as PS
from forex.intraday_lab.iter16_fx_xsection import COMM, SGN, load
from forex.intraday_lab.lab import FX

# tester swap, USD per lot per night, median over the screened EAs' deals (side = the pair's own long / short)
SWAP_USD = {"AUDUSD": {1: -3.0, -1: -5.12}, "EURUSD": {1: -10.0, -1: 0.63}, "GBPUSD": {1: -6.7, -1: -4.0}, "USDJPY": {1: 1.7, -1: -13.0}}
SWAP_DEFAULT_BP = -1.0                                                  # USDCAD / USDCHF: no data, charged on both sides (conservative)
CELLS = list(product((120, 168, 240), (2.5, 3.0, 3.5), (36, 48, 72)))


def swap_bp_table(price):
    t = {}
    for k, s in enumerate(FX):
        for side in (1, -1):
            if s in SWAP_USD:
                notional = 100000 * (price[k] if SGN[s] == 1 else 1.0)
                t[(k, side)] = SWAP_USD[s][side] / notional * 1e4
            else:
                t[(k, side)] = SWAP_DEFAULT_BP
    return t


def nights(d0, d1):
    out = 0; d = d0.normalize()
    while d < d1.normalize():
        out += 3 if d.dayofweek == 2 else 1; d += pd.Timedelta(days=1)
    return out


def run_cell(l55, l00, x_ff, spv, idx, W, th, H, swap_tab, inc, thr=None):
    """Returns the list of (exit day, net_no_swap, net_swap) and ADDS the hourly equity increments of every trade to inc (per unit notional per leg)."""
    n = len(idx); out = []
    for (i, j) in combinations(range(6), 2):
        x55 = pd.Series(l55[:, i] - l55[:, j]); mu = x55.rolling(W, min_periods=W // 2).mean(); sd = x55.rolling(W, min_periods=W // 2).std(); z = ((x55 - mu) / sd).values; x00 = l00[:, i] - l00[:, j]; xf = x_ff[(i, j)]
        t = W + 1
        while t < n - H:
            if np.isnan(z[t]) or np.isnan(x00[t]) or np.isnan(x00[t + H]) or np.isnan(spv[[t, t + H]][:, [i, j]]).any() or abs(z[t]) < th or spv[t, i] > 3e-4 or spv[t, j] > 3e-4:
                t += 1; continue
            pos = -np.sign(z[t]); gross = pos * (x00[t + H] - x00[t]); half_in = 0.5 * (spv[t, i] + spv[t, j]) + 2 * COMM; half_out = 0.5 * (spv[t + H, i] + spv[t + H, j]) + 2 * COMM
            nn = nights(idx[t], idx[t + H]); si = SGN[FX[i]] * int(pos); sj = SGN[FX[j]] * int(-pos)
            sw = nn * (swap_tab[(i, si)] + swap_tab[(j, sj)]) * 1e-4
            if thr is not None and sw * 1e4 < thr:
                t += 1; continue
            out.append((idx[t + H].normalize(), gross - half_in - half_out, gross - half_in - half_out + sw))
            d = np.diff(xf[t:t + H + 1]); inc[t + 1:t + H + 1] += pos * np.nan_to_num(d); inc[t] -= half_in; inc[t + H] -= half_out - sw
            t += H
    return out


def sharpe(x):
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252)) if len(x) > 40 and x.std(ddof=1) > 0 else np.nan


def main():
    P55, P00, SP = load(); sg = np.array([SGN[s] for s in FX]); l55 = np.log(P55.values) * sg; l00 = np.log(P00.values) * sg; spv = SP.values; idx = P00.index; n = len(idx)
    price = np.nanmedian(P00.values, axis=0); swap_tab = swap_bp_table(price)
    x_ff = {(i, j): pd.Series(l00[:, i] - l00[:, j]).ffill().values for i, j in combinations(range(6), 2)}
    days = pd.bdate_range("2021-10-01", "2026-09-30"); rows = []; ens_ns = []; ens_sw = []; inc_all = np.zeros(n)
    for W, th, H in CELLS:
        inc = np.zeros(n); T = run_cell(l55, l00, x_ff, spv, idx, W, th, H, swap_tab, inc); inc_all += inc / len(CELLS)
        df = pd.DataFrame(T, columns=["d", "ns", "sw"]); a = df.groupby("d").ns.sum().reindex(days).fillna(0.0); b = df.groupby("d").sw.sum().reindex(days).fillna(0.0); ens_ns.append(a); ens_sw.append(b)
        rows.append(dict(W=W, theta=th, H=H, trades=len(df), net_noswap_bp=df.ns.mean() * 1e4, net_swap_bp=df.sw.mean() * 1e4,
                         dev_ns=sharpe(a.loc["2021-10-01":"2023-12-31"]), dev_sw=sharpe(b.loc["2021-10-01":"2023-12-31"]), val_ns=sharpe(a.loc["2024-01-01":"2024-12-31"]), val_sw=sharpe(b.loc["2024-01-01":"2024-12-31"])))
        print(f"cell {W}/{th}/{H}: {rows[-1]}", flush=True)
    R = pd.DataFrame(rows); R.to_csv(r"D:\finance\scratch\lab\iter23_cells.csv", index=False)
    en, es = sum(ens_ns) / len(CELLS), sum(ens_sw) / len(CELLS); ctr = R[(R.W == 168) & (R.theta == 3.0) & (R.H == 48)].iloc[0]
    print(f"\nCENTRE: DEV no-swap {ctr.dev_ns:.2f} swap {ctr.dev_sw:.2f} | VAL no-swap {ctr.val_ns:.2f} swap {ctr.val_sw:.2f}; mean swap cost {(ctr.net_noswap_bp - ctr.net_swap_bp):.2f} bp a trade")
    print("ENSEMBLE Sharpe  no-swap / swap:")
    for nm, a, b in (("DEV 2021-10..2023-12", "2021-10-01", "2023-12-31"), ("VAL 2024", "2024-01-01", "2024-12-31"), ("HOLD 2025-26 (CONTAMINATED)", "2025-01-01", "2026-09-30")):
        print(f"  {nm:<30} {sharpe(en.loc[a:b]):5.2f} / {sharpe(es.loc[a:b]):5.2f}")
    print("ENSEMBLE Sharpe by calendar year (net of swap):")
    ys = {y: sharpe(es.loc[f'{y}-01-01':f'{y}-12-31']) for y in (2021, 2022, 2023, 2024, 2025, 2026)}; print(" ", {k: round(v, 2) for k, v in ys.items()})
    print("share of the 27 cells with swap Sharpe > 0: DEV %.0f%%, VAL %.0f%%" % ((R.dev_sw > 0).mean() * 100, (R.val_sw > 0).mean() * 100))
    # equity on the 2-Step: hourly marked equity of the ensemble, exposure L per leg (multiples of the account)
    ser = pd.Series(inc_all, index=idx); dayv = ser.groupby(ser.index.normalize()).sum().reindex(days).fillna(0.0)
    cum = ser.cumsum(); start_of_day = cum.groupby(cum.index.normalize()).transform(lambda s: s.iloc[0] - ser.loc[s.index[0]]); intra = (cum - start_of_day).groupby(cum.index.normalize()).min().reindex(days).fillna(0.0)
    dayv_np, intra_np = dayv.values, np.minimum(intra.values, dayv.values)
    print("\nENSEMBLE on the MT5 2-Step (hourly marked equity approximated as balance; every weekday start; no deadline):")
    for L in (3, 5, 8):
        v = dayv_np * L * 1e5; m = intra_np * L * 1e5
        o = PS.evaluate(v, m, pd.DatetimeIndex(days)); sd = pd.Series(v).std()
        print(f"  L = {L} x account per leg: ann. vol {sd * np.sqrt(252) / 1e5:5.1%} of $100K | pass {o.p2:4.0%} breach {o.b2:4.0%} median {o.days_med:4.0f} days | worst day {o.worst_day:.1f}% | total {v.sum() / 1e3:,.0f}K over the sample", flush=True)
    pd.DataFrame({"day": days, "v_unit": dayv_np, "m_unit": intra_np}).to_csv(r"D:\finance\scratch\lab\iter23_ensemble_daily.csv", index=False)


if __name__ == "__main__":
    main()
