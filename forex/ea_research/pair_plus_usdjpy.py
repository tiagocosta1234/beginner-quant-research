"""Gold EA pair (as in pair_from_today.py) plus a small USDJPY London breakout leg, from today's account state.
USDJPY day P&L from the MT5 2022-26 trades (BRK_EXITS, X4_noTP) aligned by date with the pair's pool days; intraday worst of a USDJPY trade day
taken as -1R (conservative).   python -m forex.ea_research.pair_plus_usdjpy"""
import numpy as np
import pandas as pd

from forex.ea_research import combo_grid as cg
from forex.ea_research import pass70 as P
from forex.ea_research.event_macro import server_s
from forex.ea_research.pair_from_today import HN

P.C0 = -2291.92


def usdjpy_days():
    e = pd.read_parquet("data/si_ledgers/BRK_EXITS.parquet")
    e = e[(e.mkt == "USDJPY") & (e.kind == "BRK")]
    return e.groupby("day").X4_noTP.first()


def with_usdjpy(S, uj, risk):
    days = pd.to_datetime(np.asarray(S["days"], dtype=np.int64) * 86400, unit="s")      # pair days are epoch-day integers
    r = uj.reindex(days).to_numpy()
    traded = ~np.isnan(r)
    v = np.where(traded, r * risk, 0.0)
    return dict(V=S["V"] + v, B=S["B"] + np.where(traded, -risk, 0.0), Hi=S["Hi"] + np.maximum(v, 0.0), days=S["days"]), traded.mean(), np.corrcoef(S["V"][traded], v[traded])[0, 1]


def main():
    cal = pd.read_csv("data/data_macro/event_calendar.csv")
    cg.EV = np.array(sorted(server_s(r.date, 8, 30) for r in cal.itertuples() if r.kind == "CPI"))
    dip = cg.dip_days(500)
    uj = usdjpy_days()
    H = max(HN.values()) + 1
    for label, g, ms, mx, dr in (("pair x1.5 + ManualDip 500", 1500.0, 1.5, 1.5, 500), ("pair x1.2", 1500.0, 1.2, 1.2, 0)):
        base = {}
        for pool in ("MT5", "FT"):
            S = cg.pair_series(pool, ms, mx, g)
            base[pool] = cg.add_dip(S, dip, g) if dr else S
        for risk in (0, 150, 250, 400):
            res, info = {}, []
            for pool in ("MT5", "FT"):
                S = base[pool]
                if risk:
                    S, cover, corr = with_usdjpy(S, uj, risk)
                    info.append(f"{pool}: USDJPY on {cover:.0%} of days, corr with pair {corr:+.2f}")
                res[pool] = P.simulate([S] * len(P.MULTS), P.I12, H)
            out = []
            for k, n in HN.items():
                pp = 50 * sum(np.mean((res[p][0] == 1) & (res[p][1] < n)) for p in res)
                bb = 50 * sum(np.mean((res[p][0] == 2) & (res[p][1] < n)) for p in res)
                out.append(f"{k} {pp:.1f}% ({bb:.1f}%)")
            print(f"{label} + USDJPY ${risk}: " + " | ".join(out) + ("   [" + "; ".join(info) + "]" if info else ""))


if __name__ == "__main__":
    main()
