"""How far do MT5 broker prices jump in the first seconds of a US release? (descriptive) CPI / NFP (08:30 NY) and FOMC (14:00 NY) in the MT5 broker tick era
(Oct 2025 - Oct 2026), real ticks of XAUUSD, NSDQ, SP, USDJPY, EURUSD: the largest mid move within 10 s and 60 s of the release (vs the last
mid before it), the spread 1 s after, and the move in units of the daily card's typical stop (gold: 0.26% of price, Nasdaq: 0.20%;
USDJPY: its median London box 0.13%; SP / EURUSD: 0.20% / 0.10% for scale).   python -m forex.ea_research.news_gaps"""
import glob

import numpy as np
import pandas as pd

from forex.ea_research.event_macro import server_s

STOP_PCT = {"XAUUSD": 0.26, "NSDQ": 0.20, "SP": 0.20, "USDJPY": 0.13, "EURUSD": 0.10}


def load(sym):
    t = pd.concat([pd.read_parquet(f, columns=["time_msc", "bid", "ask"]) for f in sorted(glob.glob(f"D:/finance/ticks/{sym}/*.parquet"))])
    t = t[(t.bid > 0) & (t.ask >= t.bid)].sort_values("time_msc")
    return t.time_msc.to_numpy(np.int64), t.bid.to_numpy(), t.ask.to_numpy()


def main():
    cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv")
    cal = cal[(cal.date >= "2025-10-01") & (cal.date <= "2026-10-12")]
    ev = [(r.kind, r.date, server_s(r.date, 14, 0) if r.kind == "FOMC" else server_s(r.date, 8, 30)) for r in cal.itertuples()]
    rows = []
    for sym, pct in STOP_PCT.items():
        ms, bid, ask = load(sym)
        mid = (bid + ask) / 2
        for kind, day, s in ev:
            t0 = s * 1000
            i0 = np.searchsorted(ms, t0) - 1
            if i0 < 0 or t0 - ms[i0] > 60_000:
                continue
            m0 = mid[i0]
            out = dict(sym=sym, kind=kind, day=day, spread_before=ask[i0] - bid[i0])
            for sec in (10, 60):
                j = np.searchsorted(ms, t0 + sec * 1000)
                seg = mid[i0 + 1:j]
                if len(seg) == 0:
                    out[f"move{sec}"] = np.nan
                    continue
                out[f"move{sec}"] = np.max(np.abs(seg - m0))
            j1 = np.searchsorted(ms, t0 + 1000)
            out["spread_after"] = ask[min(j1, len(ask) - 1)] - bid[min(j1, len(bid) - 1)]
            stop = pct / 100 * m0
            out["R10"], out["R60"] = out["move10"] / stop, out["move60"] / stop
            rows.append(out)
    T = pd.DataFrame(rows)
    T.to_csv("D:/finance/si_ledgers/NEWS_GAPS.csv", index=False)
    pd.set_option("display.width", 200)
    g = T.groupby(["sym", "kind"]).agg(events=("R10", "size"), move10_median=("move10", "median"), R10_median=("R10", "median"), R10_max=("R10", "max"),
                                       share_R10_over_1=("R10", lambda x: np.mean(x > 1)), R60_median=("R60", "median"), share_R60_over_1=("R60", lambda x: np.mean(x > 1)),
                                       spread_before=("spread_before", "median"), spread_after=("spread_after", "median"))
    print(g.round(3).to_string())
    big = T.sort_values("R10", ascending=False).head(8)
    print("\nlargest 10-second moves (in card stops):")
    print(big[["sym", "kind", "day", "move10", "R10", "spread_after"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
