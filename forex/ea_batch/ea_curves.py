"""2026 equity curves of the top-ranked EAs on a $100K MT5 1-Step account (the trader, 2026-10-06: "i wanna see all of those EAs equity curve for 2026 in a 100k evaluation cycle").

For each EA: the tester's deals (results_2026/<id>.csv) are scaled to the frozen lot (lam_frozen of the ranking = the largest size whose rebuilt equity drawdown stays <= 8% and whose worst day <= 2.5%),
the intraday equity is rebuilt from MT5 broker's 1-minute bid / ask bars exactly as floating.py does (basis = the one that verified against the tester's own drawdown), and chained 1-Step attempts are run
from the first trading day: +10% target (best day <= 50% of the profit), 3% daily loss, 10% floor trailing the highest end-of-day balance; after a pass or a breach the next attempt starts the next weekday
with a fresh $100K. Output: D:/finance/scratch/curves/data.json (hourly equity per attempt, floors, outcomes).

  python -m forex.ea_batch.ea_curves
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_batch import floating

HERE = Path(__file__).resolve().parent
RES = HERE / "results_2026"
SUMMARY = Path(r"D:\finance\scratch\mon_out\results_summary.csv")
OUT = Path(r"D:\finance\scratch\curves"); OUT.mkdir(parents=True, exist_ok=True)
INITIAL = 100_000.0


def minute_equity(deals: pd.DataFrame, symbol: str, start="2026-01-01", end="2026-09-30", basis="mid"):
    """(bars index, E) with E = realized + floating P&L at the TESTED lot, per minute (the same arrays floating.rebuild reduces to days)."""
    t0, t1 = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    bars, _ = floating.bars_for(symbol, t0, t1)
    pos, _ = floating.pair_positions(deals, floating.prior_k(symbol, t0, t1))
    ts = bars.index.values.astype("datetime64[ns]").astype(np.int64)
    n = len(ts)
    bl, bh, bc, al, ah, ac = (bars[c].values for c in ("bl", "bh", "bc", "al", "ah", "ac"))
    d = deals.copy()
    d["t"] = pd.to_datetime(d.time.astype(str).str.replace(".", "-", regex=False))
    net = (d.profit + d.commission + d.swap).values
    real = np.zeros(n)
    np.add.at(real, floating._bar_idx(ts, d.t.values.astype("datetime64[ns]").astype(np.int64)), net)
    R = np.cumsum(real)
    Fm, Fh, Sh = np.zeros(n), np.zeros(n), np.zeros(n)
    for p in pos.itertuples():
        i0 = int(floating._bar_idx(ts, p.te)); i1 = int(floating._bar_idx(ts, p.tx))
        if not np.isfinite(p.k):
            continue
        kv = p.v * p.k
        if p.side == 1:
            wl, cl = (bl - p.pe) * kv, (bc - p.pe) * kv
        elif p.side == -1:
            wl, cl = (p.pe - ah) * kv, (p.pe - ac) * kv
        else:
            wl, cl = np.minimum(bl - p.pe, p.pe - ah) * kv, np.minimum(bc - p.pe, p.pe - ac) * kv
        if i1 > i0:
            Fm[i0] += cl[i0]; Fm[i0 + 1:i1] += wl[i0 + 1:i1]
            Fh[i0:i1] += wl[i0:i1]
        Sh[i1] += min(wl[i1] - net[p.i1], 0.0)
    E = R + (Fm if basis == "mid" else Fh + Sh)
    return bars.index, E, R


def attempts(day_v: pd.Series, day_m: pd.Series, days):
    """Chained 1-Step attempts over the weekdays `days`: list of (start index, end index, outcome)."""
    out, i = [], 0
    while i < len(days):
        bal = hwm = INITIAL; pos = best = 0.0; res = None
        for j in range(i, len(days)):
            d = days[j]
            v = float(day_v.get(d, 0.0)); m = min(float(day_m.get(d, 0.0)), v)
            hwm = max(hwm, bal)
            if m < -3_000 or bal + m <= hwm - 10_000:
                res = ("breach", j); break
            bal += v
            if v > 0:
                pos += v; best = max(best, v)
            if bal > 110_000 and best <= 0.5 * pos:
                res = ("pass", j); break
        if res is None:
            out.append((i, len(days) - 1, "open")); break
        out.append((i, res[1], res[0])); i = res[1] + 1
    return out


def main():
    s = pd.read_csv(SUMMARY, dtype={"id": str})
    st = pd.read_csv(RES / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last").set_index("id")
    top = s[s.rankable_e == True].head(5)
    days_all = pd.bdate_range("2026-01-01", "2026-09-30")
    data = []
    for r in top.itertuples():
        f = RES / f"{r.id}.csv"
        deals = pd.read_csv(f)
        sym, dd = str(st.loc[r.id, "symbol"]), float(st.loc[r.id, "eq_dd"])
        fl = floating.get(r.id, 2026, f, sym, dd, "2026-01-01", "2026-09-30")
        if not fl.ok:
            print(r.id, "floating not ok:", fl.status); continue
        lam = float(r.lam_frozen)
        basis = fl.diag.get("basis", "mid")
        idx, E, R = minute_equity(deals, sym, basis=basis)
        # day frames at the frozen lot
        v = (fl.v * lam); m = (fl.m * lam)
        att = attempts(v, m, days_all)
        # hourly points per attempt
        hour = pd.DatetimeIndex(idx.floor("h"))
        df = pd.DataFrame({"E": E, "R": R}, index=idx)
        day_idx = pd.DatetimeIndex(idx.normalize())
        segs = []
        for k, (a, b, outcome) in enumerate(att):
            d0, d1 = days_all[a], days_all[b]
            mask = (day_idx >= d0) & (day_idx <= d1)
            if not mask.any():
                continue
            sub = df[mask]
            first_day_start = int(np.flatnonzero(mask)[0])
            r_before = df.R.values[first_day_start - 1] if first_day_start > 0 else 0.0
            base = r_before                                   # realized P&L before the attempt: the attempt's equity is 100K + lam * (E - base)
            eq = INITIAL + lam * (sub.E.values - base)
            h = pd.DatetimeIndex(sub.index.floor("h"))
            g = pd.DataFrame({"eq": eq, "h": h}).groupby("h").agg(last=("eq", "last"), low=("eq", "min"))
            # trailing floor on end-of-day balances (closed P&L), plus the day's own start
            dd_ = pd.Series(v.reindex(days_all).fillna(0.0).values, index=days_all).loc[d0:d1]
            bal = INITIAL + dd_.cumsum()
            hwm = np.maximum.accumulate(np.maximum(bal.values, INITIAL))
            floor = hwm - 10_000
            segs.append(dict(n=k + 1, start=str(d0.date()), end=str(d1.date()), outcome=outcome, days=int((d1 - d0).days + 1),
                             t=[x.strftime("%Y-%m-%dT%H:%M") for x in g.index], eq=[round(float(x), 0) for x in g["last"]], low=[round(float(x), 0) for x in g["low"]],
                             floor_t=[x.strftime("%Y-%m-%d") for x in dd_.index], floor=[round(float(x), 0) for x in floor],
                             end_balance=round(float(INITIAL + lam * (sub.E.values[-1] - base)), 0),
                             worst=round(float(eq.min()), 0), best=round(float(eq.max()), 0)))
        title = str(st.loc[r.id, "title"])[:60]
        net_all = float(lam * (E[-1]))
        data.append(dict(id=r.id, title=title, symbol=sym, period=str(st.loc[r.id, "period"]), lam=round(lam, 2), basis=basis, ratio=round(float(fl.ratio), 2),
                         p1_30=float(r.e_p1_30), p1_60=float(r.e_p1_60), p1_86=float(r.e_p1_86), net_2026=round(net_all, 0), positions=int(fl.diag.get("positions", 0)), attempts=segs))
        print(f"{r.id} {title[:34]}: lot x{lam:.2f}, basis {basis}, ratio {fl.ratio:.2f}, 2026 net {net_all:+,.0f}; attempts: " + ", ".join(f"{a['outcome']} {a['start']}..{a['end']} ({a['days']}d)" for a in segs), flush=True)
    (OUT / "data.json").write_text(json.dumps(data, separators=(",", ":")))
    print("wrote", OUT / "data.json", (OUT / "data.json").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
