"""All five top-ranked EAs in ONE $100K MT5 1-Step account (the trader, 2026-10-06: "what if we combined all trades into one evaluation cycle?").

2026 (in-sample: the five were picked by their 2026 results): every EA's tester deals scaled to its frozen lot x c, the intraday equity of each rebuilt from MT5 broker's 1-minute bid / ask bars (ea_curves.minute_equity),
all summed on ONE minute clock -- floating losses that coincide add up exactly as the firm sees them. c is the same for all five and is chosen by a rule written before looking at pass rates: the LARGEST c on the
grid whose combined worst intraday equity drop is <= 2.5% of $100K and whose combined maximum equity drawdown is <= 8% (the caps each EA is already sized to). The whole c grid is reported.
Chances: pass / breach of a 1-step test from every 2026 weekday start, within 30 / 60 / 86 days (floating.chances_eq), and chained tests from 1 January as in ea_curves.py.
OUT OF SAMPLE (2025, 2024): only the EAs that have those years (confirm.load_year, the stage-2 frozen size incl. its gold price-level factor): daily P&L summed, worst equity of the day = the SUM of the members'
worst equities (conservative; as portfolio.py), same c.  Output: D:/finance/scratch/curves/combo.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_batch import confirm, ea_curves as EC, floating

HERE = Path(__file__).resolve().parent
RES = HERE / "results_2026"
INITIAL = 100_000.0
GRID = (1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1)
START, END = pd.Timestamp("2026-01-01"), pd.Timestamp("2026-09-30")
WINDOWS = {H: [list(pd.bdate_range(s, s + pd.Timedelta(days=H))) for s in pd.bdate_range(START, END) if s + pd.Timedelta(days=H) <= END] for H in (30, 60, 86)}


def maxdd(eq):
    e = np.concatenate([[0.0], eq])
    return float((np.maximum.accumulate(e) - e).max())


def main():
    s = pd.read_csv(EC.SUMMARY, dtype={"id": str})
    st = pd.read_csv(RES / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last").set_index("id")
    top = s[s.rankable_e == True].head(5)
    Es, Rs, names, lams = {}, {}, {}, {}
    for r in top.itertuples():
        f = RES / f"{r.id}.csv"; deals = pd.read_csv(f); sym = str(st.loc[r.id, "symbol"])
        fl = floating.get(r.id, 2026, f, sym, float(st.loc[r.id, "eq_dd"]), "2026-01-01", "2026-09-30")
        idx, E, R = EC.minute_equity(deals, sym, basis=fl.diag.get("basis", "mid"))
        Es[r.id] = pd.Series(E, index=idx); Rs[r.id] = pd.Series(R, index=idx); names[r.id] = str(st.loc[r.id, "title"]).split(",")[0][:48]; lams[r.id] = float(r.lam_frozen)
    U = pd.DatetimeIndex(sorted(set().union(*[set(x.index) for x in Es.values()])))
    E1 = sum(lams[i] * Es[i].reindex(U).ffill().fillna(0.0) for i in Es).values            # combined equity at c = 1 (every EA at its frozen lot)
    R1 = sum(lams[i] * Rs[i].reindex(U).ffill().fillna(0.0) for i in Rs).values
    day = U.values.astype("datetime64[D]")
    start = np.flatnonzero(np.r_[True, day[1:] != day[:-1]]); days = pd.DatetimeIndex(day[start])
    before = np.where(start > 0, R1[np.maximum(start - 1, 0)], 0.0)
    v1 = np.add.reduceat(np.diff(R1, prepend=0.0), start)
    m1 = np.minimum(np.minimum.reduceat(E1, start) - before, v1)
    bd = pd.bdate_range(START, END)
    V1 = pd.Series(v1, index=days).reindex(bd).fillna(0.0); M1 = pd.Series(m1, index=days).reindex(bd).fillna(0.0)
    ent = set(days[np.abs(v1) > 0])
    rows = []
    for c in GRID:
        ch = floating.chances_eq(V1, M1, ent, c, WINDOWS)
        rows.append(dict(c=c, worst_intraday_pct=float(-M1.min() * c / INITIAL * 100), worst_closed_pct=float(-V1.min() * c / INITIAL * 100), dd_pct=float(maxdd(c * E1) / INITIAL * 100), net=float(c * R1[-1]),
                         p1_30=ch["p1_30"], b1_30=ch["b1_30"], p1_60=ch["p1_60"], b1_60=ch["b1_60"], p1_86=ch["p1_86"], b1_86=ch["b1_86"], p2_86=ch["p2_86"], days30_med=ch["days30_med"]))
        print(f"c={c:>4}: worst intraday {rows[-1]['worst_intraday_pct']:.1f}% closed {rows[-1]['worst_closed_pct']:.1f}% maxDD {rows[-1]['dd_pct']:.1f}% net {rows[-1]['net']:+,.0f} | 1-Step pass 30d {ch['p1_30']:.0%} (breach {ch['b1_30']:.0%}) 60d {ch['p1_60']:.0%} ({ch['b1_60']:.0%}) 86d {ch['p1_86']:.0%} ({ch['b1_86']:.0%}) | 2-Step 86d {ch['p2_86']:.0%}", flush=True)
    ok = [r for r in rows if r["worst_intraday_pct"] <= 2.5 and r["dd_pct"] <= 8.0]
    c0 = max(r["c"] for r in ok) if ok else GRID[-1]
    print("rule-chosen c =", c0, flush=True)
    # chained tests at c0 and at c = 1
    out = dict(grid=rows, c0=c0, members=[dict(id=i, title=names[i], lam=lams[i], lam_c=lams[i] * c0, net=float(lams[i] * c0 * Rs[i].iloc[-1])) for i in Es], views=[])
    for label, c in ((f"All five in one account, each at {c0:.2f} of its frozen lot", c0), ("All five at their full frozen lots", 1.0)):
        v = V1 * c; m = M1 * c
        att = EC.attempts(v, m, bd)
        df = pd.DataFrame({"E": E1 * c, "R": R1 * c}, index=U); dayi = pd.DatetimeIndex(U.normalize()); segs = []
        for k, (a, b, outcome) in enumerate(att):
            d0, d1 = bd[a], bd[b]
            mask = (dayi >= d0) & (dayi <= d1)
            if not mask.any():
                continue
            sub = df[mask]; i0 = int(np.flatnonzero(mask)[0]); base = df.R.values[i0 - 1] if i0 > 0 else 0.0
            eq = INITIAL + (sub.E.values - base)
            g = pd.DataFrame({"eq": eq, "h": pd.DatetimeIndex(sub.index.floor("h"))}).groupby("h").agg(last=("eq", "last"), low=("eq", "min"))
            dd_ = v.loc[d0:d1]; bal = INITIAL + dd_.cumsum(); fl = np.maximum.accumulate(np.maximum(bal.values, INITIAL)) - 10_000
            segs.append(dict(n=k + 1, start=str(d0.date()), end=str(d1.date()), outcome=outcome, days=int((d1 - d0).days + 1), t=[x.strftime("%Y-%m-%dT%H:%M") for x in g.index],
                             eq=[round(float(x), 0) for x in g["last"]], low=[round(float(x), 0) for x in g["low"]], floor_t=[str(x.date()) for x in dd_.index], floor=[round(float(x), 0) for x in fl],
                             worst=round(float(eq.min()), 0), best=round(float(eq.max()), 0)))
        out["views"].append(dict(label=label, c=c, attempts=segs))
        print(label, ":", ", ".join(f"{a['outcome']} {a['start']}..{a['end']} ({a['days']}d, low {a['worst']:,.0f})" for a in segs), flush=True)
    # out of sample: the EAs that have 2025 / 2024
    oos = []
    for year in (2025, 2024):
        parts = []
        for _, r in top.iterrows():
            stt, d = confirm.load_year(r, year)
            if stt == "ok" and d["m"] is not None:
                parts.append((r.id, d))
        if not parts:
            continue
        W = confirm._W[year][0]
        pnl = sum(d["pnl"] for _, d in parts); mm = sum(d["m"] for _, d in parts); entx = set().union(*[d["ent"] for _, d in parts])
        wins = {H: [list(pd.bdate_range(s, s + pd.Timedelta(days=H))) for s in pd.bdate_range(f"{year}-01-01", f"{year}-12-31") if s + pd.Timedelta(days=H) <= pd.Timestamp(f"{year}-12-31")] for H in (30, 60, 86)}
        for c in (c0, 1.0):
            ch = floating.chances_eq(pnl.reindex(pd.bdate_range(f"{year}-01-01", f"{year}-12-31")).fillna(0.0), np.minimum(mm, pnl).reindex(pd.bdate_range(f"{year}-01-01", f"{year}-12-31")).fillna(0.0), entx, c, wins)
            oos.append(dict(year=year, c=c, members=[names[i] for i, _ in parts], net=float(pnl.sum() * c), p1_30=ch["p1_30"], b1_30=ch["b1_30"], p1_60=ch["p1_60"], b1_60=ch["b1_60"], p1_86=ch["p1_86"], b1_86=ch["b1_86"]))
            print(f"OOS {year} c={c:.2f} members {[names[i][:22] for i, _ in parts]}: net {pnl.sum() * c:+,.0f}; 1-Step 30d {ch['p1_30']:.0%} ({ch['b1_30']:.0%}) 60d {ch['p1_60']:.0%} ({ch['b1_60']:.0%}) 86d {ch['p1_86']:.0%} ({ch['b1_86']:.0%})", flush=True)
    out["oos"] = oos
    (EC.OUT / "combo.json").write_text(json.dumps(out, separators=(",", ":")))
    print("wrote combo.json")


if __name__ == "__main__":
    main()
