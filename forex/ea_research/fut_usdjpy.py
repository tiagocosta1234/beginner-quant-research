"""the trader 26 Oct 2026: "on futures". The USDJPY London-open breakout (PRESAMPLE L1, frozen: box 08:00-08:30 London, stop orders to 11:00,
stop at the other side, exit 17:00) re-priced with CME 6J futures costs instead of spot spreads. DESCRIPTIVE: 2020-26 is already-seen data
(HistData 2020-21 and 2022-24, MT5 2025-26), so this only asks whether the known edge survives futures friction; it is not a new test.
6J = JPY/USD, 12.5M yen, tick 0.0000005 = $6.25; it moves inversely to USDJPY, so the same box / stop / exit apply. One 6J tick in USDJPY
units at price P is P^2 * 5e-7 (about 0.6 pip at 110, 1.1 pip at 150). Costs per trade: ask = bid + 1 tick (spread), then minus
commission $5 round turn (0.8 tick) and slippage of 1 tick on the stop-order entry and 1 tick on the exit (always charged), in R.
Usage (from D:/finance/beginner-quant-research): python -m forex.ea_research.fut_usdjpy"""
import numpy as np
import pandas as pd

from forex.ea_research.brk_exits import exits
from forex.ea_research.crt import load

H, M = 3600, 60
TICK = 5e-7; COMM_T = 0.8; SLIP_T = 2.0


def from_bid(t_utc, bo, bh, bl, bc):
    D = {"bo": bo, "bh": bh, "bl": bl, "bc": bc}
    tk = bc ** 2 * TICK
    for a, b in (("ao", "bo"), ("ah", "bh"), ("al", "bl"), ("ac", "bc")):
        D[a] = D[b] + tk
    D["t"] = t_utc
    loc = pd.to_datetime(t_utc, unit="s").tz_localize("UTC").tz_convert("Europe/London").tz_localize(None)
    D["lc"] = loc.values.astype("datetime64[s]").astype(np.int64)
    return D


def histdata(path, lo, hi):
    d = pd.read_parquet(path).sort_values("t_utc").drop_duplicates("t_utc")
    d = d[(d.t_utc >= pd.Timestamp(lo).timestamp()) & (d.t_utc < pd.Timestamp(hi).timestamp())]
    return from_bid(d.t_utc.to_numpy(np.int64), *(d[k].to_numpy(float) for k in ("bo", "bh", "bl", "bc")))


def mt5(lo):
    E = load("USDJPY", pd.Timestamp("2026-10-26").timestamp())          # load(sym, end): data up to `end`
    t = pd.to_datetime(E["t"], unit="s").tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    ok = np.asarray(~t.isna()) & (np.asarray(E["t"]) >= pd.Timestamp(lo).timestamp())
    tu = t[ok].values.astype("datetime64[s]").astype(np.int64)
    return from_bid(tu, *(np.asarray(E[k], float)[ok] for k in ("bo", "bh", "bl", "bc")))


def l1(D, rng):
    lc, rows = D["lc"], []
    for d in np.unique(lc // 86400):
        base = d * 86400
        i0, i1 = np.searchsorted(lc, base + 8 * H), np.searchsorted(lc, base + 8 * H + 30 * M)
        w1, xe = np.searchsorted(lc, base + 11 * H), np.searchsorted(lc, base + 17 * H)
        if xe >= len(lc) or i1 - i0 < 20 or lc[i0] // 86400 != d or w1 <= i1 + 30:
            continue
        Hb, Lb = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
        up = np.flatnonzero(D["ah"][i1:w1] >= Hb); dn = np.flatnonzero(D["bl"][i1:w1] <= Lb)
        ku, kd = (i1 + up[0] if len(up) else None), (i1 + dn[0] if len(dn) else None)
        if (ku is None and kd is None) or (ku is not None and ku == kd):
            continue
        side = 1 if (kd is None or (ku is not None and ku < kd)) else -1
        k = ku if side > 0 else kd
        e = max(Hb, D["ao"][k]) if side > 0 else min(Lb, D["bo"][k])
        R = abs(e - (Lb if side > 0 else Hb))
        if k >= xe or not (R > 0 and R >= 2 * (D["ao"][k] - D["bo"][k])):
            continue
        x = exits(D, k, xe, side, e, R)
        if not x:
            continue
        tk = D["bc"][k] ** 2 * TICK
        net = x[3] - (COMM_T + SLIP_T) * tk / R
        kc = int(rng.integers(i1, w1)); sc = 1 if rng.random() < 0.5 else -1
        ec = D["ao"][kc] if sc > 0 else D["bo"][kc]; xc = exits(D, kc, xe, sc, ec, R)
        rows.append(dict(day=pd.Timestamp(base, unit="s"), side=side, R_spread_only=x[3], R=net, box_pips=R * 100, ticks=R / tk,
                         C=(xc[3] - (COMM_T + SLIP_T) * tk / R) if xc else np.nan))
    return pd.DataFrame(rows)


def t(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def main():
    rng = np.random.default_rng(7)
    parts = [l1(histdata("D:/finance/data_histdata/USDJPY.parquet", "2020-01-02", "2022-01-01"), rng),
             l1(histdata("D:/finance/data_histdata/USDJPY_2022_24.parquet", "2022-01-01", "2025-01-01"), rng),
             l1(mt5("2025-01-01"), rng)]
    df = pd.concat(parts, ignore_index=True); df["yr"] = df.day.dt.year
    print("USDJPY London breakout on 6J futures costs (1 tick spread + $5 RT + 2 ticks slippage), 2020-26, DESCRIPTIVE (seen data)")
    print("median box %.1f pips = %.0f 6J ticks; futures friction about %.3f R a trade" % (df.box_pips.median(), df.ticks.median(), (df.R_spread_only - df.R).median()))
    print("%-6s %5s %9s %9s %7s %8s %9s" % ("year", "n", "R spot*", "R 6J", "t 6J", "win %", "random"))
    for y, g in list(df.groupby("yr")) + [("all", df)]:
        print("%-6s %5d %+9.3f %+9.3f %7.2f %7.0f%% %+9.3f" % (y, len(g), g.R_spread_only.mean(), g.R.mean(), t(g.R), 100 * (g.R > 0).mean(), g.C.mean()))
    print("* R spot = the same trades with only the 1-tick spread (no commission / slippage)")
    assert df.day.is_unique, "more than one trade on a day"
    print("one trade a day at most: mean %.3f R a trade; at $1,500 risk: $%.0f a trade on average" % (df.R.mean(), 1500 * df.R.mean()))
    w = df.sort_values("day").R.cumsum(); dd = (w - w.cummax()).min()
    run = mx = 0
    for r in df.sort_values("day").R:
        run = run + 1 if r <= 0 else 0; mx = max(mx, run)
    print("worst drawdown %.1f R; longest losing run %d trades" % (dd, mx))


if __name__ == "__main__":
    main()
