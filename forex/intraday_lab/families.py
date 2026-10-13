"""Signal families for the intraday lab. Each returns (signal bar indices, direction +1/-1, stop distance in price, take-profit multiple of the stop, max bars). Rules are fixed before results (see lab/PREREG.md)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from forex.intraday_lab.lab import Bars


def _out(i, d, stop, tpm, maxb):
    return np.asarray(i, dtype=np.int64), np.asarray(d, dtype=np.int64), np.asarray(stop, dtype=np.float64), tpm, maxb


def orb(b: Bars, start_hour: int, nrange: int, m: float, sess_hours: int = 8, **_):
    """Opening range: the first nrange bars from start_hour (server time); first close beyond the range after it completes enters in that direction; stop = range size, target m x stop, flat at the end of the session."""
    idx, dr, st, mb = [], [], [], []
    days = np.unique(b.day)
    for dd in days:
        s = int(np.searchsorted(b.t, dd * 86400 + start_hour * 3600))
        e = s + nrange
        if e >= b.n or b.t[s] - (dd * 86400 + start_hour * 3600) > b.tf * 60 * 2:
            continue
        rh = b.bh[s:e].max(); rl = b.bl[s:e].min(); size = rh - rl
        if size <= 0:
            continue
        last = s + (sess_hours * 60) // b.tf
        seg = np.arange(e, min(last, b.n - 1))
        up = np.flatnonzero(b.bc[seg] > rh); dn = np.flatnonzero(b.bc[seg] < rl)
        u = up[0] if len(up) else 10**9; w = dn[0] if len(dn) else 10**9
        if u == w == 10**9:
            continue
        j = int(seg[min(u, w)]); idx.append(j); dr.append(1 if u < w else -1); st.append(size); mb.append(max(2, last - j))
    return _out(idx, dr, st, m, np.array(mb))


def mr(b: Bars, n: int, k: float, atrm: float, tpm: float, maxb: int, hours: tuple | None = None, **_):
    """Bollinger z-score fade."""
    c = pd.Series(b.mid); mu = c.rolling(n).mean(); sd = c.rolling(n).std(); z = ((c - mu) / sd).values
    atr = b.atr(14)
    cond_l = (z < -k) & (np.r_[np.nan, z[:-1]] >= -k); cond_s = (z > k) & (np.r_[np.nan, z[:-1]] <= k)
    if hours:
        ok = (b.hour >= hours[0]) & (b.hour < hours[1]); cond_l &= ok; cond_s &= ok
    il = np.flatnonzero(cond_l); is_ = np.flatnonzero(cond_s)
    idx = np.r_[il, is_]; d = np.r_[np.ones(len(il), int), -np.ones(len(is_), int)]
    o = np.argsort(idx); idx, d = idx[o], d[o]
    return _out(idx, d, atrm * atr[idx], tpm, maxb)


def don(b: Bars, n: int, atrm: float, tpm: float, maxb: int, hours: tuple | None = None, **_):
    """Donchian breakout continuation."""
    hh = pd.Series(b.bh).rolling(n).max().shift(1).values; ll = pd.Series(b.bl).rolling(n).min().shift(1).values; atr = b.atr(14)
    cl = b.bc > hh; cs = b.bc < ll
    if hours:
        ok = (b.hour >= hours[0]) & (b.hour < hours[1]); cl &= ok; cs &= ok
    il = np.flatnonzero(cl); is_ = np.flatnonzero(cs)
    idx = np.r_[il, is_]; d = np.r_[np.ones(len(il), int), -np.ones(len(is_), int)]
    o = np.argsort(idx); idx, d = idx[o], d[o]
    return _out(idx, d, atrm * atr[idx], tpm, maxb)


def rsi2(b: Bars, lo: float, hi: float, atrm: float, tpm: float, maxb: int, hours: tuple | None = None, **_):
    """RSI(2) extremes fade."""
    c = pd.Series(b.mid); dl = c.diff(); up = dl.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    rsi = (100 - 100 / (1 + up / dn.replace(0, np.nan))).values; atr = b.atr(14)
    cl = rsi < lo; cs = rsi > hi
    if hours:
        ok = (b.hour >= hours[0]) & (b.hour < hours[1]); cl &= ok; cs &= ok
    il = np.flatnonzero(cl); is_ = np.flatnonzero(cs)
    idx = np.r_[il, is_]; d = np.r_[np.ones(len(il), int), -np.ones(len(is_), int)]
    o = np.argsort(idx); idx, d = idx[o], d[o]
    return _out(idx, d, atrm * atr[idx], tpm, maxb)


FAMILIES = {"orb": orb, "mr": mr, "don": don, "rsi2": rsi2}


def grid(tf: int):
    """Pre-registered grid per timeframe."""
    g = []
    nr = (3, 6) if tf == 5 else ((2, 4) if tf == 15 else (10, 20))
    for sh in (9, 10, 15, 16):
        for n in nr:
            for m in (1.0, 2.0):
                g.append(("orb", dict(start_hour=sh, nrange=n, m=m)))
    mb = (24, 48) if tf >= 5 else (60, 120)
    for n in (20, 50):
        for k in (2.0, 2.5):
            for a in (1.5, 2.5):
                for m_ in mb:
                    g.append(("mr", dict(n=n, k=k, atrm=a, tpm=1.0, maxb=m_)))
    for n in (20, 60):
        for a in (1.5, 2.5):
            for t_ in (1.5, 3.0):
                g.append(("don", dict(n=n, atrm=a, tpm=t_, maxb=48 if tf >= 5 else 120)))
    for lo, hi in ((5, 95), (10, 90)):
        for a in (1.5, 2.5):
            g.append(("rsi2", dict(lo=lo, hi=hi, atrm=a, tpm=1.0, maxb=24 if tf >= 5 else 60)))
    return g
