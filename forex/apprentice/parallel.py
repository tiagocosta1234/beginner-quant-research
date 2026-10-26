"""PREREG_PARALLEL_FORWARD on BrokerAPI data (the trader 26 Oct 2026: "switch all you can to BrokerAPI"). READ-ONLY: it only calls the BrokerAPI History
API (brokerapi_py.BrokerAPI.get_bars) with the practice credentials in live_bot/.env; it never places, changes or cancels an order and prints
no credential. Track A is LONDON_FIRST15_1TO1.pine recomputed from BrokerAPI 1-minute bars with the frozen settings: direction rule Candle
(close > open of the 08:00-08:15 London window, a flat candle follows the daily trend), stop = the far end of the window + 0.5 x window range
(never tighter than 0.03 x prior daily ATR14), target = 1R, entry = the 08:14 bar close, exits checked from the 08:15 bar on (stop first on a
tie), flat at the open of the first bar at or after 16:00 London, costs MGC 0.32 / MNQ 1.1 / MES 0.74 / MYM 4.4 points round trip.
Usage (from forex/apprentice):
  python brokerapi_parallel.py first15 [YYYY-MM-DD]   -> the window and track A's trade per symbol, using ONLY bars before 08:15 London
  python brokerapi_parallel.py record  [YYYY-MM-DD]   -> track A's exit and net R per symbol (run after 16:00 London)"""
import asyncio, datetime as dt, os, sys
from zoneinfo import ZoneInfo

import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(HERE, "..", "..", "live_bot", ".env")
SYMS = ["MGC", "MNQ", "MES", "MYM"]
COST = {"MGC": 0.32, "MNQ": 1.1, "MES": 0.74, "MYM": 4.4}
LON = ZoneInfo("Europe/London")


def load_env():
    for line in open(ENV, encoding="utf-8"):
        line = line.strip()
        if line.startswith("BROKERAPI_") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def to_london(df):
    ts = df["timestamp"]
    if ts.dtype.time_zone is None:
        ts = ts.dt.replace_time_zone("UTC")
    return df.with_columns(ts.dt.convert_time_zone("Europe/London").alias("lon"))


def daily_context(d):
    """Prior-day ATR14 (Wilder) and close > SMA20, from daily bars that closed before the session date."""
    d = d.sort("timestamp")
    hi, lo, cl = d["high"].to_list(), d["low"].to_list(), d["close"].to_list()
    tr = [hi[0] - lo[0]] + [max(hi[i] - lo[i], abs(hi[i] - cl[i - 1]), abs(lo[i] - cl[i - 1])) for i in range(1, len(cl))]
    atr = None
    for i, x in enumerate(tr):
        atr = (sum(tr[:14]) / 14 if i == 13 else (atr * 13 + x) / 14) if i >= 13 else None
    trend = cl[-1] > sum(cl[-20:]) / 20 if len(cl) >= 20 else None
    return atr, trend


async def main(mode, day):
    import brokerapi_py as px
    load_env()
    out = []
    async with px.BrokerAPI.from_env() as client:
        await client.authenticate()
        start = dt.datetime.combine(day, dt.time(8, 0), LON)
        cut = start + dt.timedelta(minutes=15) if mode == "first15" else dt.datetime.combine(day, dt.time(16, 5), LON)
        for s in SYMS:
            m1 = await client.get_bars(s, interval=1, unit=2, start_time=start - dt.timedelta(minutes=5), end_time=cut, partial=False)
            dd = await client.get_bars(s, days=45, interval=1, unit=4, end_time=start - dt.timedelta(hours=10), partial=False)
            if m1 is None or len(m1) == 0:
                out.append(f"{s}: no 1m data"); continue
            m1 = to_london(m1).sort("lon")
            w = m1.filter((pl.col("lon") >= start) & (pl.col("lon") < start + dt.timedelta(minutes=15)))
            if len(w) < 10:
                out.append(f"{s}: window has {len(w)} bars, skipped"); continue
            atr, trend = daily_context(dd) if dd is not None and len(dd) >= 15 else (None, None)
            wo, wh, wl, wc = w["open"][0], w["high"].max(), w["low"].min(), w["close"][-1]
            up = wc > wo or (wc == wo and bool(trend))
            risk = max(abs(wc - (wl if up else wh)) + 0.5 * (wh - wl), 0.03 * atr if atr else 0.0)
            sl, tp = (wc - risk, wc + risk) if up else (wc + risk, wc - risk)
            row = dict(symbol=s, a_dir="LONG" if up else "SHORT", a_entry=round(wc, 2), a_stop=round(sl, 2), a_target=round(tp, 2),
                       w_open=wo, w_high=wh, w_low=wl, atr14=round(atr, 2) if atr else None, trend_up=trend, last_bar=str(w["lon"][-1])[:16])
            if mode == "record":
                after = m1.filter(pl.col("lon") >= start + dt.timedelta(minutes=15))
                ex, note = None, "no exit bar yet"
                for r in after.iter_rows(named=True):
                    if r["lon"] >= dt.datetime.combine(day, dt.time(16, 0), LON):
                        ex, note = r["open"], "session end 16:00"; break
                    sl_hit = r["low"] <= sl if up else r["high"] >= sl
                    tp_hit = r["high"] >= tp if up else r["low"] <= tp
                    if sl_hit or tp_hit:
                        ex, note = (sl, f"stop {str(r['lon'])[11:16]}") if sl_hit else (tp, f"target {str(r['lon'])[11:16]}"); break
                if ex is not None:
                    gross = ((ex - wc) if up else (wc - ex)) / risk
                    row.update(a_R_net=round(gross - COST[s] / risk, 3), a_exit_note=note)
                else:
                    row.update(a_R_net=None, a_exit_note=note)
            out.append(row)
    for r in out:
        print(r)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "first15"
    day = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.datetime.now(LON).date()
    asyncio.run(main(mode, day))
