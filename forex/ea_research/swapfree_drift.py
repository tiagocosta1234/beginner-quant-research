"""Swap-free drift book (PREREG_SWAPFREE_DRIFT.md): long-only inverse-vol book of SP, NSDQ, DAX, NIKKEI, XAUUSD, weekly decisions Monday 18:00 server.
   python -m forex.ea_research.swapfree_drift --dry-run     counts, truncation test, hand check (no P&L)
   python -m forex.ea_research.swapfree_drift --run         DEV / VAL / OOT (HOLD stays closed)
   python -m forex.ea_research.swapfree_drift --hold D2     the one HOLD look for a variant that passed development"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

MT5 = Path("D:/finance/beginner-quant-research/forex/data_mt5")
HD = Path("D:/finance/data_histdata")
OUTD = Path("D:/finance/si_ledgers")
MK = ("SP", "NSDQ", "DAX", "NIKKEI", "XAUUSD")
HDN = {"SP": "SPXUSD", "NSDQ": "NSXUSD", "DAX": "GRXEUR", "NIKKEI": "JPXJPY", "XAUUSD": "XAUUSD", "EURUSD": "EURUSD", "USDJPY": "USDJPY"}
CCY = {"DAX": "EURUSD", "NIKKEI": "USDJPY"}
DEC_MIN = 18 * 60          # decision minute of the server day
MARK_MIN = 22 * 60 + 55    # daily mark: last bar at or before 22:55 server
DROP_DAX_OOT = True
VOLN, SMAN, WD = 60, 200, 0  # registered values (sensitivity runs change them): vol window, SMA length, first weekday allowed for the weekly decision
VARIANTS = ("D1", "D2", "D3", "D4")
PER = {"OOT": ("2020-01-01", "2021-11-30"), "DEV": ("2022-01-03", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-10-02")}


# ---------------------------------------------------------------- M1 loading (server clock epoch seconds)
def load_mt5(m):
    d = pd.read_parquet(MT5 / f"{m}_M1_rates.parquet", columns=["t", "bo", "bl", "bc", "ao"])
    return d.rename(columns={"t": "ts"})


def load_hd(m):
    sym = HDN[m]; pq = HD / f"{sym}.parquet"
    if pq.exists() and sym in ("NSXUSD", "USDJPY"):
        d = pd.read_parquet(pq); utc = d.t_utc.to_numpy()
    else:
        fr = []
        for yr in (2020, 2021):
            z = zipfile.ZipFile(HD / f"DAT_ASCII_{sym}_M1_{yr}.zip"); n = [x for x in z.namelist() if x.lower().endswith(".csv")][0]
            fr.append(pd.read_csv(io.BytesIO(z.read(n)), sep=";", header=None, names=["dt", "bo", "bh", "bl", "bc", "v"]))
        d = pd.concat(fr)
        utc = (pd.to_datetime(d.dt, format="%Y%m%d %H%M%S") + pd.Timedelta(hours=5)).astype("datetime64[s]").astype("int64").to_numpy()
    srv = pd.to_datetime(utc, unit="s", utc=True).tz_convert("Europe/Athens").tz_localize(None).astype("datetime64[s]").astype("int64")
    out = pd.DataFrame({"ts": np.asarray(srv), "bo": d.bo.to_numpy(), "bl": d.bl.to_numpy(), "bc": d.bc.to_numpy()})
    out = out.sort_values("ts").drop_duplicates("ts")
    return out[out.ts < pd.Timestamp("2021-12-01").value // 10**9]


def mt5_spread18(m):
    d = load_mt5(m); h = (d.ts // 3600) % 24; y = pd.to_datetime(d.ts, unit="s").dt.year
    s = (d.ao - d.bo)[(h == 18) & (y <= 2024)]
    return float(s.median())


def daily(d, spread=None):
    """Per server date: mark (bid close of last bar <= 22:55), day low (min bid low), decision bar (first bar at/after 18:00): bid open, ask open."""
    d = d.copy(); d["date"] = d.ts // 86400; d["mn"] = (d.ts % 86400) // 60
    if "ao" not in d: d["ao"] = d.bo + spread
    g = d.groupby("date")
    low = g.bl.min()
    mk = d[d.mn <= MARK_MIN].groupby("date").bc.last()
    dec = d[(d.mn >= DEC_MIN) & (d.mn < DEC_MIN + 30)].groupby("date")[["bo", "ao"]].first()
    out = pd.DataFrame({"mark": mk, "low": low}).join(dec)
    out.index = pd.to_datetime(out.index * 86400, unit="s")
    return out.dropna(subset=["mark"])


def build(source):
    """source 'MT5' or 'HD'. Returns dict of daily frames for the 5 markets + fx marks."""
    D = {}
    for m in MK + ("EURUSD", "USDJPY"):
        if source == "MT5": D[m] = daily(load_mt5(m))
        else: D[m] = daily(load_hd(m), spread=mt5_spread18(m) if m in MK else 0.0)
    return D


def spliced_closes(DE, DH):
    """Signal series: HistData closes before 2021-12-01 ratio-spliced to MT5 broker marks."""
    C = {}
    for m in MK:
        e, h = DE[m].mark, DH[m].mark
        if m == "DAX": h = h[h.index >= "2020-06-15"]   # Amendment 1: HistData GRXEUR is another index after 2020-06-12
        r = e.iloc[0] / h.iloc[-1]
        C[m] = pd.concat([h * r, e])
    return pd.DataFrame(C).sort_index().ffill()  # engine fix: holidays differ by market; forward fill uses only the past


# ---------------------------------------------------------------- signals (causal: closes strictly before the decision date)
def signals(C, day, variant):
    past = C[C.index < day]
    if len(past) < VOLN + 1:  # warm-up: no decision without VOLN daily returns (engine fix, not a tuning choice)
        z = pd.Series(0.0, index=C.columns); return z, z > 0
    ret = np.log(past).diff().iloc[-VOLN:]
    vol = ret.std() * np.sqrt(252)
    w = (1 / vol) / (1 / vol).sum()
    on = pd.Series(True, index=C.columns)
    if variant in ("D2", "D4"):
        on = past.iloc[-1] > past.iloc[-SMAN:].mean()
        if past.iloc[-SMAN:].notna().sum().min() < SMAN: on[:] = False
    scale = 1.0
    if variant in ("D3", "D4"):
        cov = ret.cov() * 252
        s_unit = float(np.sqrt(w.to_numpy() @ cov.to_numpy() @ w.to_numpy()))
        scale = min(2.0, 0.12 / s_unit)
    return w * on * scale, on


# ---------------------------------------------------------------- book simulation (USD per unit gross G = 1)
def run_book(D, C, variant, start, end, G=100_000.0):
    mk = tuple(m for m in MK if not (DROP_DAX_OOT and m == "DAX" and D[m].index.max() < pd.Timestamp("2021-12-01")))  # Amendment 1: no DAX P&L in the HistData OOT
    days = sorted(set().union(*[set(D[m].index) for m in mk]))
    days = [x for x in days if pd.Timestamp(start) <= x <= pd.Timestamp(end) and x.weekday() < 5]
    fx = {m: (D[CCY[m]].mark if m in CCY else None) for m in MK}

    def usd(m, x):  # price-unit P&L -> USD on day x
        if m not in CCY: return 1.0
        f = fx[m]; g = f[f.index <= x]; v = g.iloc[-1] if len(g) else f.iloc[0]
        return v if CCY[m].endswith("USD") else 1.0 / v   # EURUSD / AUDUSD multiply, USDJPY divides

    u = {m: 0.0 for m in MK}; prev = {m: np.nan for m in MK}; last_on = {m: None for m in MK}
    rows = []; week = None; ntr = 0; cost_tot = 0.0; bym = {m: 0.0 for m in mk}
    for x in days:
        V = 0.0; B = 0.0; cost = 0.0
        wk = x.isocalendar()[:2]
        decide = wk != week and x.weekday() >= WD and all(not np.isnan(D[m].bo.get(x, np.nan)) for m in mk)
        new = dict(u)
        if decide:
            week = wk
            w, on = signals(C[list(mk)], x, variant)
            for m in mk:
                px = D[m].bo[x] * usd(m, x)
                tgt = G * w[m] / px
                flip = last_on[m] is not None and bool(on[m]) != last_on[m]
                if u[m] == 0 or tgt == 0 or abs(tgt - u[m]) > 0.25 * abs(tgt) or flip:
                    new[m] = tgt
                last_on[m] = bool(on[m])
        for m in mk:
            r = D[m].loc[x] if x in D[m].index else None
            if r is None: continue
            k = usd(m, x); p0 = prev[m]
            if np.isnan(p0): p0 = r.mark if np.isnan(r.bo) else r.bo
            V0 = V
            if decide and new[m] != u[m]:
                ntr += 1
                V += u[m] * (r.bo - p0) * k
                dq = new[m] - u[m]
                c = max(dq, 0) * (r.ao - r.bo) * k; cost += c
                V += new[m] * (r.mark - r.bo) * k - c
            else:
                V += u[m] * (r.mark - p0) * k
            bym[m] += V - V0
            B += max(u[m], new[m]) * min(0.0, r.low - p0) * k
            prev[m] = r.mark
        u = new
        cost_tot += cost
        rows.append((x, V, min(B - cost, V, 0.0)))
    out = pd.DataFrame(rows, columns=["day", "V", "B"]).set_index("day")
    out.attrs.update(trades=ntr, cost=cost_tot, bym=bym)
    return out


def stats(s):
    v = s.V; n = len(v); m = v.mean(); sd = v.std()
    return dict(days=n, mean=m, t=m / sd * np.sqrt(n) if sd > 0 else 0, sharpe=m / sd * np.sqrt(252) if sd > 0 else 0, total=v.sum(),
                maxdd=float((v.cumsum() - v.cumsum().cummax()).min()), worst_day=float(s.B.min()))


# ---------------------------------------------------------------- dry run
def dry():
    DE, DH = build("MT5"), build("HD")
    C = spliced_closes(DE, DH)
    for src, D in (("MT5", DE), ("HD", DH)):
        for m in MK:
            f = D[m]; print(f"{src} {m}: {len(f)} days {f.index.min().date()}..{f.index.max().date()}, decision bars {f.bo.notna().sum()}, spread18 median {float((f.ao - f.bo).median()):.3f}")
    print("splice ratios check (MT5 broker first mark / HD last mark):", {m: round(DE[m].mark.iloc[0] / DH[m].mark.iloc[-1], 4) for m in MK})
    # truncation test: signals on a decision day must not change when all data after that day is cut
    for x in (pd.Timestamp("2022-06-13"), pd.Timestamp("2024-03-04"), pd.Timestamp("2021-03-01")):
        for v in VARIANTS:
            a, _ = signals(C, x, v); b, _ = signals(C[C.index <= x], x, v)
            assert np.allclose(a.fillna(0), b.fillna(0)), (x, v)
    print("truncation test passed (signals identical with the future cut)")
    x = pd.Timestamp("2024-03-04"); past = C[C.index < x]; r = np.log(past).diff().iloc[-60:]
    vol = r.std() * np.sqrt(252); print("hand check 2024-03-04: vol", vol.round(4).to_dict(), "-> w", ((1 / vol) / (1 / vol).sum()).round(4).to_dict())
    print("signals D2", signals(C, x, "D2")[1].to_dict())
    for p, (a, b) in PER.items():
        if p == "HOLD": continue
        D = DH if p == "OOT" else DE
        n = len([d for d in D["SP"].index if pd.Timestamp(a) <= d <= pd.Timestamp(b)])
        print(f"{p}: {n} SP days")
    return DE, DH, C


def main():
    if "--dry-run" in sys.argv:
        dry(); return
    DE, DH = build("MT5"), build("HD"); C = spliced_closes(DE, DH)
    hold = sys.argv[sys.argv.index("--hold") + 1] if "--hold" in sys.argv else None
    rows = []; series = {}
    for v in VARIANTS if hold is None else (hold,):
        for p, (a, b) in PER.items():
            if (p == "HOLD") != (hold is not None): continue
            s = run_book(DH if p == "OOT" else DE, C, v, a, b)
            series[(v, p)] = s
            st = stats(s); st.update(variant=v, period=p, trades=s.attrs["trades"], cost=s.attrs["cost"]); rows.append(st)
            print(f"{v} {p}: mean {st['mean']:+.1f} USD/day per 100k gross, t {st['t']:+.2f}, Sharpe {st['sharpe']:+.2f}, total {st['total']:+.0f}, maxDD {st['maxdd']:.0f}, worst day low {st['worst_day']:.0f}, trades {st['trades']}, cost {st['cost']:.0f}", flush=True)
        if hold is None:
            dv = pd.concat([series[(v, "DEV")], series[(v, "VAL")]])
            st = stats(dv); print(f"{v} DEV+VAL: t {st['t']:+.2f} Sharpe {st['sharpe']:+.2f}  (bar t >= 2.24)")
            rows.append({**st, "variant": v, "period": "DEV+VAL"})
    T = pd.DataFrame(rows)
    tag = "HOLD_" + hold if hold else "RUN"
    T.to_csv(OUTD / f"SWAPFREE_{tag}.csv", index=False)
    pd.concat({f"{k[0]}_{k[1]}": s for k, s in series.items()}).to_parquet(OUTD / f"SWAPFREE_{tag}_series.parquet")


if __name__ == "__main__":
    main()
