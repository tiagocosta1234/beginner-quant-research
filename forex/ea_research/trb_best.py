"""The best breakout the TRB grid can find in 2022-24, and what it did in 2025 and 2026 (the trader 2026-10-15: "is this truly the best the
breakouts can get? I don't believe it"). 2026 is already open for the breakout family (ORB_TREND_2026_RESULT.md).
   python -m forex.ea_research.trb_best            builds the cache to 2026-10-02 (D:/finance/tmp/trb_cache_2026) and reports"""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_research import trb

END26 = pd.Timestamp("2026-10-03").timestamp()
CACHE26 = Path("D:/finance/tmp/trb_cache_2026")
PER = {"IS 2022-24": ("2022-01-01", "2024-12-31"), "2025": ("2025-01-01", "2025-12-31"), "2026": ("2026-01-01", "2026-10-02")}


def build_one(sym):
    trb.CACHE = CACHE26
    return trb.market((sym, END26))


def labels():
    out = []
    for si, T in enumerate(trb.SLOTS):
        for li, L in enumerate(trb.LENS):
            for mi, m in enumerate(trb.MODES):
                for a, s in enumerate(trb.SLS):
                    for b, tp in enumerate(trb.TPS):
                        out.append(f"{T // 3600:02d}:{T % 3600 // 60:02d} srv box{L} {m} SL{s} TP{tp}")
    return np.array(out)


def main():
    CACHE26.mkdir(parents=True, exist_ok=True)
    todo = [s for s in trb.SYMS if not (CACHE26 / f"{s}.npz").exists()]
    with ProcessPoolExecutor(8) as ex:
        list(ex.map(build_one, todo))
    lab = labels()
    rows = []
    for s in trb.SYMS:
        z = np.load(CACHE26 / f"{s}.npz")
        days = pd.to_datetime(z["days"], unit="s")
        R = z["R"].reshape(len(days), -1)                         # [day, config]
        stats = {}
        for k, (a, b) in PER.items():
            m = (days >= a) & (days <= b)
            x = R[m]
            stats[k] = (np.sum(~np.isnan(x), 0), np.nansum(x, 0))
        n_is, tot_is = stats["IS 2022-24"]
        tot_is = np.where(n_is >= 150, tot_is, -np.inf)
        best = int(np.argmax(tot_is))
        r = dict(sym=s, best_config=lab[best])
        for k in PER:
            n, tot = stats[k][0][best], stats[k][1][best]
            r[f"n {k}"], r[f"R/trade {k}"], r[f"$ {k}"] = int(n), (tot / n if n else np.nan), tot * 1000
        rows.append(r)
    D = pd.DataFrame(rows).sort_values("R/trade IS 2022-24", ascending=False)
    D.to_csv("D:/finance/si_ledgers/TRB_BEST.csv", index=False)
    pd.set_option("display.width", 260); pd.set_option("display.max_colwidth", 40)
    cols = ["sym", "best_config", "n IS 2022-24", "R/trade IS 2022-24", "$ IS 2022-24", "R/trade 2025", "$ 2025", "R/trade 2026", "$ 2026"]
    print(D[cols].round(3).to_string(index=False))
    print(f"\nAVERAGE over 46 markets, R per trade: in-sample {D['R/trade IS 2022-24'].mean():+.3f} | 2025 {D['R/trade 2025'].mean():+.3f} | 2026 {D['R/trade 2026'].mean():+.3f}")
    print(f"markets whose best breakout made money: in-sample {np.sum(D['$ IS 2022-24'] > 0)}/46 | 2025 {np.sum(D['$ 2025'] > 0)}/46 | 2026 {np.sum(D['$ 2026'] > 0)}/46 | both 2025 and 2026 {np.sum((D['$ 2025'] > 0) & (D['$ 2026'] > 0))}/46")
    top = D.head(10)
    print(f"TOP 10 in-sample: in-sample {top['R/trade IS 2022-24'].mean():+.3f} R/trade, $ {top['$ IS 2022-24'].sum():+,.0f} | 2025 {top['R/trade 2025'].mean():+.3f}, $ {top['$ 2025'].sum():+,.0f} | 2026 {top['R/trade 2026'].mean():+.3f}, $ {top['$ 2026'].sum():+,.0f}")


if __name__ == "__main__":
    main()
