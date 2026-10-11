"""Family DA: confirmed index dip-reversal as an add-on to the gold pair on MT5, exactly as registered in PREREG_DIP_ADDON.md.
   python -m mt5broker.ea_research.dip_addon"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_research import pass70 as P

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data_mt5"
MK = {"SP": ("America/New_York", 1549), "NSDQ": ("America/New_York", 1549), "DOW": ("America/New_York", 1549), "DAX": ("Europe/Berlin", 1719)}
import sys
SLIP, RISK, CAP, KSTOP = 1e-5, 1000.0, 150000.0, 3.0
import os
Z = float(os.environ.get("DA_Z", "2.0"))                                   # DA2: DA_Z=1.5
EPOCH = pd.Timestamp("1970-01-01")


def load(m):
    tz, hm = MK[m]
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bl", "bc", "ao"]).sort_values("t").drop_duplicates("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo)].reset_index(drop=True)
    loc = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert(tz)
    d["date"] = loc.dt.tz_localize(None).dt.normalize(); d["hm"] = loc.dt.hour * 100 + loc.dt.minute
    return d.dropna(subset=["date"])


def signals(m):
    tz, hm = MK[m]; d = load(m)
    dec = d[d.hm == hm].drop_duplicates("date").set_index("date").bc
    fil = d[d.hm == hm + 1].drop_duplicates("date").set_index("date")
    r = dec.pct_change(); sd = r.rolling(60, min_periods=40).std(); z3 = np.log(dec / dec.shift(3)) / (sd * np.sqrt(3))
    days = dec.index; out = []
    for i in range(3, len(days) - 1):
        D, N = days[i], days[i + 1]
        if not (np.isfinite(z3.iat[i]) and z3.iat[i] <= -Z and N.dayofweek > D.dayofweek and (N - D).days <= 3 and D in fil.index and N in fil.index): continue
        out.append(dict(mkt=m, date=D, t_in=int(fil.at[D, "t"]), t_out=int(fil.at[N, "t"]), e=float(fil.at[D, "ao"]) * (1 + SLIP), sd=float(sd.iat[i])))
    return d, pd.DataFrame(out)


def trades():
    rows, bars = [], {}
    for m in MK:
        d, S = signals(m); bars[m] = d; rows.append(S)
    T = pd.concat(rows, ignore_index=True); T["n"] = T.groupby("date").mkt.transform("count")
    T["q"] = np.minimum(RISK / T.n / (KSTOP * T.sd), CAP) / T.e             # units of the index
    T["stop"] = T.e * (1 - KSTOP * T.sd); return T, bars


def day_arrays(T, bars):
    """Per server day: V = realised P&L, B = min equity vs day start (floating incl.), Hi = max. Server day = t // 86400."""
    acc = {}
    T = T.copy(); T["pl"] = np.nan; T["stopped"] = False
    for k, r in T.iterrows():
        d = bars[r.mkt]; a = int(np.searchsorted(d.t.values, r.t_in)); b = int(np.searchsorted(d.t.values, r.t_out))
        seg = d.iloc[a:b + 1]; t = seg.t.values; bl = seg.bl.values; bc = seg.bc.values; bo = seg.bo.values
        hit = np.nonzero(bl[:-1] <= r.stop)[0]
        if len(hit): j = hit[0]; px = min(r.stop, bo[j]); T.at[k, "stopped"] = True
        else: j = len(t) - 1; px = bo[j]
        px *= (1 - SLIP); pl = (px - r.e) * r.q; T.at[k, "pl"] = pl
        eq_low = (np.minimum(bl[:j + 1], bc[:j + 1]) - r.e) * r.q; eq_hi = (bc[:j + 1] - r.e) * r.q; sday = t[:j + 1] // 86400
        for sd_ in np.unique(sday):
            msk = sday == sd_; A = acc.setdefault(int(sd_), [0.0, 0.0, 0.0])
            A[1] += min(0.0, eq_low[msk].min()); A[2] += max(0.0, eq_hi[msk].max())
        A = acc.setdefault(int(t[j] // 86400), [0.0, 0.0, 0.0]); A[0] += pl; A[1] = min(A[1], pl); A[2] = max(A[2], pl)
    D = pd.DataFrame(acc, index=["V", "B", "Hi"]).T.sort_index(); return T, D


def combine(S, D):
    days = S["days"]; X = D.reindex(days).fillna(0.0)
    return dict(V=S["V"] + X.V.values, B=S["B"] + X.B.values, Hi=S["Hi"] + X.Hi.values, days=days)


def main():
    T, bars = trades(); T, D = day_arrays(T, bars)
    T["bp"] = T.pl / (T.q * T.e) * 1e4; y = T.groupby(T.date.dt.year)
    print(f"DA trades 2022-26: {len(T)} | signal days {T.date.nunique()} | mean {T.pl.mean():+.1f} USD ({T.bp.mean():+.1f} bp) | win {100*(T.pl > 0).mean():.1f}% | stopped {100*T.stopped.mean():.1f}% | worst {T.pl.min():,.0f}")
    print("   by year (trades, USD total, bp mean):", {k: (len(g), round(g.pl.sum()), round(g.bp.mean(), 1)) for k, g in y})
    print("   by market (trades, bp mean):", {k: (len(g), round(g.bp.mean(), 1)) for k, g in T.groupby("mkt")})
    P.C0 = 560.0; res = {}
    for pool in ("MT5", "FT"):
        S = P.series_nh(pool, 1.2); C = combine(S, D); pv = pd.Series(S["V"]); dv = pd.Series(C["V"]) - pv
        act = dv != 0; print(f"{pool}: days {len(pv)} | DA active days {int(act.sum())} | corr(pair V, DA V) all days {pv.corr(dv):+.2f}, DA days {pv[act].corr(dv[act]):+.2f} | DA total {dv.sum():,.0f}")
        for nm, X in (("pair", S), ("pair+DA", C)):
            st, day = P.simulate([X] * len(P.MULTS), P.I12, 52); res[(pool, nm)] = {h: P.p_by(st, day, H) for h, H in P.HORIZONS.items()}
    print("\nP(pass) / P(breach) from +560 counted on 2026-10-12, live x1.2, pass70 rules:")
    for nm in ("pair", "pair+DA"):
        line = []
        for h in P.HORIZONS:
            e, f = res[("MT5", nm)][h], res[("FT", nm)][h]; line.append(f"{h}: MT5 {100*e[0]:.0f}% FT {100*f[0]:.0f}% MIX {50*(e[0]+f[0]):.1f}% (breach MIX {50*(e[1]+f[1]):.1f}%)")
        print(f"  {nm:8s} " + " | ".join(line))
    with open(HERE / "LEDGER.csv", "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},dip_addon,{'DA2' if Z == 1.5 else 'DA'},2022-26,{T.date.nunique()},{len(T)},{T.pl.sum():.1f},{T.bp.mean():.4f},,,{(T.pl > 0).mean():.3f},\n")


if __name__ == "__main__":
    main()
