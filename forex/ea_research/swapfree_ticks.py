"""Bar 4 of PREREG_SWAPFREE_DRIFT: the D2 / D4 books on MT5 broker real ticks (server clock), 2025-10-01..2026-10-13, compared with the M1 engine on the same days.
Decision fill: first tick at or after 18:00:00.300 server (300 ms latency), buys at the ask; mark: last bid at or before 22:55:59; day low: lowest bid of the server day.
   python -m forex.ea_research.swapfree_ticks"""
import glob

import numpy as np
import pandas as pd

from forex.ea_research import swapfree_drift as S

DAY = 86_400_000


def tick_daily(m):
    fr = []
    for f in sorted(glob.glob(f"D:/finance/ticks/{m}/*.parquet")):
        t = pd.read_parquet(f, columns=["time_msc", "bid", "ask"])
        t = t[(t.bid > 0) & (t.ask > 0)]
        t["date"] = t.time_msc // DAY; ms = t.time_msc % DAY
        g = t.groupby("date")
        low = g.bid.min()
        mk = t[ms <= (22 * 3600 + 55 * 60 + 59) * 1000].groupby("date").bid.last()
        d = t[(ms >= 18 * 3600 * 1000 + 300) & (ms < 18 * 3600 * 1000 + 30 * 60 * 1000)].groupby("date")[["bid", "ask"]].first().rename(columns={"bid": "bo", "ask": "ao"})
        fr.append(pd.DataFrame({"mark": mk, "low": low}).join(d))
    out = pd.concat(fr); out = out[~out.index.duplicated(keep="last")]
    out.index = pd.to_datetime(out.index * DAY, unit="ms")
    return out.dropna(subset=["mark"])


def main():
    DE, DH = S.build("MT5"), S.build("HD"); C = S.spliced_closes(DE, DH)
    DT = {m: tick_daily(m) for m in S.MK + ("EURUSD", "USDJPY")}
    for m in S.MK:
        a = DT[m].join(DE[m], rsuffix="_m1", how="inner")
        print(f"{m}: tick days {len(DT[m])}, median spread at 18:00 ticks {float((DT[m].ao - DT[m].bo).median()):.3f} vs M1 {float((a.ao_m1 - a.bo_m1).median()):.3f}, "
              f"median |mark diff| {float((a.mark - a.mark_m1).abs().median()):.3f}, median day-low diff (tick - M1) {float((a.low - a.low_m1).median()):+.3f}")
    rows = []
    for v in ("D2", "D4"):
        tk = S.run_book(DT, C, v, "2025-10-01", "2026-10-02"); m1 = S.run_book(DE, C, v, "2025-10-01", "2026-10-02")
        tk2 = S.run_book(DT, C, v, "2025-10-01", "2026-10-13")
        r = tk.V.sum() / m1.V.sum() if m1.V.sum() else np.nan
        print(f"{v} 2025-10-01..2026-10-02: ticks {tk.V.sum():+.0f} (mean {tk.V.mean():+.1f}/day, worst low {tk.B.min():.0f}, cost {tk.attrs['cost']:.0f}) vs M1 {m1.V.sum():+.0f} "
              f"(worst low {m1.B.min():.0f}, cost {m1.attrs['cost']:.0f}) -> ratio {r:.2f} (bar >= 0.75); daily corr {np.corrcoef(tk.V.reindex(m1.index).fillna(0), m1.V)[0, 1]:.3f}; to 2026-10-13 on ticks {tk2.V.sum():+.0f}")
        rows.append(dict(variant=v, ticks=tk.V.sum(), m1=m1.V.sum(), ratio=r, ticks_to_1013=tk2.V.sum(), tick_worst_low=tk.B.min(), m1_worst_low=m1.B.min()))
        tk2.to_parquet(f"D:/finance/si_ledgers/SWAPFREE_TICKS_{v}.parquet")
    pd.DataFrame(rows).to_csv("D:/finance/si_ledgers/SWAPFREE_TICKS.csv", index=False)


if __name__ == "__main__":
    main()
