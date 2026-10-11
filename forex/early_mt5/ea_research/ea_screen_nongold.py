"""Family XS: strict non-gold screen of the CodeBase EA batch, exactly as registered in PREREG_EA_SCREEN_NONGOLD.md.
   python -m mt5broker.ea_research.ea_screen_nongold [--holdout]"""
from __future__ import annotations

import datetime as dt
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RES = HERE.parents[0] / "ea_batch" / "results"
OUT = HERE / "EA_SCREEN_NONGOLD_OUTPUT.txt"


def monthly(f):
    d = pd.read_csv(f)
    if d.empty: return None, 0
    d = d[d.direction.astype(str).str.lower().str.startswith("out")]
    if d.empty: return None, 0
    d["pl"] = d.profit + d.commission + d.swap; d["time"] = pd.to_datetime(d.time, format="%Y.%m.%d %H:%M:%S", errors="coerce")
    d = d.dropna(subset=["time"]); return d.set_index("time").pl.resample("ME").sum(), d


def main(holdout=False):
    st = pd.read_csv(RES / "status.csv"); st = st[(st.symbol != "XAUUSD") & (st.deals > 0)]
    rows, ms = [], {}
    for _, r in st.iterrows():
        f = RES / f"{r.id}.csv"
        if not f.exists(): continue
        m, d = monthly(f)
        if m is None: continue
        dv = d[(d.time >= "2022-01-01") & (d.time < "2026-01-01")]; m25 = m[(m.index >= "2022-01-01") & (m.index < "2026-01-01")]
        if len(m25) < 12: continue
        yr = dv.groupby(dv.time.dt.year).pl.sum(); pf = dv.pl[dv.pl > 0].sum() / max(-dv.pl[dv.pl < 0].sum(), 1e-9)
        t = m25.mean() / (m25.std(ddof=1) / np.sqrt(len(m25))) if m25.std() > 0 else 0
        rows.append(dict(id=r.id, title=str(r.title)[:60], symbol=r.symbol, tf=r.period, trades=len(dv), y22=yr.get(2022, 0), y23=yr.get(2023, 0), y24=yr.get(2024, 0), y25=yr.get(2025, 0), pf=pf, t=t))
        ms[r.id] = m25
    R = pd.DataFrame(rows)
    R["pass"] = (R.trades >= 100) & (R[["y22", "y23", "y24", "y25"]] > 0).all(axis=1) & (R.t >= 3.5) & (R.pf >= 1.2)
    lines = [f"non-gold EAs with deals: {len(R)} | trades>=100: {(R.trades >= 100).sum()} | all 4 years positive: {((R[['y22','y23','y24','y25']] > 0).all(axis=1) & (R.trades >= 100)).sum()} | t>=3.5: {(R.t >= 3.5).sum()} | PASS all: {R['pass'].sum()}"]
    # reality check: best monthly t under a sign-randomised null (each EA's months demeaned, block-resampled jointly)
    rng = np.random.default_rng(11); keys = [k for k in ms if len(ms[k]) >= 24]; best = []
    for _ in range(200):
        bt = -9
        for k in keys:
            x = ms[k].to_numpy(); x = x - x.mean(); n = len(x); i = np.empty(n, int); i[0] = rng.integers(n)
            for j in range(1, n): i[j] = rng.integers(n) if rng.random() < 0.25 else (i[j - 1] + 1) % n
            y = x[i]; s = y.std(ddof=1)
            if s > 0: bt = max(bt, y.mean() / (s / np.sqrt(n)))
        best.append(bt)
    lines.append(f"reality check: best monthly t across {len(keys)} EAs with no edge: median {np.median(best):+.2f}, 95th pct {np.percentile(best, 95):+.2f}; real best {R.t.max():+.2f}")
    lines.append("top 15 by monthly t (2022-25):"); lines.append(R.sort_values("t", ascending=False).head(15).round(2).to_string(index=False))
    if holdout and R["pass"].any():
        for _, r in R[R["pass"]].iterrows():
            _, d = monthly(RES / f"{r.id}.csv"); h = d[(d.time >= "2026-01-01")]; lines.append(f"HOLD 2026 {r.id} {r.title}: trades {len(h)} net {h.pl.sum():+,.0f}")
    txt = "\n".join(lines); print(txt); OUT.write_text(txt, encoding="utf-8")
    with open(HERE / "LEDGER.csv", "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},ea_screen_nongold,XS,2022-25,{len(R)},{int(R['pass'].sum())},,,,{R.t.max():.2f},,best {R.sort_values('t').iloc[-1].id}\n")


if __name__ == "__main__":
    main("--holdout" in sys.argv)
