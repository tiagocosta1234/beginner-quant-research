"""The five top-ranked EAs in ONE $100K MT5 1-Step account over the WHOLE data set, 2022-01 .. 2026-09 (the trader, 2026-10-06: "do the whole data set we have").

Per year every EA's tester deals (results_<year>/<id>.csv, real ticks, run at the default lot) are scaled to its frozen lot (lam_frozen of the 2026 ranking, times the gold price-level factor confirm.load_year uses for
other years), its intraday equity is rebuilt from MT5 broker's 1-minute bid / ask bars (ea_curves.minute_equity, basis verified against the tester's own drawdown), and the five are summed on one minute clock.
The years are chained into one cumulative series. A size scale c, the same for every EA and every year, is chosen by a rule fixed before looking at pass rates: the LARGEST c on the grid whose WHOLE-PERIOD combined
worst intraday equity drop is <= 2.5% of $100K and maximum equity drawdown <= 8%. The whole grid is reported. Pass / breach chances: a 1-step test started on every weekday 2022-2026 (within 30 / 60 / 86 days),
and per year. 2026 is in-sample for the choice of the five EAs; 2022-2025 are not, but the frozen sizes come from 2026.   Output: D:/finance/scratch/curves/combo_all.json
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_batch import confirm, ea_curves as EC, floating

HERE = Path(__file__).resolve().parent
INITIAL = 100_000.0
YEARS = (2022, 2023, 2024, 2025, 2026)
GRID = tuple(float(x) for x in os.environ.get("EA_GRID", "1.0,0.8,0.6,0.5,0.4,0.3,0.25,0.2,0.15,0.1").split(","))
END = pd.Timestamp("2026-09-30")


def maxdd(eq):
    e = np.concatenate([[0.0], eq])
    return float((np.maximum.accumulate(e) - e).max())


def year_frames(top, st26, year):
    """(minute index, combined equity E at c=1, realized R at c=1, members used, per-EA net at c=1) for one year."""
    Es, Rs, used, nets = {}, {}, [], {}
    for _, r in top.iterrows():
        rd = HERE / f"results_{year}"; f = rd / f"{r.id}.csv"; stf = rd / "status.csv"
        if not f.exists() or not stf.exists():
            continue
        st = pd.read_csv(stf, dtype={"id": str}).drop_duplicates("id", keep="last").set_index("id")
        if r.id not in st.index or not st.loc[r.id, "eq_dd"] > 0:
            continue
        sym = str(st.loc[r.id, "symbol"])
        end = "2026-09-30" if year == 2026 else f"{year}-12-31"
        fl = floating.get(r.id, year, f, sym, float(st.loc[r.id, "eq_dd"]), f"{year}-01-01", end)
        if not fl.ok:
            print(f"  {year} {r.id}: floating {fl.status} -- excluded", flush=True); continue
        fac = 1.0 if (year == 2026 or confirm.is_fx(sym)) else confirm.level(HERE / "results_2026" / f"{r.id}.csv") / confirm.level(f)
        lam = float(r.lam_frozen) * fac
        deals = pd.read_csv(f)
        idx, E, R = EC.minute_equity(deals, sym, f"{year}-01-01", end, basis=fl.diag.get("basis", "mid"))
        Es[r.id] = lam * pd.Series(E, index=idx); Rs[r.id] = lam * pd.Series(R, index=idx); used.append(str(r.id)); nets[str(r.id)] = float(lam * R[-1])
    if not Es:
        return None
    U = pd.DatetimeIndex(sorted(set().union(*[set(x.index) for x in Es.values()])))
    E = sum(x.reindex(U).ffill().fillna(0.0) for x in Es.values()).values
    R = sum(x.reindex(U).ffill().fillna(0.0) for x in Rs.values()).values
    return U, E, R, used, nets


def main():
    s = pd.read_csv(EC.SUMMARY, dtype={"id": str})
    top = s[s.rankable_e == True].head(5)
    import os
    ids = os.environ.get("EA_IDS")
    if ids:
        top = top[top.id.isin(ids.split(","))]
    title = {str(r.id): str(r.id) for _, r in top.iterrows()}
    st26 = pd.read_csv(HERE / "results_2026" / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last").set_index("id")
    for i in title:
        title[i] = str(st26.loc[i, "title"]).split(",")[0][:40]
    parts, offset = [], 0.0
    Uall, Eall, Rall, meta = [], [], [], []
    for y in YEARS:
        fr = year_frames(top, st26, y)
        if fr is None:
            print(y, "no data", flush=True); continue
        U, E, R, used, nets = fr
        print(f"{y}: members {[title[i][:20] for i in used]}; net at frozen lots {sum(nets.values()):+,.0f}", flush=True)
        meta.append(dict(year=y, members=[title[i] for i in used], nets={title[i]: round(v) for i, v in nets.items()}))
        print("   per EA net at frozen lots: " + ", ".join(f"{title[i][:18]} {v:+,.0f}" for i, v in nets.items()), flush=True)
        Uall.append(U); Eall.append(E + offset); Rall.append(R + offset); offset += R[-1]
    U = pd.DatetimeIndex(np.concatenate([u.values for u in Uall])); E1 = np.concatenate(Eall); R1 = np.concatenate(Rall)
    day = U.values.astype("datetime64[D]")
    start = np.flatnonzero(np.r_[True, day[1:] != day[:-1]]); days = pd.DatetimeIndex(day[start])
    before = np.where(start > 0, R1[np.maximum(start - 1, 0)], 0.0)
    v1 = np.add.reduceat(np.diff(R1, prepend=0.0), start)
    m1 = np.minimum(np.minimum.reduceat(E1, start) - before, v1)
    bd = pd.bdate_range(days.min(), END)
    V1 = pd.Series(v1, index=days).reindex(bd).fillna(0.0); M1 = pd.Series(m1, index=days).reindex(bd).fillna(0.0)
    ent = set(days[np.abs(v1) > 0])
    wins = {H: [list(pd.bdate_range(x, x + pd.Timedelta(days=H))) for x in bd if x + pd.Timedelta(days=H) <= END] for H in (30, 60, 86)}
    rows = []
    for c in GRID:
        ch = floating.chances_eq(V1, M1, ent, c, wins)
        by_year = {}
        for y in YEARS:
            ys = [dl for dl in wins[30] if dl[0].year == y]
            if not ys:
                continue
            w1 = {H: [dl for dl in wins[H] if dl[0].year == y] for H in (30, 60, 86)}
            cy = floating.chances_eq(V1, M1, ent, c, w1)
            by_year[y] = dict(net=float(c * V1.loc[f"{y}-01-01":f"{y}-12-31"].sum()), p1_30=cy["p1_30"], b1_30=cy["b1_30"], p1_60=cy["p1_60"], b1_60=cy["b1_60"], p1_86=cy["p1_86"], b1_86=cy["b1_86"])
        rows.append(dict(c=c, worst_intraday_pct=float(-M1.min() * c / INITIAL * 100), worst_closed_pct=float(-V1.min() * c / INITIAL * 100), dd_pct=float(maxdd(c * E1) / INITIAL * 100), net=float(c * R1[-1]),
                         p1_30=ch["p1_30"], b1_30=ch["b1_30"], p1_60=ch["p1_60"], b1_60=ch["b1_60"], p1_86=ch["p1_86"], b1_86=ch["b1_86"], p2_86=ch["p2_86"], by_year=by_year))
        r = rows[-1]
        print(f"c={c:>4}: worst intraday {r['worst_intraday_pct']:.1f}% maxDD {r['dd_pct']:.1f}% net {r['net']:+,.0f} | 1-Step pass 30d {ch['p1_30']:.0%} ({ch['b1_30']:.0%}) 60d {ch['p1_60']:.0%} ({ch['b1_60']:.0%}) 86d {ch['p1_86']:.0%} ({ch['b1_86']:.0%}) | 2-Step 86d {ch['p2_86']:.0%}", flush=True)
        if True:
            print("    by year: " + "; ".join(f"{y} net {d['net']:+,.0f} 30d {d['p1_30']:.0%} ({d['b1_30']:.0%}) 60d {d['p1_60']:.0%} 86d {d['p1_86']:.0%} ({d['b1_86']:.0%})" for y, d in by_year.items()), flush=True)
    ok = [r for r in rows if r["worst_intraday_pct"] <= 2.5 and r["dd_pct"] <= 8.0]
    c0 = max(r["c"] for r in ok) if ok else 0.4
    print("whole-period rule satisfiable:", bool(ok), "-> c used for the chained cycle =", c0, "(0.40 = the 2026 rule's scale when no scale meets the caps over 2022-2026)", flush=True)
    # chained tests across the whole period at c0
    v, m = V1 * c0, M1 * c0
    att = EC.attempts(v, m, bd)
    df = pd.DataFrame({"E": E1 * c0, "R": R1 * c0}, index=U); dayi = pd.DatetimeIndex(U.normalize()); segs = []
    for k, (a, b, outcome) in enumerate(att):
        d0, d1 = bd[a], bd[b]
        mask = (dayi >= d0) & (dayi <= d1)
        if not mask.any():
            continue
        sub = df[mask]; i0 = int(np.flatnonzero(mask)[0]); base = df.R.values[i0 - 1] if i0 > 0 else 0.0
        eq = INITIAL + (sub.E.values - base)
        g = pd.DataFrame({"eq": eq, "h": pd.DatetimeIndex(sub.index.floor("4h"))}).groupby("h").agg(last=("eq", "last"), low=("eq", "min"))
        dd_ = v.loc[d0:d1]; bal = INITIAL + dd_.cumsum(); fl = np.maximum.accumulate(np.maximum(bal.values, INITIAL)) - 10_000
        segs.append(dict(n=k + 1, start=str(d0.date()), end=str(d1.date()), outcome=outcome, days=int((d1 - d0).days + 1), t=[x.strftime("%Y-%m-%dT%H:%M") for x in g.index],
                         eq=[round(float(x), 0) for x in g["last"]], low=[round(float(x), 0) for x in g["low"]], floor_t=[str(x.date()) for x in dd_.index], floor=[round(float(x), 0) for x in fl],
                         worst=round(float(eq.min()), 0), best=round(float(eq.max()), 0)))
    n_pass = sum(a["outcome"] == "pass" for a in segs); n_br = sum(a["outcome"] == "breach" for a in segs)
    print(f"chained tests at c={c0}: {len(segs)} ({n_pass} pass, {n_br} breach, last: {segs[-1]['outcome']}); median days to pass {np.median([a['days'] for a in segs if a['outcome'] == 'pass']):.0f}", flush=True)
    for a in segs:
        print(f"   #{a['n']} {a['start']}..{a['end']} {a['days']}d {a['outcome']} (low {a['worst']:,.0f})", flush=True)
    out = dict(grid=rows, c0=c0, years=meta, attempts=segs, start=str(bd[0].date()), titles=list(title.values()))
    (EC.OUT / (os.environ.get("EA_OUT") or "combo_all.json")).write_text(json.dumps(out, separators=(",", ":")))
    print("wrote combo_all.json", (EC.OUT / (os.environ.get("EA_OUT") or "combo_all.json")).stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
