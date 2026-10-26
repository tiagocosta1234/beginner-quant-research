"""the trader 26 Oct 2026: "futures data could have given a different result ... our whole backtest results could be poisoned by wrong data type".
Every logged blind trade (January batch 1 + batch 2) replayed on BOTH data sets with the same rules: entry at the open of the minute after
the logged candle, his stop and target DISTANCES from that fill, stop first if both in one minute, still open at 17:00 local = closed there.
SPOT = MT5 XAUUSD bid/ask (the registered scoring: fill on the ask (long) / bid (short), exits on the other side).
FUT  = Databento GC 1m (the MGC price): fill 1 tick (0.1) worse, stop exits 1 tick worse, target exits at the price.
Prints each trade's result on both and how often they agree. Usage (from ema12): python spot_vs_futures.py"""
import numpy as np, pandas as pd
import blind_png as B


def spot_day(day):
    r = pd.read_parquet(B.SRC); t = pd.to_datetime(r.t, unit="s")
    m = (t >= day) & (t < pd.Timestamp(day) + pd.Timedelta(days=1, hours=6)); r, t = r[m], t[m]
    return r.set_axis(t.pipe(lambda x: x - pd.Timedelta(hours=7)).dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("Europe/London").dt.tz_localize(None).to_numpy()).sort_index()


def play(bars, sd, sdist, tdist, hi_col, lo_col, fill, slip):
    sl, tp = fill - sd * sdist, fill + sd * tdist
    for ts, b in bars.iterrows():
        hi, lo = b[hi_col], b[lo_col]
        if (lo <= sl) if sd > 0 else (hi >= sl): return -1.0 - slip / sdist, "SL", ts
        if (hi >= tp) if sd > 0 else (lo <= tp): return tdist / sdist, "TP", ts
    last = bars.iloc[-1]
    return sd * (last["close" if "close" in bars else "bc"] - fill) / sdist, "EOD", bars.index[-1]


def main():
    rows = []
    for f, batch in (("BLIND_LOG_JAN2026_FXR.csv", "Jan"), ("BLIND_LOG_BATCH2_FXR.csv", "B2")):
        L = pd.read_csv(f)
        for r in L.itertuples():
            if r.side not in ("L", "S") or not isinstance(r.hhmm, str): continue
            hh = r.hhmm.strip("~")
            sd = 1 if r.side == "L" else -1; sdist, tdist = abs(r.entry - r.stop), abs(r.target - r.entry)
            start = pd.Timestamp("%s %s" % (r.date, hh)) + pd.Timedelta(minutes=1); end = pd.Timestamp("%s 17:00" % r.date)
            s = spot_day(r.date); s = s[(s.index >= start) & (s.index <= end)]
            out = dict(batch=batch, date=r.date, side=r.side, flag=r.flag, pre=r.pre, stop_pts=round(sdist, 2))
            if len(s):
                fill = s.ao.iloc[0] if sd > 0 else s.bo.iloc[0]
                Rs, ks, ts = play(s, sd, sdist, tdist, "bh" if sd > 0 else "ah", "bl" if sd > 0 else "al", fill, 0.0)
                out.update(spot_R=round(Rs, 2), spot_exit=ks, spot_time=ts.strftime("%H:%M"))
            g = B.load_fut(r.date, end); g = g[g.index >= start]
            if len(g):
                fill = g.open.iloc[0] + sd * 0.1
                Rf, kf, tf = play(g, sd, sdist, tdist, "high", "low", fill, 0.1)
                out.update(fut_R=round(Rf, 2), fut_exit=kf, fut_time=tf.strftime("%H:%M"))
            rows.append(out)
    D = pd.DataFrame(rows)
    pd.set_option("display.width", 200); print(D.to_string(index=False))
    both = D.dropna(subset=["spot_R", "fut_R"])
    same = (np.sign(both.spot_R) == np.sign(both.fut_R))
    print("\ntrades on both data sets: %d   same win/loss outcome: %d (%.0f%%)   same exit type: %d" % (
        len(both), same.sum(), 100 * same.mean(), (both.spot_exit == both.fut_exit).sum()))
    for lab, sub in (("ALL", both), ("January", both[both.batch == "Jan"]), ("Batch 2", both[both.batch == "B2"])):
        print("  %-8s n %2d   spot: %2d wins, mean R %+.3f   futures: %2d wins, mean R %+.3f" % (
            lab, len(sub), (sub.spot_R > 0).sum(), sub.spot_R.mean(), (sub.fut_R > 0).sum(), sub.fut_R.mean()))
    diff = both[~same]
    if len(diff): print("\nDIFFERENT outcome:\n" + diff[["batch", "date", "side", "stop_pts", "spot_R", "spot_exit", "spot_time", "fut_R", "fut_exit", "fut_time"]].to_string(index=False))
    miss = D[D.fut_R.isna()]
    if len(miss): print("\nno futures data (Databento ends 2026-09-25): " + ", ".join(miss.date))


if __name__ == "__main__":
    main()
