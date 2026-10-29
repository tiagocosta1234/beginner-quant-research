"""Month-end FX rebalancing into the London 16:00 fix (PREREG_MONTHEND_FX.md).
   python -m forex.ea_research.monthend_fx --dry-run | --run | --hold M1"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from forex.ea_research import swapfree_drift as S

S.HDN.update({"ASX": "AUXAUD", "GBPUSD": "GBPUSD", "USDCHF": "USDCHF", "AUDUSD": "AUDUSD", "USDCAD": "USDCAD", "NZDUSD": "NZDUSD"})
PAIRS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD")
USD_BASE = {"USDJPY", "USDCHF", "USDCAD"}          # long USD = long the pair
IDX = ("SP", "DAX", "NIKKEI", "ASX")
SPEC = {"EURUSD": "DAX", "USDJPY": "NIKKEI", "AUDUSD": "ASX"}
CELLS = {"M1": dict(sig="basket", pairs=PAIRS, ent=16 * 60, ext=18 * 60, sign=1),
         "M2": dict(sig="basket", pairs=PAIRS, ent=10 * 60, ext=18 * 60, sign=1),
         "M3": dict(sig="spec", pairs=tuple(SPEC), ent=16 * 60, ext=18 * 60, sign=1),
         "M4": dict(sig="basket", pairs=PAIRS, ent=18 * 60, ext=20 * 60, sign=-1)}
PER = {"OOT": ("2020-01-01", "2021-11-30"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SIG_MIN = 16 * 60


class Mkt:
    def __init__(self, d, spread=None):
        d = d.sort_values("ts"); self.ts = d.ts.to_numpy(); self.bo = d.bo.to_numpy(); self.bc = d.bc.to_numpy()
        self.ao = d.ao.to_numpy() if "ao" in d else self.bo + spread

    def at_open(self, t, tol=300):
        """bar opening at t (or the first within tol seconds after it): bid, ask."""
        i = np.searchsorted(self.ts, t)
        if i >= len(self.ts) or self.ts[i] - t > tol: return np.nan, np.nan
        return self.bo[i], self.ao[i]

    def last_close(self, t, tol=6 * 3600):
        i = np.searchsorted(self.ts, t, side="left") - 1   # bars that CLOSED before t (bar opening at t-60 closes at t)
        if i < 0 or t - self.ts[i] > tol: return np.nan
        return self.bc[i]


def markets(src):
    out = {}
    for m in IDX + PAIRS:
        if src == "MT5": out[m] = Mkt(S.load_mt5(m))
        else:
            d = S.load_hd(m); out[m] = Mkt(d, spread=S.mt5_spread18(m) if m in PAIRS else 0.0)
    return out


def month_days(M, a, b, which="last"):
    days = pd.bdate_range(a, b); g = pd.Series(days, index=days).groupby([days.year, days.month])
    res = []
    for _, s in g:
        cand = list(s) if which == "last" else list(s)
        if which == "last": cand = cand[::-1]
        else: cand = cand[9:] if len(cand) > 9 else []
        for d in cand:  # last weekday with an MT5/HD bar at the signal minute on SP and EURUSD
            t = int(d.value // 10**9) + SIG_MIN * 60
            if not np.isnan(M["EURUSD"].at_open(t)[0]) and not np.isnan(M["SP"].last_close(t)):
                res.append(d); break
    return res


def signals(M, day, prev_day, smin=SIG_MIN):
    t1 = int(day.value // 10**9) + smin * 60; t0 = int(prev_day.value // 10**9) + smin * 60
    r = {m: np.log(M[m].last_close(t1) / M[m].last_close(t0)) for m in IDX}
    return {"basket": r["SP"] - np.nanmean([r["DAX"], r["NIKKEI"], r["ASX"]]), **{p: r["SP"] - r[SPEC[p]] for p in SPEC}}, r


def trades(M, cell, a, b, control=False):
    c = CELLS[cell]; rows = []
    ends = month_days(M, "2019-12-01" if a < "2022" else "2021-11-01", b, "last")
    for i in range(1, len(ends)):
        prev = ends[i - 1]
        if control:
            mids = month_days(M, ends[i].replace(day=1).strftime("%Y-%m-%d"), ends[i].strftime("%Y-%m-%d"), "mid")
            if not mids: continue
            day = mids[0]
        else:
            day = ends[i]
        if not (pd.Timestamp(a) <= day <= pd.Timestamp(b)): continue
        sg, _ = signals(M, day, prev, min(c["ent"], SIG_MIN))  # signal measured no later than the entry minute
        for p in c["pairs"]:
            s = sg["basket"] if c["sig"] == "basket" else sg[p]
            if not np.isfinite(s) or s == 0: continue
            usd = -np.sign(s) * c["sign"]            # +1 = buy USD
            side = usd if p in USD_BASE else -usd    # +1 = buy the pair
            t_in = int(day.value // 10**9) + c["ent"] * 60; t_out = int(day.value // 10**9) + c["ext"] * 60
            bi, ai = M[p].at_open(t_in); bo_, ao_ = M[p].at_open(t_out)
            if np.isnan(bi) or np.isnan(bo_): continue
            ent = ai if side > 0 else bi; ex = bo_ if side > 0 else ao_
            rows.append(dict(day=day, pair=p, side=side, sig=s, bp=1e4 * side * (ex - ent) / ent, gross=1e4 * side * ((bo_ + ao_) - (bi + ai)) / (bi + ai)))
    return pd.DataFrame(rows)


def stat(T):
    if T.empty: return dict(months=0, trades=0, mean=np.nan, t=np.nan, gross=np.nan)
    m = T.groupby("day").bp.mean(); n = len(m)
    return dict(months=n, trades=len(T), mean=m.mean(), t=m.mean() / m.std() * np.sqrt(n) if n > 2 else np.nan, gross=T.gross.mean(), per_trade=T.bp.mean())


def main():
    ME, MH = markets("MT5"), markets("HD")
    if "--dry-run" in sys.argv:
        for src, M, per in (("HD", MH, ("OOT",)), ("MT5", ME, ("DEV", "VAL"))):
            for p in per:
                a, b = PER[p]; T = trades(M, "M1", a, b)
                print(f"{src} {p}: month-ends {T.day.nunique()}, trades {len(T)}, pairs {T.pair.value_counts().to_dict()}")
        d0, d1 = pd.Timestamp("2024-02-29"), pd.Timestamp("2024-03-28")
        sg, r = signals(ME, d1, d0)
        print("hand check Mar 2024: index month log returns", {k: round(v, 5) for k, v in r.items()}, "basket signal", round(sg["basket"], 5))
        t1 = int(d1.value // 10**9) + SIG_MIN * 60
        print("   SP last close before", pd.to_datetime(t1, unit="s"), ME["SP"].last_close(t1), "| EURUSD bar at 16:00", ME["EURUSD"].at_open(t1))
        # truncation: cut every market after the decision minute, signal identical
        for d0, d1 in ((pd.Timestamp("2022-05-31"), pd.Timestamp("2022-06-30")), (pd.Timestamp("2025-02-28"), pd.Timestamp("2025-03-31"))):
            t1 = int(d1.value // 10**9) + SIG_MIN * 60; cut = {}
            for m, x in ME.items():
                k = np.searchsorted(x.ts, t1); y = Mkt.__new__(Mkt); y.ts, y.bo, y.bc, y.ao = x.ts[:k], x.bo[:k], x.bc[:k], x.ao[:k]; cut[m] = y
            assert np.isclose(signals(ME, d1, d0)[0]["basket"], signals(cut, d1, d0)[0]["basket"]), d1
        print("truncation test passed")
        return
    hold = sys.argv[sys.argv.index("--hold") + 1] if "--hold" in sys.argv else None
    rows = []; allT = []
    for cell in (CELLS if hold is None else (hold,)):
        for p, (a, b) in PER.items():
            if (p == "HOLD") != (hold is not None): continue
            T = trades(MH if p == "OOT" else ME, cell, a, b); T["cell"], T["period"] = cell, p; allT.append(T)
            s = stat(T); rows.append(dict(cell=cell, period=p, **s))
            print(f"{cell} {p}: months {s['months']}, trades {s['trades']}, monthly mean {s['mean']:+.2f} bp net (gross {s['gross']:+.2f}), t {s['t']:+.2f}", flush=True)
        if hold is None:
            T = pd.concat([x for x in allT if x.cell.iloc[0] == cell and x.period.iloc[0] in ("DEV", "VAL")]); s = stat(T)
            print(f"{cell} DEV+VAL: monthly mean {s['mean']:+.2f} bp, t {s['t']:+.2f} (bar 2.40)")
            rows.append(dict(cell=cell, period="DEV+VAL", **s))
            for p in ("DEV", "VAL"):
                C = trades(ME, cell, *PER[p], control=True); sc = stat(C)
                print(f"   control (business day 10) {p}: mean {sc['mean']:+.2f} bp, t {sc['t']:+.2f}")
                rows.append(dict(cell=cell, period=f"CONTROL_{p}", **sc))
    tag = f"HOLD_{hold}" if hold else "RUN"
    pd.DataFrame(rows).to_csv(f"data/si_ledgers/MONTHEND_{tag}.csv", index=False)
    pd.concat(allT).to_parquet(f"data/si_ledgers/MONTHEND_{tag}_trades.parquet")


if __name__ == "__main__":
    main()
