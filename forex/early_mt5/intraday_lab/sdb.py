"""Python port of the Stochastic Daily Breakout EA (ea_batch/77900/StochDailyBreakout.mq5, open source by Bruno Myrrha) so that it can be tested vectorised on any symbol, with our own variants.
Rule on H1 (chart period) bars, evaluated at the first tick of every new bar: stochastic signal line (%K over the close-to-close range, SMMA slowing, SMMA signal), bar-2 turn (down = peak, up = trough); Bollinger(9, 2.0) on the weighted price read at shift 4;
BUY STOP at yesterday's high when the signal turns down and the open 3 bars ago is below the upper band; SELL STOP at yesterday's low when it turns up and that open is above the lower band. Stop and target = pct of the order price (1.9%), pending order lives 9 bars, one position at a time.
Fills / exits are simulated on the 1-minute BID / ASK bars: a buy stop fills when the ask high reaches the level (at the level, or at the open of a gapping minute), its stop and target are checked on bid low / high (stop first); sells mirror it on ask / bid.
Costs: the real spread (bid / ask) plus the MT5 broker commission (USD 6 a lot round turn on gold / FX, none on indices). R = net P&L / stop distance.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mt5broker.intraday_lab.lab import DATA, commission_price


def load_m1(sym):
    m = pd.read_parquet(DATA / f"{sym}_M1_ticks_full.parquet")
    return {k: m[c].values.astype(np.float64) for k, c in (("bo", "open"), ("bh", "high"), ("bl", "low"), ("bc", "close"), ("ao", "ask_open"), ("ah", "ask_high"), ("al", "ask_low"), ("ac", "ask_close"))} | {"t": m.time.values.astype(np.int64)}


def h1_bars(m1):
    g = (m1["t"] // 3600) * 3600; df = pd.DataFrame({"g": g, "bo": m1["bo"], "bh": m1["bh"], "bl": m1["bl"], "bc": m1["bc"]})
    a = df.groupby("g").agg(o=("bo", "first"), h=("bh", "max"), l=("bl", "min"), c=("bc", "last")); return a.index.values.astype(np.int64), a.o.values, a.h.values, a.l.values, a.c.values


def daily_hl(m1):
    d = m1["t"] // 86400; df = pd.DataFrame({"d": d, "h": m1["bh"], "l": m1["bl"]}); a = df.groupby("d").agg(h=("h", "max"), l=("l", "min")); return a.index.values.astype(np.int64), a.h.values, a.l.values


def stoch_signal(c, K=23, D=3, S=7):
    n = len(c); k = np.empty(n); main = np.empty(n); sig = np.empty(n)
    cs = pd.Series(c); hi_r = cs.rolling(K).max().values; lo_r = cs.rolling(K).min().values
    for i in range(n):
        if i >= K + 1:
            hi, lo = hi_r[i], lo_r[i]
        else:
            hi = lo = 50.0
        den = hi - lo; nom = c[i] - lo
        k[i] = (k[i - 1] if i else 50.0) if abs(den) < 1e-8 else min(100.0, max(0.0, 100 * nom / den))
        pm = main[i - 1] if i else 50.0
        main[i] = (pm * (S - 1) + k[i]) / S if i + 1 >= S else 0.0
        ps = sig[i - 1] if i else 50.0
        sig[i] = (ps * (D - 1) + main[i]) / D if i + 1 >= D else 0.0
    return sig


def bands(o, h, l, c, period=9, dev=2.0):
    w = pd.Series((h + l + 2 * c) / 4); ma = w.rolling(period).mean(); sd = w.rolling(period).std(ddof=0)
    return (ma + dev * sd).values, (ma - dev * sd).values


def simulate(sym, m1=None, pct=1.9, expiry=9, K=23, D=3, S=7, bp=9, start="2021-10-01", end="2026-10-02", atr_stop=None):
    """Return a DataFrame of trades (entry time, side, level, entry price, exit price, R). atr_stop = k: stop = target = k x ATR20 of the daily range at the signal (instead of pct of the price)."""
    m1 = m1 or load_m1(sym); t1 = m1["t"]
    ht, ho, hh, hl, hc = h1_bars(m1); sig = stoch_signal(hc, K, D, S); up, lo_b = bands(ho, hh, hl, hc, bp)
    dd, dH, dL = daily_hl(m1); dr = pd.Series(dH - dL).rolling(20).mean().shift(1).values
    t_lo, t_hi = int(pd.Timestamp(start).timestamp()), int(pd.Timestamp(end).timestamp()) + 86400
    comm = commission_price(sym, float(np.nanmedian(m1["bc"]))); trades = []
    pend = {1: None, -1: None}; busy_until = -1                 # one pending order per side (the EA replaces only the order of the same side); hedging account: both may fill
    i0 = int(np.searchsorted(ht, t_lo)); n = len(ht)
    for i in range(max(i0, 30), n):
        t0 = int(ht[i])
        if t0 > t_hi:
            break
        for sd_ in (1, -1):
            if pend[sd_] is not None and i - pend[sd_]["i"] >= expiry:
                pend[sd_] = None
        if t0 >= busy_until and i >= 5:
            s3, s2, s1 = sig[i - 3], sig[i - 2], sig[i - 1]
            turn_down = s3 < s2 and s2 > s1; turn_up = s3 > s2 and s2 < s1; open3 = ho[i - 3]
            buy = open3 < up[i - 4] and turn_down; sell = open3 > lo_b[i - 4] and turn_up
            if buy or sell:
                d = int(np.searchsorted(dd, t0 // 86400)) - 1
                if d >= 0:
                    j0 = int(np.searchsorted(t1, t0))
                    if buy and dH[d] > m1["ao"][j0]:
                        pend[1] = dict(i=i, side=1, level=float(dH[d]), atr=float(dr[d]))
                    elif sell and not buy and dL[d] < m1["bo"][j0]:
                        pend[-1] = dict(i=i, side=-1, level=float(dL[d]), atr=float(dr[d]))
        j0 = int(np.searchsorted(t1, t0)); j1 = int(np.searchsorted(t1, t0 + 3600))
        for side in (1, -1):
            pd_ = pend[side]
            if pd_ is None or j1 <= j0:
                continue
            L = pd_["level"]
            hit = (m1["ah"][j0:j1] >= L) if side > 0 else (m1["bl"][j0:j1] <= L)
            if not hit.any():
                continue
            jf = j0 + int(np.argmax(hit)); pend[side] = None
            p_fill = max(L, m1["ao"][jf]) if side > 0 else min(L, m1["bo"][jf])
            sd = (L * pct / 100.0) if atr_stop is None else atr_stop * pd_["atr"]
            if not np.isfinite(sd) or sd <= 0:
                continue
            sl = L - side * sd; tp = L + side * sd
            if side > 0:
                stop_hit = m1["bl"][jf:] <= sl; tp_hit = m1["bh"][jf:] >= tp
            else:
                stop_hit = m1["ah"][jf:] >= sl; tp_hit = m1["al"][jf:] <= tp
            a = int(np.argmax(stop_hit)) if stop_hit.any() else 10**12; b = int(np.argmax(tp_hit)) if tp_hit.any() else 10**12
            if a == b == 10**12:
                busy_until = int(t1[-1]) + 1; continue
            if a <= b:
                je = jf + a; op = m1["bo"][je] if side > 0 else m1["ao"][je]; px = min(sl, op) if side > 0 else max(sl, op)
            else:
                je = jf + b; px = tp
            pnl = (px - p_fill) * side - comm
            trades.append(dict(t_entry=int(t1[jf]), t_exit=int(t1[je]), side=side, level=L, entry=p_fill, exit=px, stop=sd, R=pnl / sd, pnl=pnl, year=pd.Timestamp(int(t1[jf]), unit="s").year))
            busy_until = max(busy_until, int(t1[je]) + 60)
    return pd.DataFrame(trades)
