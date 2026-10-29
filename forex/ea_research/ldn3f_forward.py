"""LDN3F forward test (PREREG_LDN3F.md): London 30-min breakout 1:1 with the three entry filters.
READ-ONLY MT5 use: initialize, symbols_get, copy_rates_range, shutdown. Never sends orders.
Usage: python -m forex.ea_research.ldn3f_forward [--since 2026-10-19] [--until YYYY-MM-DD]
Writes data/scratch/ldn3f/forward.csv (one row per market-day with a trigger) and prints the status."""
import argparse, datetime as dt, glob, os, numpy as np, pandas as pd
from zoneinfo import ZoneInfo
from forex.ea_research.orbx import walk, ct, CRYPTO

TERMINAL = os.getenv("MT5_TERMINAL") or r"C:\Program Files\MetaTrader 5\terminal64.exe"
SRV, LIS = ZoneInfo("Europe/Athens"), ZoneInfo("Europe/London")
OUT = "data/scratch/ldn3f/forward.csv"
MARKETS = sorted(os.path.basename(f)[:-17] for f in glob.glob("forex/data_mt5/*_M1_rates.parquet"))
MARKETS = [m for m in MARKETS if m not in CRYPTO]


def smin(day, h, m):
    t = pd.Timestamp(day.year, day.month, day.day, h, m, tz=LIS).tz_convert(SRV)
    return t.hour * 60 + t.minute


def pull(since, until):
    import MetaTrader5 as mt5
    assert mt5.initialize(path=TERMINAL), mt5.last_error()
    try:
        names = {s.name.rstrip("+"): s.name for s in mt5.symbols_get()}
        out = {}
        start = dt.datetime.combine(since - dt.timedelta(days=45), dt.time())
        end = dt.datetime.combine(until + dt.timedelta(days=1), dt.time())
        for m in MARKETS:
            if m not in names:
                print("no symbol for", m); continue
            info = mt5.symbol_info(names[m])
            r = mt5.copy_rates_range(names[m], mt5.TIMEFRAME_M1, start, end)
            if r is None or len(r) == 0:
                print("no rates for", m); continue
            d = pd.DataFrame(r)
            pt = info.point
            d = d.rename(columns={"time": "t", "open": "bo", "high": "bh", "low": "bl", "close": "bc"})
            for a, b in (("ao", "bo"), ("ah", "bh"), ("al", "bl"), ("ac", "bc")):
                d[a] = d[b] + d.spread * pt
            out[m] = d[["t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]]
        return out
    finally:
        mt5.shutdown()


def trades(sym, d, since):
    t = pd.to_datetime(d.t, unit="s"); d = d.assign(day=t.dt.normalize(), hm=t.dt.hour * 60 + t.dt.minute)
    mh, ml, mc = (d.bh + d.ah) / 2, (d.bl + d.al) / 2, (d.bc + d.ac) / 2
    D = pd.DataFrame({"h": mh.groupby(d.day).max(), "l": ml.groupby(d.day).min(), "c": mc.groupby(d.day).last()})
    D = D[D.index.weekday < 5]
    D["atr20"] = (D.h - D.l).shift(1).rolling(20, min_periods=15).mean()
    D["r5"] = D.c.shift(1) - D.c.shift(6)
    rows = []
    for day, g in d.groupby("day"):
        if day < pd.Timestamp(since) or day.weekday() >= 5 or day not in D.index:
            continue
        hm = g.hm.to_numpy(); b0, b1, e_end, x_end = smin(day, 8, 0), smin(day, 8, 30), smin(day, 10, 0), smin(day, 17, 0)
        bm = (hm >= b0) & (hm < b1)
        if bm.sum() < 25 or hm.max() < x_end - 1:
            continue                                   # box incomplete or day not finished yet
        bh, bl, bo, bc = g.bh.to_numpy(), g.bl.to_numpy(), g.bo.to_numpy(), g.bc.to_numpy()
        ah, al, ao, ac = g.ah.to_numpy(), g.al.to_numpy(), g.ao.to_numpy(), g.ac.to_numpy()
        hi, lo = bh[bm].max(), bl[bm].min(); S = hi - lo
        idx = np.flatnonzero((hm >= b1) & (hm < x_end))
        if S <= 0 or len(idx) < 30:
            continue
        fill = None
        for i, j in enumerate(idx):
            if hm[j] >= e_end:
                break
            if ah[j] >= hi:
                fill = (i, 1, max(hi, ao[j]), hi + S, lo); break
            if bl[j] <= lo:
                fill = (i, -1, min(lo, bo[j]), lo - S, hi); break
        if fill is None:
            continue
        i, side, e, tp, sl = fill
        seg = (bo[idx], bh[idx], bl[idx], bc[idx]) if side == 1 else (ao[idx], ah[idx], al[idx], ac[idx])
        ex = walk(*seg, i, side, tp, sl)
        spread = np.median(ac[bm] - bc[bm]); atr = D.loc[day, "atr20"]
        tr5 = side * D.loc[day, "r5"] / atr if atr > 0 else np.nan
        delay = hm[idx[i]] - b1
        f1, f2, f3 = S / spread >= 33.3 if spread > 0 else True, delay > 8, tr5 < 0.59
        rows.append(dict(day=day.date(), sym=sym, side=side, R=(ex - e) * side / abs(e - sl), box_spread=S / spread if spread > 0 else np.inf,
                         delay=int(delay), tr5=tr5, f1=f1, f2=f2, f3=f3, take=bool(f1 and f2 and f3)))
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-10-19"); ap.add_argument("--until", default=None)
    ap.add_argument("--no-save", action="store_true")
    a = ap.parse_args()
    since = dt.date.fromisoformat(a.since); until = dt.date.fromisoformat(a.until) if a.until else dt.date.today()
    data = pull(since, until)
    rows = [r for m, d in data.items() for r in trades(m, d, since)]
    T = pd.DataFrame(rows)
    if T.empty:
        print("no completed trading days since", since); raise SystemExit
    if not a.no_save:
        os.makedirs(os.path.dirname(OUT), exist_ok=True); T.to_csv(OUT, index=False)
    T["day"] = pd.to_datetime(T.day)
    f, b = T[T["take"]], T
    mf, tf = ct(f) if len(f) > 1 else (np.nan, np.nan)
    mb, tb = ct(b) if len(b) > 1 else (np.nan, np.nan)
    print(f"LDN3F forward {since}..{T.day.max().date()}: filtered n {len(f)} mean {mf:+.3f}R t {tf:+.2f} | "
          f"base n {len(b)} mean {mb:+.3f}R t {tb:+.2f} | decision at n >= 150 (futility: n >= 75 and mean <= -0.10)")
