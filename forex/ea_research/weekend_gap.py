"""PREREG_WEEKEND_GAP: fade the weekend reopen gap at 01:05 server Monday, exit 10:00 (E1) or 16:00 (E2).
   python -m forex.ea_research.weekend_gap --dry-run | --run | --hold G1"""
import sys

import numpy as np
import pandas as pd

from forex.ea_research import swapfree_drift as S
from forex.ea_research import monthend_fx as M   # noqa: F401  (extends S.HDN with the FX majors)

FX = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD")
IX = ("SP", "NSDQ", "DAX", "NIKKEI", "XAUUSD")
CELLS = {"G1": (FX, 10), "G2": (FX, 16), "G3": (IX, 10), "G4": (IX, 16)}
PER = {"OOT": ("2020-01-01", "2021-11-30"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-10-02")}
ENTRY = 1 * 3600 + 5 * 60


class Q:
    def __init__(self, ts, bo, ao, bc, ac):
        self.ts, self.bo, self.ao, self.bc, self.ac = ts, bo, ao, bc, ac

    def open_at(self, t, tol=600):
        i = np.searchsorted(self.ts, t)
        if i >= len(self.ts) or self.ts[i] - t > tol: return None
        return self.bo[i], self.ao[i]

    def close_before(self, t, tol=4 * 86400):
        i = np.searchsorted(self.ts, t) - 1
        if i < 0 or t - self.ts[i] > tol: return None
        return self.bc[i], self.ac[i], self.ts[i]


def mt5q(m):
    d = pd.read_parquet(S.MT5 / f"{m}_M1_rates.parquet", columns=["t", "bo", "bc", "ao", "ac"]).sort_values("t")
    return Q(d.t.to_numpy(), d.bo.to_numpy(), d.ao.to_numpy(), d.bc.to_numpy(), d.ac.to_numpy())


def hour_spread(m):
    d = pd.read_parquet(S.MT5 / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao"]); h = (d.t // 3600) % 24
    y = pd.to_datetime(d.t, unit="s").dt.year
    return (d.ao - d.bo)[y <= 2024].groupby(h[y <= 2024]).median()


def hdq(m):
    d = S.load_hd(m); sp = hour_spread(m); h = (d.ts // 3600) % 24; s = sp.reindex(h).to_numpy()
    s = np.where(np.isnan(s), np.nanmedian(sp), s)
    return Q(d.ts.to_numpy(), d.bo.to_numpy(), d.bo.to_numpy() + s, d.bc.to_numpy(), d.bc.to_numpy() + s)


def trades(Qs, mkts, exit_h, a, b):
    rows = []
    for mon in pd.date_range(a, b, freq="W-MON"):
        t0 = int(mon.value // 10**9)
        for m in mkts:
            q = Qs.get(m)
            if q is None: continue
            fri = q.close_before(t0 - 3600)            # last bar before Monday 00:00 server
            if fri is None: continue
            fb, fa, fts = fri
            if (fts % 86400) // 60 > 22 * 60 + 55:     # use the last bar at or before 22:55 of that day
                i = np.searchsorted(q.ts, fts - (fts % 86400) + (22 * 60 + 55) * 60 + 60) - 1; fb, fa = q.bc[i], q.ac[i]
            ent = q.open_at(t0 + ENTRY); ex = q.open_at(t0 + exit_h * 3600)
            if ent is None or ex is None: continue
            eb, ea = ent; xb, xa = ex
            gap = ((eb + ea) / 2) / ((fb + fa) / 2) - 1; spr = (ea - eb) / ((eb + ea) / 2)
            if abs(gap) <= 2 * spr: continue
            side = -np.sign(gap)
            pin = ea if side > 0 else eb; pout = xb if side > 0 else xa
            rows.append(dict(monday=mon, mkt=m, gap_bp=1e4 * gap, spread_bp=1e4 * spr, side=side, bp=1e4 * side * (pout - pin) / pin))
    return pd.DataFrame(rows)


def stat(T):
    if T.empty: return dict(mondays=0, trades=0, mean=np.nan, t=np.nan)
    w = T.groupby("monday").bp.mean(); n = len(w)
    return dict(mondays=n, trades=len(T), mean=w.mean(), t=w.mean() / w.std() * np.sqrt(n) if n > 2 else np.nan, per_trade=T.bp.mean())


def main():
    QE = {m: mt5q(m) for m in FX + IX}
    QH = {m: hdq(m) for m in FX + IX if m != "DAX"}
    if "--dry-run" in sys.argv:
        for m in ("EURUSD", "SP", "XAUUSD"):
            sp = hour_spread(m); print(f"{m} MT5 broker median spread by hour (2022-24) h1 {sp.get(1, np.nan):.5f} h2 {sp.get(2, np.nan):.5f} h10 {sp.get(10, np.nan):.5f} h16 {sp.get(16, np.nan):.5f}")
        for c, (mk, h) in CELLS.items():
            for p, (a, b) in PER.items():
                if p == "HOLD": continue
                T = trades(QH if p == "OOT" else QE, mk, h, a, b)
                print(f"{c} {p}: Mondays {T.monday.nunique() if len(T) else 0}, trades {len(T)}, median |gap| {T.gap_bp.abs().median() if len(T) else 0:.1f} bp, median spread {T.spread_bp.median() if len(T) else 0:.2f} bp")
        T = trades(QE, ("EURUSD",), 10, "2024-03-04", "2024-03-04"); print("hand check 2024-03-04 EURUSD:", T.to_dict("records"))
        q = QE["EURUSD"]; t0 = int(pd.Timestamp("2024-03-04").value // 10**9)
        print("   Friday bar before:", q.close_before(t0 - 3600), "| 01:05 bar:", q.open_at(t0 + ENTRY), "| 10:00 bar:", q.open_at(t0 + 36000))
        print("truncation: the decision reads only bars with ts <= Monday 01:05 (close_before / open_at at the entry minute); the exit bar is read only for the P&L")
        return
    hold = sys.argv[sys.argv.index("--hold") + 1] if "--hold" in sys.argv else None
    rows, allT = [], []
    for c, (mk, h) in CELLS.items():
        if hold and c != hold: continue
        for p, (a, b) in PER.items():
            if (p == "HOLD") != bool(hold): continue
            T = trades(QH if p == "OOT" else QE, mk, h, a, b); T["cell"], T["period"] = c, p; allT.append(T)
            s = stat(T); rows.append(dict(cell=c, period=p, **s))
            print(f"{c} {p}: Mondays {s['mondays']}, trades {s['trades']}, mean {s['mean']:+.2f} bp net, t {s['t']:+.2f}", flush=True)
        if not hold:
            T = pd.concat([x for x in allT if x.cell.iloc[0] == c and x.period.iloc[0] in ("DEV", "VAL")]); s = stat(T)
            print(f"{c} DEV+VAL: mean {s['mean']:+.2f} bp, t {s['t']:+.2f} (bar 2.50)"); rows.append(dict(cell=c, period="DEV+VAL", **s))
    tag = f"HOLD_{hold}" if hold else "RUN"
    pd.DataFrame(rows).to_csv(f"data/si_ledgers/WEEKEND_GAP_{tag}.csv", index=False)
    pd.concat(allT).to_parquet(f"data/si_ledgers/WEEKEND_GAP_{tag}_trades.parquet")


if __name__ == "__main__":
    main()
