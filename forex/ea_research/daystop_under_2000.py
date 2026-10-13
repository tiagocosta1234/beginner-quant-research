"""the trader 2026-10-11: "(original wording omitted)". Guard day-stop level vs worst realised day at x1.5 (no-hedge off),
   and the cost in pass probability (pass70 rules, start +560).   python -m forex.ea_research.daystop_under_2000 (NEWS=1 for the news-flat test)"""
import numpy as np, pandas as pd
from forex.ea_research import clean_boot_lib as L
from forex.ea_research import pass70 as P
from forex.ea_batch.mt5_mc_config import CH

P.C0 = 560.0


def grid():
    for stop in (2000, 1800, 1700, 1600, 1500):
        out, res = [], {}
        for pool in ("MT5", "FT"):
            src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b)
            tr = L.merge(L.ea_trades(src, "sdb", CH["sdb"] * 1.5, lo), L.ea_trades(src, "xau5", CH["xau5"] * 1.5, lo))
            r = L.C.simulate(L.bars(), tr, lo, hi, None, float(stop)); S = dict(V=r["V"], B=r["B"], Hi=r["Hi"], days=r["days"])
            worst = min(S["V"].min(), S["B"].min()); over = int((np.minimum(S["V"], S["B"]) < -2000).sum())
            st, day = P.simulate([S] * len(P.MULTS), P.I12, 52); res[pool] = {h: P.p_by(st, day, n) for h, n in P.HORIZONS.items()}
            out.append(f"{pool}: worst day {worst:,.0f}, days below -2,000: {over} of {len(S['V'])}, mean/day {S['V'].mean():.0f}")
        mix = {h: 50 * (res['MT5'][h][0] + res['FT'][h][0]) for h in P.HORIZONS}; br = 50 * (res['MT5']['22 Dec'][1] + res['FT']['22 Dec'][1])
        print(f"stop {stop}: " + " | ".join(out) + f" || P(pass) MIX 30 Nov {mix['30 Nov']:.1f}% 22 Dec {mix['22 Dec']:.1f}% breach {br:.1f}%")


def news_flat(tr, events, bars):
    """Close every position still open 2 minutes before a release (CPI / NFP 08:30 NY, FOMC 14:00 NY) at that minute's bid/ask;
    trades whose entry falls in [release - 2 min, release + 5 min] are skipped."""
    tm, bc, sp = bars; tr = {k: v.copy() for k, v in tr.items()}; keep = np.ones(len(tr["in_s"]), bool)
    for T in events:
        cut = T - 120; i = int(np.searchsorted(tm, cut)); bid = bc[min(i, len(tm) - 1)]; ask = bid + sp[min(i, len(tm) - 1)]
        op = (tr["in_s"] < cut) & (tr["out_s"] > cut) & keep
        for j in np.nonzero(op)[0]:
            px = bid if tr["side"][j] > 0 else ask; tr["pl"][j] = tr["side"][j] * (px - tr["entry"][j]) * tr["q"][j]; tr["out_s"][j] = cut
        keep &= ~((tr["in_s"] >= cut) & (tr["in_s"] <= T + 300))
    return {k: v[keep] for k, v in tr.items()}


def news_test(stop=1700.0):
    from forex.ea_research.event_macro import server_s
    cal = pd.read_csv("D:/finance/data_macro/event_calendar.csv")
    ev = sorted(server_s(r.date, 8, 30) if r.kind in ("CPI", "NFP") else server_s(r.date, 14, 0) for r in cal.itertuples() if r.kind in ("CPI", "NFP", "FOMC"))
    ev = np.array(ev); res = {}; info = []
    for pool in ("MT5", "FT"):
        src, a, b = L.POOLS[pool]; lo, hi = L.day(a), L.day(b); bars = L.bars()
        tr = news_flat(L.merge(L.ea_trades(src, "sdb", CH["sdb"] * 1.5, lo), L.ea_trades(src, "xau5", CH["xau5"] * 1.5, lo)), ev, bars)
        r = L.C.simulate(bars, tr, lo, hi, None, stop); S = dict(V=r["V"], B=r["B"], Hi=r["Hi"], days=r["days"])
        w = np.minimum(S["V"], S["B"]); info.append(f"{pool}: worst day {w.min():,.0f}, days below -2,000: {(w < -2000).sum()}, mean/day {S['V'].mean():.0f}")
        st, day = P.simulate([S] * len(P.MULTS), P.I12, 52); res[pool] = {h: P.p_by(st, day, n) for h, n in P.HORIZONS.items()}
    print(f"NEWS-FLAT (CPI/NFP/FOMC) + stop {stop:.0f}: " + " | ".join(info) + f" || MIX 30 Nov {50*(res['MT5']['30 Nov'][0]+res['FT']['30 Nov'][0]):.1f}% 22 Dec {50*(res['MT5']['22 Dec'][0]+res['FT']['22 Dec'][0]):.1f}% breach {50*(res['MT5']['22 Dec'][1]+res['FT']['22 Dec'][1]):.1f}%")


if __name__ == "__main__":
    import os
    news_test() if os.environ.get("NEWS") else grid()   # clean_boot_lib rewrites sys.argv, so the switch is an env var
